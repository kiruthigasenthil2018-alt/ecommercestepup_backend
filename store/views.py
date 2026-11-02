import hmac, random, re, traceback
import jwt
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Avg, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .geo import in_india, locate
from .invoice import build_invoice
from .models import *
from .serializers import *

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
strong = lambda pw: len(pw) >= 8 and bool(re.search(r"[a-z]", pw) and re.search(r"[A-Z]", pw) and re.search(r"\d", pw))
clean = lambda v: str(v or "").strip().lower()

def user_data(user, pr=None):
    pr = pr or Profile.objects.get_or_create(user=user)[0]
    return {"email": user.email, "name": user.first_name, "is_admin": user.is_staff, "avatar": pr.avatar, "phone": pr.phone}

def token_for(user):
    user.last_login = timezone.now(); user.save(update_fields=["last_login"])
    t, _ = Token.objects.get_or_create(user=user)
    return Response({"token": t.key, "user": user_data(user)})

def social_user(email, name="", provider="google"):
    u = User.objects.filter(email__iexact=email).first(); new = u is None
    if new: u = User.objects.create_user(username=email, email=email, first_name=name or email.split("@")[0])
    p, _ = Profile.objects.get_or_create(user=u)
    if new: p.provider = provider
    if provider == "google": p.google_linked = True
    p.verified = True; p.save()
    return u

def issue_code(rec):
    """Create and email a 6-digit code. Returns None when sent, or a short warning if SMTP failed
    (in DEBUG the real error is shown and the code is printed in the backend terminal so you can keep testing)."""
    code = f"{random.SystemRandom().randint(0, 999999):06d}"
    rec.code = make_password(code); rec.expires = timezone.now() + timedelta(minutes=10); rec.attempts = 0; rec.save()
    try:
        send_mail("Your StepUp.in verification code", f"Hi,\n\nYour StepUp.in verification code is {code}\nIt expires in 10 minutes.\n\nIf you did not request this, ignore this email.\n\n- StepUp.in, Chennai",
                  settings.DEFAULT_FROM_EMAIL, [rec.email])
        return {"warning": None, "code": code}
    except Exception as e:
        traceback.print_exc()
        print(f"\n*** EMAIL FAILED: {e.__class__.__name__}: {e}\n*** Verification code for {rec.email}: {code}\n", flush=True)
        if not (settings.DEBUG or settings.SHOW_OTP_ON_SCREEN): raise
        return {"warning": f"{e.__class__.__name__}: {e}"[:200], "code": code}

def otp_response(res):
    """Tell the page whether the email went out, and (demo mode) include the code so it can be shown on the login page."""
    emailed = bool(settings.EMAIL_HOST_USER) and not res["warning"]
    out = {"sent": True, "smtp": emailed, "warning": res["warning"]}
    if settings.SHOW_OTP_ON_SCREEN or not emailed: out["dev_code"] = res["code"]
    return Response(out)

def smtp_fail(e):
    hint = "Gmail rejected the login - use a Google App Password (not your normal password)." if "Authentication" in e.__class__.__name__ else "Check EMAIL_HOST_USER / EMAIL_HOST_PASSWORD in backend/.env, then restart the backend."
    return Response({"error": f"Could not send the email. {hint} [{e.__class__.__name__}: {str(e)[:120]}]"}, 502)

@api_view(["POST"])
def signup(request):
    email = clean(request.data.get("email")); pw = request.data.get("password", "")
    if not EMAIL_RE.match(email): return Response({"error": "Enter a valid email address."}, 400)
    if not strong(pw): return Response({"error": "Password needs 8+ characters with upper-case, lower-case and a number."}, 400)
    if User.objects.filter(Q(username__iexact=email) | Q(email__iexact=email)).exists():
        return Response({"error": "This email is already registered. Please log in."}, 400)
    rec, _ = EmailOTP.objects.get_or_create(email=email, defaults={"password": "", "code": "", "expires": timezone.now()})
    rec.password = make_password(pw)
    try: res = issue_code(rec)
    except Exception as e: return smtp_fail(e)
    return otp_response(res)

