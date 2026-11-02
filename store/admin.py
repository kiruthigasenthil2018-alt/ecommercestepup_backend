import json
import secrets
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.db.models import Count
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html, format_html_join
from .geo import courier_pos, locate
from .models import *

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "gender", "product_count"); list_filter = ("gender",); search_fields = ("name",)
    def product_count(self, c): return c.products.count()

class ReviewInline(admin.TabularInline): model = Review; extra = 0

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("photo", "name", "brand", "category", "price", "stock", "is_available", "is_featured", "trending")
    list_display_links = ("name",); list_editable = ("price", "stock", "is_available", "is_featured", "trending")
    list_filter = ("category", "is_available", "is_featured", "trending"); search_fields = ("name", "brand"); inlines = [ReviewInline]
    actions = ["make_available", "make_unavailable", "make_featured", "make_trending"]
    def photo(self, p):
        url = p.image.url if p.image else settings.FRONTEND_URL + p.image_path
        return format_html('<img src="{}" alt="" style="height:48px;width:48px;object-fit:contain;background:#eee;border-radius:6px">', url)
    @admin.action(description="Mark selected as available")
    def make_available(self, r, qs): qs.update(is_available=True)
    @admin.action(description="Mark selected as unavailable")
    def make_unavailable(self, r, qs): qs.update(is_available=False)
    @admin.action(description="Mark selected as featured")
    def make_featured(self, r, qs): qs.update(is_featured=True)
    @admin.action(description="Mark selected as trending")
    def make_trending(self, r, qs): qs.update(trending=True)

class ItemInline(admin.TabularInline):
    model = OrderItem; extra = 0; can_delete = False
    readonly_fields = ("product", "name", "size", "color", "quantity", "price")
    def has_add_permission(self, request, obj=None): return False

