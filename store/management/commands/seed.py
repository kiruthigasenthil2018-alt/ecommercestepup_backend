import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from datetime import date, timedelta
from store.models import *

BLK, BRN, WHT, BLU, RED, GRY = "black", "brown", "white", "blue", "red", "grey"
# brand, name, gender, style, price, rating, colors, image, trending
P = [
("", "Ophelia Womens Silver Diamante Heel", "women", "Heels", 2299, 5, [GRY], "heel-ophelia", 1),
("", "Billie Womens Silver Diamante Heel", "women", "Heels", 3000, 5, [GRY], "heel-billie", 1),
("", "Drew Womens Blush Diamante Slip On Shoe", "women", "Shoes", 2599, 4, [WHT], "drew-blush", 1),
("", "Drew Womens Navy Diamante Slip On Shoe", "women", "Shoes", 1299, 5, [BLU], "drew-navy", 1),
("", "Weaver Mens Navy Lace Up Trainer", "men", "Trainers", 2799, 5, [BLK, BLU], "weaver-navy", 1),
("", "Weaver Mens White Lace Up Trainer", "men", "Trainers", 2259, 5, [WHT, BLK], "weaver-white", 1),
("", "Calista Girls Pink Daisy Print Sandal", "kids", "Sandals", 2899, 5, ["pink"], "calista", 1),
("", "Colby Boys Blue Dinosaur Canvas", "kids", "Canvas", 3299, 5, [BLU], "colby", 1),
("Comfy Steps", "Harlan Mens Tan Boat Shoe", "men", "Shoes", 2799, 5, [BLK, BRN, WHT], "boat1", 0),
("XL", "Weaver Mens Lace Up Trainer", "men", "Trainers", 1799, 5, [BLK, RED, WHT], "xl-trainer", 0),
("", "Doubal Strap Sandals", "men", "Sandals", 2999, 4, [BLK, BRN, WHT], "strap-sandal", 0),
("Comfy Steps", "Lustral White Leather Slippers", "men", "Slippers", 1995, 5, [BRN, WHT], "white-slipper", 0),
("Osaga", "Neptune Mens Lace Up Trainer", "men", "Trainers", 2799, 5, [BLK, BLU, WHT], "osaga", 0),
("", "Mateo Leather Lace-up Sneakers", "men", "Shoes", 3999, 5, [BLK, BRN, WHT], "mateo", 0),
("Urban Territory", "Beaumont Mens Black Warm Boots", "men", "Boots", 2799, 5, [BLK, BRN, WHT], "urban-black", 0),
("Urban Territory", "Bill Mens Brown Lace Up Boots", "men", "Boots", 2999, 4, [BLK, BRN], "urban-brown", 0),
("", "Leather Ethnic Sandals", "men", "Sandals", 2995, 4, [BRN], "ethnic", 0),
("", "Herfa Hand Painted Tan Leather Sandals", "men", "Sandals", 4999, 4, [BRN], "herfa", 0),
("", "Lucas Luxury Leather Loafers", "men", "Shoes", 9999, 5, [BLK, BRN], "lucas", 0),
("", "Lenore Tan Leather Formal Loafers", "men", "Shoes", 7399, 5, ["tan"], "lenore", 0),
("Lunar", "Tancy Womens Lilac Sandal", "women", "Sandals", 2799, 5, [BLK, BRN, WHT], "lunar", 0),
("Lilley", "Drew Womens Diamante Slip Shoe", "women", "Shoes", 3799, 5, [BLK, WHT], "lilley-drew", 0),
("Softlites", "Selina Womens Navy Sandal", "women", "Sandals", 2699, 4, [BLK, BRN, WHT], "softlites", 0),
("", "Sadie Womens Floral Beach Mule", "women", "Slippers", 2799, 5, [BLK, BRN, BLU], "shoezone-mule", 0),
("Truffle", "Ophelia Womens Silver Heel", "women", "Heels", 5999, 5, [GRY], "truffle", 0),
("Lilley", "Audrey Womens Patent Lace Shoe", "women", "Shoes", 3799, 5, [BLK, BRN, WHT], "lilley-patent", 0),
("", "Noelle Mesh Bow Ballerinas", "women", "Shoes", 3599, 4, [BLK, BRN], "noelle", 0),
("", "Stella Flat Embellished Sliders", "women", "Sandals", 1999, 4, [BLK, BRN, WHT], "stella", 0),
("", "Olivia Pencil Heels", "women", "Heels", 3199, 5, [BLK], "olivia", 0),
("", "Amelia Kitten Heels", "women", "Heels", 3699, 4, ["tan"], "amelia", 0),
("Beckett", "Beckett Sandals", "women", "Sandals", 2599, 5, [BLK, GRY, WHT], "beckett", 0),
("", "Gitano Flat Back Elastic Sandals", "women", "Sandals", 1799, 4, ["tan"], "gitano", 0),
("", "Whitby Girls White Multi Marble EVA Clog", "kids", "Sandals", 2799, 4, ["multi"], "whitby", 0),
("Walkright", "Claudia Girls Blue Fasten Canvas", "kids", "Canvas", 3199, 4, [BLU], "claudia", 0),
("Walkright", "Carey Girls Pink Polka Dot Canvas", "kids", "Canvas", 2699, 4, [BLU, "pink"], "carey", 0),
("Walkright", "Charlotte Girls Multi T-Bar Sandal", "kids", "Sandals", 4799, 5, ["multi"], "charlotte", 0),
("The Slipper Company", "Cherish Girls Pink Bootie", "kids", "Slippers", 2999, 4, ["pink"], "bootie", 0),
("LOL", "Surprise Kids Fasten Slipper", "kids", "Slippers", 2799, 5, ["multi"], "lol", 0),
("Bluey", "Kids Blue Easy Fasten Slipper", "kids", "Slippers", 4999, 5, [BLU], "bluey", 0),
("Spider-Man", "Kids Red Light Up Trainer", "kids", "Trainers", 5799, 4, ["multi"], "spiderman", 0),
("Disney Stitch", "Fairground Kids Multi EVA Clog", "kids", "Sandals", 3999, 5, ["multi"], "stitch", 0),
("Disney Frozen", "Sparkle Kids Purple Sandal", "kids", "Sandals", 5599, 4, ["purple"], "frozen", 0),
("", "Shower Kids Black Welly Size 11 to 6", "kids", "Boots", 4999, 5, [BLK, BRN, WHT], "welly", 0),
("", "Hurricane Glitter Unicorn Welly", "kids", "Boots", 2799, 4, ["purple"], "unicorn", 0),
]
SIZES = {"men": [41, 42, 43, 44, 45], "women": [3, 4, 5, 6, 7], "kids": [3, 4, 5, 6, 7]}
DESC = ("Crafted for everyday comfort, this pair from StepUp.in features a cushioned footbed, a durable gripped outsole and "
        "a secure fit that keeps you steady from morning to night.")