@api_view(["POST"])
def resend(request):
    rec = EmailOTP.objects.filter(email=clean(request.data.get("email"))).first()
    if not rec: return Response({"error": "Please start sign-up again."}, 400)
    try: res = issue_code(rec)
    except Exception as e: return smtp_fail(e)
    return otp_response(res)

@api_view(["POST"])
def verify(request):
    email = clean(request.data.get("email")); code = str(request.data.get("code", "")).strip()
    rec = EmailOTP.objects.filter(email=email).exclude(password="").first()
    if not rec: return Response({"error": "Please start sign-up again."}, 400)
    if rec.expires < timezone.now(): return Response({"error": "This code has expired. Tap Resend."}, 400)
    if rec.attempts >= 5: return Response({"error": "Too many wrong attempts. Tap Resend for a new code."}, 400)
    if not check_password(code, rec.code):
        rec.attempts += 1; rec.save(); return Response({"error": "Incorrect code. Try again."}, 400)
    u = User(username=email, email=email, first_name=email.split("@")[0]); u.password = rec.password; u.save(); rec.delete()
    return token_for(u)

@api_view(["POST"])
def login_otp(request):
    email = clean(request.data.get("email"))
    u = User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).first() if EMAIL_RE.match(email) else None
    if not u: return Response({"error": "No account found for this email. Please register first."}, 400)
    rec, _ = EmailOTP.objects.get_or_create(email=email, defaults={"password": "", "code": "", "expires": timezone.now()})
    rec.password = ""  # empty password marks this as a LOGIN code
    try: res = issue_code(rec)
    except Exception as e: return smtp_fail(e)
    return otp_response(res)

@api_view(["POST"])
def login_otp_verify(request):
    email = clean(request.data.get("email")); code = str(request.data.get("code", "")).strip()
    rec = EmailOTP.objects.filter(email=email, password="").first()
    if not rec: return Response({"error": "Please request a new code."}, 400)
    if rec.expires < timezone.now(): return Response({"error": "This code has expired. Tap Resend."}, 400)
    if rec.attempts >= 5: return Response({"error": "Too many wrong attempts. Tap Resend for a new code."}, 400)
    if not check_password(code, rec.code):
        rec.attempts += 1; rec.save(); return Response({"error": "Incorrect code. Try again."}, 400)
    u = User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).first(); rec.delete()
    return token_for(u)

@api_view(["POST"])
def login(request):
    email = clean(request.data.get("email"))
    u0 = User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).first()
    u = authenticate(username=u0.username, password=request.data.get("password", "")) if u0 else None
    if not u: return Response({"error": "Wrong email or password."}, 400)
    return token_for(u)

@api_view(["POST"])
def google_login(request):
    from google.oauth2 import id_token
    from google.auth.transport import requests as grq
    ids = [i.strip() for i in settings.GOOGLE_CLIENT_ID.split(",") if i.strip()]
    if not ids: return Response({"error": "Google sign-in is not configured on the server (set GOOGLE_CLIENT_ID)."}, 400)
    try: info = id_token.verify_oauth2_token(request.data.get("credential", ""), grq.Request(), audience=ids, clock_skew_in_seconds=60)
    except Exception as e:
        print("Google sign-in failed:", e, flush=True)
        return Response({"error": f"Google sign-in failed: {str(e)[:180]}"}, 400)
    if not info.get("email_verified"): return Response({"error": "Google email not verified."}, 400)
    return token_for(social_user(info["email"], info.get("name", "")))