STEPS = [("confirmed", "Order Confirmed"), ("shipped", "Shipped"), ("out_for_delivery", "Out for Delivery"), ("delivered", "Delivery")]

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "customer", "user", "city", "payment", "payment_status", "status", "discount", "total", "created", "tracking")
    list_display_links = ("number",); list_editable = ("status",); date_hierarchy = "created"
    list_filter = ("status", "payment", "payment_status", "city"); search_fields = ("number", "first_name", "last_name", "email", "user__email", "city")
    raw_id_fields = ("user",); inlines = [ItemInline]; actions = ["relocate", "to_shipped", "to_out", "to_delivered", "to_cancelled"]
    readonly_fields = ("number", "live_tracking", "courier_link", "dest_source", "subtotal", "discount", "total", "invoice_link")
    fieldsets = (
        ("Customer & delivery address", {"fields": ("number", "user", "first_name", "last_name", "email", "phone", "address", "landmark", "city", "state", "pincode", "dest_lat", "dest_lng", "dest_source")}),
        ("Tracking", {"fields": ("live_tracking", "courier_link", "status", "expected_delivery", "dispatched_at", "out_for_delivery_at", "delivered_at", "current_lat", "current_lng")}),
        ("Payment", {"fields": ("payment", "payment_status", "card_last4", "gift", "invoice_link")}),
        ("Totals (calculated from items below)", {"fields": ("subtotal", "discount", "total")}),
    )
    def customer(self, o): return f"{o.first_name} {o.last_name}".strip()
    def tracking(self, o): return format_html('<a class="button" href="{}">Track &amp; map</a>', reverse("admin:store_order_tracking", args=[o.pk]))
    def invoice_link(self, o): return format_html('<a href="/api/orders/{}/invoice/" target="_blank">Download bill (PDF)</a>', o.number) if o.pk else "-"
    invoice_link.short_description = "Bill"
    def live_tracking(self, o):
        if not o.pk: return "-"
        steps = format_html_join(" → ", "{}", ((format_html("<b>{}</b>", l) if k == o.status else l,) for k, l in STEPS))
        return format_html('Current: <b>{}</b><br>{}<br><a class="button" style="margin-top:6px;display:inline-block" href="{}">Open tracking map</a>',
                           o.get_status_display(), steps, reverse("admin:store_order_tracking", args=[o.pk]))
    live_tracking.short_description = "Live tracking"
    def courier_link(self, o):
        if not o.pk: return "-"
        if not o.courier_key: o.courier_key = secrets.token_urlsafe(9); o.save(update_fields=["courier_key"])
        url = f"{settings.FRONTEND_URL}/courier/{o.number}?key={o.courier_key}"
        return format_html('<a href="{0}" target="_blank">{0}</a><br><span class="help">Send this link to the delivery person. When they open it on their phone and tap "Start sharing", the customer sees the REAL GPS position live.</span>', url)
    courier_link.short_description = "Courier GPS link"
    @admin.action(description="Re-detect delivery location from the address")
    def relocate(self, request, qs):
        for o in qs: o.dest_lat, o.dest_lng, o.dest_source = locate(o.pincode, o.city, o.state); o.save()
        self.message_user(request, f"{qs.count()} order(s) re-located.", messages.SUCCESS)
    def save_model(self, request, obj, form, change):
        if change and "status" in form.changed_data and "current_lat" not in form.changed_data: obj.current_lat = obj.current_lng = None
        super().save_model(request, obj, form, change)
    def _bulk(self, request, qs, status):
        for o in qs: o.status = status; o.current_lat = o.current_lng = None; o.save()
        self.message_user(request, f"{qs.count()} order(s) updated.", messages.SUCCESS)
    @admin.action(description="Mark selected orders as Shipped")
    def to_shipped(self, r, qs): self._bulk(r, qs, "shipped")
    @admin.action(description="Mark selected orders as Out for Delivery")
    def to_out(self, r, qs): self._bulk(r, qs, "out_for_delivery")
    @admin.action(description="Mark selected orders as Delivered")
    def to_delivered(self, r, qs): self._bulk(r, qs, "delivered")
    @admin.action(description="Mark selected orders as Cancelled")
    def to_cancelled(self, r, qs): self._bulk(r, qs, "cancelled")

    def get_urls(self):
        return [path("live-map/", self.admin_site.admin_view(self.live_map), name="store_order_livemap"),
                path("<int:pk>/tracking/", self.admin_site.admin_view(self.order_tracking), name="store_order_tracking")] + super().get_urls()
    def live_map(self, request):
        rows = [{"number": o.number, "status": o.status, "city": o.city, "dest": [o.dest_lat, o.dest_lng], "pos": courier_pos(o), "url": reverse("admin:store_order_change", args=[o.pk])} for o in Order.objects.exclude(status__in=["delivered", "cancelled"])]
        return TemplateResponse(request, "admin/store/order/live_map.html", {**self.admin_site.each_context(request), "title": "Live map - all active orders", "orders": rows, "store": settings.STORE})
    def order_tracking(self, request, pk):
        o = get_object_or_404(Order, pk=pk)
        if not self.has_change_permission(request, o): raise PermissionDenied
        if request.method == "POST":
            if request.POST.get("reset"): o.current_lat = o.current_lng = None; msg = "Parcel position reset to automatic."
            elif request.POST.get("dest"):
                try: o.dest_lat, o.dest_lng = float(request.POST["lat"]), float(request.POST["lng"]); o.dest_source = "admin"; msg = "Delivery location updated."
                except (KeyError, ValueError): self.message_user(request, "Click the map first.", messages.ERROR); return redirect(request.path)
            else:
                try: o.current_lat, o.current_lng = float(request.POST["lat"]), float(request.POST["lng"]); msg = "Parcel position updated - the customer sees it on their tracking page."
                except (KeyError, ValueError): self.message_user(request, "Click the map first.", messages.ERROR); return redirect(request.path)
            o.save(); self.message_user(request, msg, messages.SUCCESS); return redirect(request.path)
        if request.GET.get("json"): return JsonResponse({"pos": courier_pos(o), "status": o.status, "label": o.get_status_display()})  # polled by the live map
        data = {"store": settings.STORE, "dest": [o.dest_lat, o.dest_lng], "pos": courier_pos(o)}
        return TemplateResponse(request, "admin/store/order/tracking.html", {**self.admin_site.each_context(request), "title": f"Tracking - {o.number}", "o": o, "data": data,
            "steps": [{"label": l, "done": i <= [s for s, _ in STEPS].index(o.status) if o.status in dict(STEPS) else False} for i, (k, l) in enumerate(STEPS)], "opts": self.model._meta})

@admin.register(WishlistItem)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "created"); list_filter = ("product__gender", "product__category"); search_fields = ("user__email", "product__name", "product__brand")
    date_hierarchy = "created"