class Command(BaseCommand):
    help = "Seed products, a demo review and an admin user"
    def handle(self, *a, **k):
        for b, n, g, s, pr, r, c, img, t in P:
            ext = "jpg" if img in ("heel-ophelia", "heel-billie", "drew-blush", "drew-navy", "weaver-navy", "weaver-white", "calista", "colby") else "png"
            gal = [f"/images/boat{i}.png" for i in range(1, 6)] if img == "boat1" else []
            cat, _ = Category.objects.get_or_create(name=s, gender=g)
            Product.objects.update_or_create(brand=b, name=n, defaults=dict(category=cat, gender=g, style=s, is_featured=bool(t), stock=50, price=pr, rating=r, colors=c, sizes=SIZES[g],
                image_path=f"/images/{img}.{ext}", gallery=gal, description=DESC, trending=bool(t)))
        h = Product.objects.get(name="Harlan Mens Tan Boat Shoe")
        h.description = ("The Harlan men's boat shoes from Comfy Steps are perfect for your casual summer outings. Featuring a tan upper with navy blue "
                         "accents and intricate white stitching, these shoes offer a trendy look. The twin elasticated gussets and lace up fastening "
                         "ensures a quick and secure fit, while the gripped outsole provides stability and security.")
        h.save()
        h.reviews.all().delete()
        for _ in range(2):
            Review.objects.create(product=h, author="Beverley", location="Weymouth", title="Super Looking",
                body="Very pleased with the super fast delivery and packaging. Shoes are very good quality and superb.")
        pwd = os.getenv("ADMIN_PASSWORD") or ("Admin@12345" if settings.DEBUG else "")
        if pwd:
            User.objects.filter(username="admin@stepup.in").delete()
            a, _ = User.objects.get_or_create(username="admin", defaults={"email": "admin@stepup.in"})
            a.email = "admin@stepup.in"; a.is_staff = a.is_superuser = True; a.first_name = "Admin"; a.set_password(pwd); a.save()
        else: self.stdout.write("ADMIN_PASSWORD not set: no admin user created. Run: python manage.py createsuperuser")
        if settings.DEBUG:  # demo customer + sample order only on your own computer
            demo, made = User.objects.get_or_create(username="demo@stepup.in", defaults={"email": "demo@stepup.in", "first_name": "Demo"})
            if made: demo.set_password("Demo@12345"); demo.save()
            if not Order.objects.filter(user=demo).exists():  # sample order so the admin tracking map has something to show
                lunar = Product.objects.get(name="Tancy Womens Lilac Sandal")
                o = Order.objects.create(user=demo, first_name="Shiva", last_name="K", email=demo.email, phone="9876543210", address="185, Main Road", city="Madurai", state="Tamil Nadu", pincode="625001",
                    payment="cod", payment_status="pay_on_delivery", subtotal=lunar.price, total=lunar.price, status="shipped", dest_lat=9.9252, dest_lng=78.1198, expected_delivery=date.today() + timedelta(days=4))
                OrderItem.objects.create(order=o, product=lunar, name=f"{lunar.brand} {lunar.name}", size="4", color="black", quantity=1, price=lunar.price)
        HomePage.objects.get_or_create(pk=1); ContactPage.objects.get_or_create(pk=1)
        if not HomeBanner.objects.exists():
            for n, (img, t, to, pos) in enumerate([("hero1.jpg", "Flat 50% Sale|kids shoes", "/shop/kids", "tl"), ("hero2.jpg", "Womens High Heels|Flat 30% offer for your|first order", "/shop/women?style=Heels", "tr"),
                    ("hero3.jpg", "Men’s wear high heel|office shoe only 40%|discount today only", "/shop/men?style=Shoes", "mr"), ("hero4.jpg", "Womens red color|high heel for party|for your first order get a free gift", "/shop/women?style=Heels", "bl")], 1):
                HomeBanner.objects.create(text=t, image_path=f"/images/{img}", link=to, position=pos, order=n)
        if settings.DEBUG: self.stdout.write("Demo customer: demo@stepup.in / Demo@12345")
        self.stdout.write("Seeded. Admin login: username admin" + (" / password Admin@12345 (change it!)" if settings.DEBUG else " / your ADMIN_PASSWORD"))