@api_view(["POST"])
def apple_login(request):
    tok = request.data.get("id_token", "")
    try:
        key = jwt.PyJWKClient("https://appleid.apple.com/auth/keys").get_signing_key_from_jwt(tok)
        info = jwt.decode(tok, key.key, algorithms=["RS256"], audience=settings.APPLE_CLIENT_ID, issuer="https://appleid.apple.com")
    except Exception: return Response({"error": "Apple sign-in failed."}, 400)
    return token_for(social_user(info.get("email") or f"{info['sub']}@privaterelay.appleid.com", request.data.get("name", ""), "apple"))

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request): return token_for(request.user)

@api_view(["GET"])
def products(request):
    if not Product.objects.exists():  # empty database -> load the catalogue automatically
        try:
            from django.core.management import call_command
            call_command("seed")
        except Exception: traceback.print_exc()
    q = request.query_params; qs = Product.objects.filter(is_available=True)
    if q.get("gender"): qs = qs.filter(gender=q["gender"])
    if q.get("trending"): qs = qs.filter(trending=True)
    if q.get("q"): qs = qs.filter(Q(name__icontains=q["q"]) | Q(brand__icontains=q["q"]) | Q(style__icontains=q["q"]))
    if q.get("style"): qs = qs.filter(style__in=q["style"].split(","))
    if q.get("brand"): qs = qs.filter(brand__in=q["brand"].split(","))
    if q.get("ids"): qs = qs.filter(id__in=[int(i) for i in q["ids"].split(",") if i.isdigit()])
    qs = qs.order_by({"low": "price", "high": "-price", "rating": "-rating", "new": "-created", "brand": "brand"}.get(q.get("sort"), "id"))
    items = list(qs)  # JSON lists filtered in Python so it works on SQLite/MySQL/PostgreSQL
    colors = [c for c in q.get("color", "").split(",") if c]; sizes = [s for s in q.get("size", "").split(",") if s]
    if colors: items = [p for p in items if any(c in p.colors for c in colors)]
    if sizes: items = [p for p in items if any(s in [str(x) for x in p.sizes] for s in sizes)]
    return Response(ProductS(items, many=True, context={"request": request}).data)