@admin.register(UserState)
class SavedCartAdmin(admin.ModelAdmin):
    list_display = ("user", "items", "cart_value", "updated"); fields = ("user", "cart_items", "updated"); readonly_fields = fields
    def items(self, s): return sum(int(x.get("quantity", 1)) for x in s.cart)
    def cart_value(self, s): return "Rs. " + format(sum(x.get("price", 0) * x.get("quantity", 1) for x in s.cart), ",")
    def cart_items(self, s):
        if not s.cart: return "Empty"
        return format_html("<ul>{}</ul>", format_html_join("", "<li>{} (size {}, {}) x {} = Rs. {}</li>", ((x.get("name"), x.get("size"), x.get("color"), x.get("quantity"), x.get("price", 0) * x.get("quantity", 1)) for x in s.cart)))
    def has_add_permission(self, request): return False

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "city", "state", "pincode"); search_fields = ("user__email", "phone", "city")

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "author", "rating", "title", "created"); list_filter = ("rating",); search_fields = ("product__name", "author", "title"); date_hierarchy = "created"

@admin.register(Enquiry)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "created"); search_fields = ("name", "email", "message"); date_hierarchy = "created"
    readonly_fields = ("created",)

@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ("email", "expires", "attempts"); readonly_fields = ("email", "code", "password", "expires", "attempts")
    def has_add_permission(self, request): return False

admin.site.register(Subscriber)

class SingletonAdmin(admin.ModelAdmin):
    def has_add_permission(self, request): return not self.model.objects.exists()
    def has_delete_permission(self, request, obj=None): return False

@admin.register(HomePage)
class HomePageAdmin(SingletonAdmin): list_display = ("__str__", "promo_text")

@admin.register(ContactPage)
class ContactPageAdmin(SingletonAdmin): list_display = ("__str__", "orders_phone", "email", "hours")

@admin.register(HomeBanner)
class HomeBannerAdmin(admin.ModelAdmin):
    list_display = ("preview", "text", "link", "position", "order", "active"); list_display_links = ("text",); list_editable = ("order", "active")
    def preview(self, b):
        url = b.image.url if b.image else settings.FRONTEND_URL + b.image_path
        return format_html('<img src="{}" alt="" style="height:44px;width:80px;object-fit:cover;border-radius:6px">', url)

# ---- Sidebar: split the store models into "Shop" and "Website pages (Home & Contact)" ----
WEB_MODELS = ("HomeBanner", "HomePage", "ContactPage", "Enquiry")
_orig_app_list = admin.site.get_app_list
def _grouped_app_list(request, app_label=None):
    out = []
    for app in _orig_app_list(request, app_label):
        if app["app_label"] != "store": out.append(app); continue
        web = [m for m in app["models"] if m["object_name"] in WEB_MODELS]; shop = [m for m in app["models"] if m["object_name"] not in WEB_MODELS]
        if shop: out.append({**app, "name": "Shop", "models": shop})
        if web: out.append({**app, "name": "Website pages (Home & Contact)", "models": web})
    return out
admin.site.get_app_list = _grouped_app_list

# ---- Users page like the Supplyhive project ----
class ProfileInline(admin.StackedInline):
    model = Profile; can_delete = False; extra = 0
    fields = ("avatar", "phone", "address", "city", "state", "pincode", "provider", "verified", "google_linked")

admin.site.unregister(User)
@admin.register(User)
class StepUpUserAdmin(DjangoUserAdmin):
    inlines = [ProfileInline]
    list_display = ("username", "email", "name", "phone", "signed_up_with", "verified", "order_count", "wishlist_count", "date_joined", "last_login", "is_staff")
    list_filter = ("is_staff", "is_superuser", "is_active", "profile__google_linked", "date_joined")
    date_hierarchy = "date_joined"; search_fields = ("username", "email", "first_name", "profile__phone")
    def get_queryset(self, request):
        return super().get_queryset(request).select_related("profile").annotate(_orders=Count("orders", distinct=True), _wish=Count("wishlist_items", distinct=True))
    def _pf(self, u): return getattr(u, "profile", None)
    @admin.display(description="Name", ordering="first_name")
    def name(self, u): return u.first_name or "-"
    @admin.display(description="Phone")
    def phone(self, u): return (self._pf(u) and self._pf(u).phone) or "-"
    @admin.display(description="Signed up with")
    def signed_up_with(self, u): p = self._pf(u); return p.get_provider_display() if p else "Email & password"
    @admin.display(description="Verified", boolean=True)
    def verified(self, u): p = self._pf(u); return p.verified if p else True
    @admin.display(description="Orders", ordering="_orders")
    def order_count(self, u): return u._orders
    @admin.display(description="Wishlist", ordering="_wish")
    def wishlist_count(self, u): return u._wish