@api_view(["GET"])
def product_detail(request, pk):
    return Response(ProductS(get_object_or_404(Product, pk=pk), context={"request": request}).data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def offer(request):
    return Response({"first_order": not request.user.orders.exists(), **settings.FIRST_ORDER})

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def orders(request):
    if request.method == "GET":
        return Response(OrderS(request.user.orders.order_by("-created"), many=True).data)
    d = request.data; items = d.get("items", []); pay = d.get("payment", "cod")
    if not items: return Response({"error": "Cart is empty."}, 400)
    if pay not in ("cod", "card", "upi", "netbanking"): return Response({"error": "Choose a payment method."}, 400)
    if pay == "card" and not re.fullmatch(r"\d{4}", str(d.get("card_last4", ""))): return Response({"error": "Enter a valid card."}, 400)
    s = OrderS(data=d); s.is_valid(raise_exception=True)
    first = not request.user.orders.exists(); F = settings.FIRST_ORDER
    g = None
    try:  # the customer placed a pin on the checkout map (or used GPS)
        la, ln = float(d.get("dest_lat")), float(d.get("dest_lng"))
        if in_india(la, ln): g = (la, ln, "pinned")
    except (TypeError, ValueError): pass
    g = g or locate(d.get("pincode"), d.get("city"), d.get("state"))
    with transaction.atomic():
        lines = []
        for i in items:
            p = get_object_or_404(Product, pk=i["product"]); n = max(1, int(i.get("quantity", 1)))
            if not p.is_available or p.stock < n: return Response({"error": f"Sorry, only {p.stock} left of {p.name}."}, 400)
            lines.append((p, n, i))
        o = s.save(user=request.user, number="", payment=pay)
        subtotal = 0
        for p, n, i in lines:
            subtotal += p.price * n; p.stock -= n; p.save()
            OrderItem.objects.create(order=o, product=p, name=f"{p.brand} {p.name}".strip(), size=i.get("size", ""), color=i.get("color", ""), quantity=n, price=p.price)
        o.subtotal = subtotal; o.discount = min(subtotal * F["percent"] // 100, F["cap"]) if first else 0
        o.gift = first; o.total = subtotal - o.discount; o.payment_status = "pay_on_delivery" if pay == "cod" else "paid"
        o.expected_delivery = timezone.now().date() + timedelta(days=5); o.dest_lat, o.dest_lng, o.dest_source = g; o.save()
        Profile.objects.update_or_create(user=request.user, defaults={"phone": o.phone, "address": o.address, "city": o.city, "state": o.state, "pincode": o.pincode})
    return Response(OrderS(o).data, 201)

def own_order(request, number):
    return get_object_or_404(Order, number=number) if request.user.is_staff else get_object_or_404(request.user.orders, number=number)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def order_detail(request, number): return Response(OrderS(own_order(request, number)).data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def invoice(request, number):
    o = own_order(request, number)
    return HttpResponse(build_invoice(o), content_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="StepUp-invoice-{o.number}.pdf"'})

@api_view(["POST"])
def enquiry(request):
    Enquiry.objects.create(name=request.data.get("name", ""), email=request.data.get("email", ""), phone=request.data.get("phone", ""), message=request.data.get("message", ""))
    return Response({"ok": True}, 201)

@api_view(["POST"])
def subscribe(request):
    email = clean(request.data.get("email"))
    if not EMAIL_RE.match(email): return Response({"error": "Enter a valid email address."}, 400)
    Subscriber.objects.get_or_create(email=email); return Response({"ok": True}, 201)

@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def state(request):
    s, _ = UserState.objects.get_or_create(user=request.user)
    if request.method == "PUT":
        if isinstance(request.data.get("cart"), list): s.cart = request.data["cart"]; s.save()
        if isinstance(request.data.get("wishlist"), list):
            valid = set(Product.objects.filter(id__in=[i for i in request.data["wishlist"] if isinstance(i, int)]).values_list("id", flat=True))
            WishlistItem.objects.filter(user=request.user).exclude(product_id__in=valid).delete()
            for pid in valid: WishlistItem.objects.get_or_create(user=request.user, product_id=pid)
    return Response({"cart": s.cart, "wishlist": list(request.user.wishlist_items.values_list("product_id", flat=True))})

@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def profile(request):
    p, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "PUT":
        d = request.data; name = str(d.get("name", request.user.first_name) or "").strip()
        phone = re.sub(r"[\s-]", "", str(d.get("phone", p.phone) or "")); pin = str(d.get("pincode", p.pincode) or "").strip()
        if name and not re.fullmatch(r"[A-Za-z][A-Za-z .'-]{1,59}", name): return Response({"error": "Enter a valid name (letters only)."}, 400)
        if phone and not re.fullmatch(r"(\+91|91|0)?[6-9]\d{9}", phone): return Response({"error": "Enter a valid 10-digit mobile number."}, 400)
        if pin and not re.fullmatch(r"[1-9]\d{5}", pin): return Response({"error": "Pincode must be 6 digits."}, 400)
        if d.get("avatar") in ("male", "female"): p.avatar = d["avatar"]
        if name: request.user.first_name = name; request.user.save()
        p.phone, p.pincode = phone, pin
        for k in ("address", "city", "state"): setattr(p, k, str(d.get(k, getattr(p, k)) or "").strip()[:250])
        p.save()
    return Response({"user": user_data(request.user, p), "name": request.user.first_name, "email": request.user.email,
                     "profile": {k: getattr(p, k) for k in ("phone", "address", "city", "state", "pincode", "avatar")}})

@api_view(["GET"])
def site(request):
    h = HomePage.objects.first(); c = ContactPage.objects.first()
    banners = [{"id": b.id, "text": b.text.replace("|", "\n"), "image": request.build_absolute_uri(b.image.url) if b.image else b.image_path, "to": b.link, "pos": b.position} for b in HomeBanner.objects.filter(active=True)]
    contact = {k: getattr(c, k) for k in ("address", "orders_phone", "queries_phone", "landline", "whatsapp", "email", "hours", "facebook", "instagram", "twitter", "meta")} if c else None
    return Response({"banners": banners, "overview": h.overview if h else "", "promo": h.promo_text if h else "", "contact": contact})

@api_view(["GET"])
def config(request):
    """Public settings for the website, so Google sign-in works after deployment without rebuilding the frontend."""
    ids = [i.strip() for i in settings.GOOGLE_CLIENT_ID.split(",") if i.strip()]
    return Response({"google_client_id": ids[0] if ids else "", "apple_client_id": settings.APPLE_CLIENT_ID})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_review(request, pk):
    p = get_object_or_404(Product, pk=pk); d = request.data
    title = str(d.get("title", "")).strip(); body = str(d.get("body", "")).strip()
    try: rating = int(d.get("rating", 5))
    except (TypeError, ValueError): rating = 0
    if not 3 <= len(title) <= 100: return Response({"error": "Title must be 3 to 100 characters."}, 400)
    if not 10 <= len(body) <= 1000: return Response({"error": "Review must be 10 to 1000 characters."}, 400)
    if not 1 <= rating <= 5: return Response({"error": "Choose a rating from 1 to 5 stars."}, 400)
    pr = Profile.objects.get_or_create(user=request.user)[0]
    r, created = Review.objects.update_or_create(product=p, user=request.user, defaults={"author": request.user.first_name or request.user.email.split("@")[0], "location": pr.city,
        "title": title, "body": body, "rating": rating, "fit": rating, "comfort": rating, "value": rating, "quality": rating, "created": timezone.now()})
    p.rating = round(p.reviews.aggregate(a=Avg("rating"))["a"] or 5, 1); p.save()
    return Response(ProductS(p, context={"request": request}).data, 201 if created else 200)

@api_view(["GET"])
def geocode_api(request):
    """Used by the checkout map to centre on the customer's pincode / city."""
    q = request.query_params; lat, lng, src = locate(q.get("pincode"), q.get("city"), q.get("state"))
    return Response({"lat": lat, "lng": lng, "source": src})

@api_view(["GET", "POST"])
def courier(request, number):
    """The delivery person's phone shares its real GPS here. No login: protected by the secret key inside the link."""
    o = get_object_or_404(Order, number=number)
    key = str(request.data.get("key", "") if request.method == "POST" else request.query_params.get("key", ""))
    if not o.courier_key or not hmac.compare_digest(o.courier_key, key): return Response({"error": "Invalid courier link."}, 403)
    if request.method == "GET":
        return Response({"number": o.number, "status": o.status, "status_label": o.get_status_display(), "name": f"{o.first_name} {o.last_name}".strip(), "phone": o.phone,
                         "address": f"{o.address}, {o.city} {o.pincode}", "dest_lat": o.dest_lat, "dest_lng": o.dest_lng, "store": settings.STORE})
    if o.status in ("delivered", "cancelled"): return Response({"error": f"This order is already {o.get_status_display().lower()}."}, 400)
    if request.data.get("action") == "delivered":
        o.status = "delivered"; o.current_lat = o.current_lng = None; o.save()
        return Response({"ok": True, "status": o.status, "status_label": o.get_status_display()})
    try: lat, lng = float(request.data.get("lat")), float(request.data.get("lng"))
    except (TypeError, ValueError): return Response({"error": "Bad location."}, 400)
    if not in_india(lat, lng): return Response({"error": "Location is outside India."}, 400)
    o.current_lat, o.current_lng = lat, lng
    if o.status in ("confirmed", "shipped"): o.status = "out_for_delivery"
    o.save()
    return Response({"ok": True, "status": o.status, "status_label": o.get_status_display()})
