import secrets
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

class Category(models.Model):
    GENDERS = [("men", "Men"), ("women", "Women"), ("kids", "Kids")]
    name = models.CharField(max_length=60, help_text="Sandals, Trainers, Boots, Slippers, Canvas, Shoes, Heels...")
    gender = models.CharField(max_length=10, choices=GENDERS)
    class Meta: unique_together = ("name", "gender"); verbose_name_plural = "Categories"; ordering = ("gender", "name")
    def __str__(self): return f"{self.get_gender_display()} - {self.name}"

class Product(models.Model):
    GENDERS = Category.GENDERS
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="products")
    brand = models.CharField(max_length=80, blank=True)
    name = models.CharField(max_length=160)
    gender = models.CharField(max_length=10, choices=GENDERS, blank=True, help_text="Filled automatically when you pick a category")
    style = models.CharField(max_length=40, blank=True, help_text="Filled automatically from the category")
    price = models.PositiveIntegerField(help_text="MRP in INR")
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=5)
    colors = models.JSONField(default=list, help_text='e.g. ["black","brown","white"]. Leave [] for the default colours')
    sizes = models.JSONField(default=list, help_text='e.g. [41,42,43]. Leave [] for the default sizes')
    image_path = models.CharField(max_length=200, blank=True, help_text="Static path e.g. /images/lunar.png")
    image = models.ImageField(upload_to="products/", blank=True, help_text="Optional upload (overrides image path)")
    gallery = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True)
    stock = models.PositiveIntegerField(default=50)
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    trending = models.BooleanField(default=False, verbose_name="Is trending")
    created = models.DateTimeField(auto_now_add=True)
    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.category_id and not self.gender: raise ValidationError("Choose a category (or a gender) so the shoe shows on the right page.")
    def save(self, *a, **k):
        if self.category_id: self.style = self.category.name; self.gender = self.category.gender
        if not self.sizes: self.sizes = [41, 42, 43, 44, 45] if self.gender == "men" else [3, 4, 5, 6, 7]
        if not self.colors: self.colors = ["black", "brown", "white"]
        if not self.image and not self.image_path: self.image_path = "/images/logo.jpg"
        super().save(*a, **k)
    def __str__(self): return f"{self.brand} {self.name}".strip()

class Order(models.Model):
    STATUS = [("confirmed", "Order Confirmed"), ("shipped", "Shipped"), ("out_for_delivery", "Out for Delivery"), ("delivered", "Delivered"), ("cancelled", "Cancelled")]
    PAYMENT = [("cod", "Cash on Delivery"), ("upi", "UPI (QR code / UPI ID)"), ("card", "Credit / Debit Card"), ("netbanking", "Net Banking")]
    PAY_STATUS = [("pay_on_delivery", "Pay on delivery"), ("awaiting", "Awaiting payment"), ("paid", "Paid - simulated (demo, no real charge)"), ("failed", "Payment failed / cancelled")]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    number = models.CharField("Order id", max_length=20, unique=True, editable=False)
    status = models.CharField(max_length=20, default="confirmed", choices=STATUS)
    payment = models.CharField("Payment method", max_length=20, default="cod", choices=PAYMENT)
    payment_status = models.CharField(max_length=20, default="pay_on_delivery", choices=PAY_STATUS)
    card_last4 = models.CharField(max_length=4, blank=True)
    subtotal = models.PositiveIntegerField(default=0)
    discount = models.PositiveIntegerField("Discount amount", default=0, help_text="First-order offer: 50% off (up to Rs. 1,500)")
    total = models.PositiveIntegerField(default=0)
    gift = models.BooleanField("Free gift (first order)", default=False)
    first_name = models.CharField("Customer first name", max_length=60); last_name = models.CharField(max_length=60, blank=True)
    email = models.EmailField(); phone = models.CharField(max_length=20)
    address = models.CharField("Street address", max_length=250); city = models.CharField(max_length=80)
    state = models.CharField(max_length=80); pincode = models.CharField("Postal code", max_length=10)
    landmark = models.CharField(max_length=120, blank=True)
    dest_lat = models.FloatField("Latitude", null=True, blank=True); dest_lng = models.FloatField("Longitude", null=True, blank=True)
    dest_source = models.CharField("Location source", max_length=10, blank=True, help_text="pinned = customer placed the pin; admin = set by you; pincode / city / district / state = looked up from the address")
    courier_key = models.CharField(max_length=24, blank=True, editable=False)
    current_lat = models.FloatField("Parcel latitude", null=True, blank=True, help_text="Optional manual position (set it on the tracking map)")
    current_lng = models.FloatField("Parcel longitude", null=True, blank=True)
    expected_delivery = models.DateField(null=True, blank=True)
    dispatched_at = models.DateTimeField("Shipped at", null=True, blank=True)
    out_for_delivery_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField("Created at", auto_now_add=True)
    def save(self, *a, **k):
        if not self.courier_key: self.courier_key = secrets.token_urlsafe(9)
        now = timezone.now()
        if self.status in ("shipped", "out_for_delivery", "delivered"): self.dispatched_at = self.dispatched_at or now
        if self.status in ("out_for_delivery", "delivered"): self.out_for_delivery_at = self.out_for_delivery_at or now
        if self.status == "delivered":
            self.delivered_at = self.delivered_at or now
            if self.payment == "cod": self.payment_status = "paid"
        super().save(*a, **k)
        if not self.number:
            self.number = f"SH{2300000 + self.pk}"; super().save(update_fields=["number"])
    def __str__(self): return self.number

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=200); size = models.CharField(max_length=10, blank=True)
    color = models.CharField(max_length=30, blank=True); quantity = models.PositiveIntegerField(default=1)
    price = models.PositiveIntegerField()

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    avatar = models.CharField(max_length=6, choices=[("male", "Male"), ("female", "Female")], default="male")
    provider = models.CharField("Signed up with", max_length=10, choices=[("email", "Email & password"), ("google", "Google"), ("apple", "Apple")], default="email")
    verified = models.BooleanField(default=True)
    google_linked = models.BooleanField("Google linked", default=False)
    phone = models.CharField(max_length=20, blank=True); address = models.CharField(max_length=250, blank=True)
    city = models.CharField(max_length=80, blank=True); state = models.CharField(max_length=80, blank=True); pincode = models.CharField(max_length=10, blank=True)
    def __str__(self): return str(self.user)

class WishlistItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wishlist_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wished_by")
    created = models.DateTimeField(auto_now_add=True)
    class Meta: unique_together = ("user", "product"); verbose_name = "Wishlist"; verbose_name_plural = "Wishlists"; ordering = ("-created",)
    def __str__(self): return f"{self.user} - {self.product}"

class UserState(models.Model):
    """Saved shopping cart so it follows the customer across sessions / devices."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="state")
    cart = models.JSONField(default=list); updated = models.DateTimeField(auto_now=True)
    class Meta: verbose_name = "Saved cart"; verbose_name_plural = "Saved carts"
    def __str__(self): return f"Cart of {self.user}"

class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviews")
    author = models.CharField(max_length=80); location = models.CharField(max_length=80, blank=True)
    title = models.CharField(max_length=100); body = models.TextField()
    fit = models.PositiveSmallIntegerField(default=5); comfort = models.PositiveSmallIntegerField(default=5)
    value = models.PositiveSmallIntegerField(default=5); quality = models.PositiveSmallIntegerField(default=5)
    rating = models.PositiveSmallIntegerField(default=5); created = models.DateTimeField(default=timezone.now)
    class Meta: ordering = ("-created",); unique_together = ("product", "user")

class Enquiry(models.Model):
    name = models.CharField(max_length=100); email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True); message = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    class Meta: verbose_name = "Contact message"; verbose_name_plural = "Contact messages"; ordering = ("-created",)

class Subscriber(models.Model):
    email = models.EmailField(unique=True); created = models.DateTimeField(auto_now_add=True)

class EmailOTP(models.Model):
    """Pending sign-ups waiting for the emailed 6-digit code (code + password are stored hashed)."""
    email = models.EmailField(unique=True); code = models.CharField(max_length=128); password = models.CharField(max_length=128)
    expires = models.DateTimeField(); attempts = models.PositiveSmallIntegerField(default=0)
    class Meta: verbose_name = "Email OTP"; verbose_name_plural = "Email OTPs"

class HomePage(models.Model):
    """Text shown on the website Home page (edit in admin)."""
    overview = models.TextField(default="Explore our curated selection of high-quality shoes for every occasion. From durable athletic shoes designed for peak performance to stylish casual sneakers and elegant dress shoes, we offer a diverse range of footwear to suit your needs. Our user friendly interface makes it easy to browse our collection and find the perfect pair, while detailed product descriptions and high-quality images ensure you make an informed decision. Join our community of style and discover your next favorite shoe!")
    promo_text = models.CharField(max_length=160, default="Get your first order with free gift & 50 % offer")
    class Meta: verbose_name = "Home page text"; verbose_name_plural = "Home page text"
    def __str__(self): return "Home page"

class HomeBanner(models.Model):
    POS = [("tl", "Top left"), ("tr", "Top right"), ("mr", "Middle right"), ("bl", "Bottom left")]
    text = models.CharField(max_length=160, help_text="Use | for a new line, e.g. Flat 50% Sale|kids shoes")
    image_path = models.CharField(max_length=200, default="/images/hero1.jpg", help_text="e.g. /images/hero1.jpg (ignored if you upload an image)")
    image = models.ImageField(upload_to="banners/", blank=True)
    link = models.CharField(max_length=120, default="/shop", help_text="Where Shop Now goes, e.g. /shop/kids")
    position = models.CharField(max_length=2, choices=POS, default="tl")
    order = models.PositiveSmallIntegerField(default=1); active = models.BooleanField(default=True)
    class Meta: ordering = ("order",); verbose_name = "Home page banner"; verbose_name_plural = "Home page banners"
    def __str__(self): return self.text.replace("|", " ")

class ContactPage(models.Model):
    """Details shown on the Contact page and in the website footer (edit in admin)."""
    address = models.CharField(max_length=250, default="No. 14, Anna Salai, Teynampet, Chennai, Tamil Nadu 600018, India.")
    orders_phone = models.CharField("Phone - online orders / complaints", max_length=30, default="+91 98412 36547")
    queries_phone = models.CharField("Phone - other queries", max_length=30, default="+91 98410 55782")
    landline = models.CharField(max_length=30, default="044 2834 7619")
    whatsapp = models.CharField(max_length=30, default="+91 98412 36547")
    email = models.EmailField(default="customercarestepup.in@gmail.com")
    hours = models.CharField(max_length=60, default="10 AM - 7 PM")
    facebook = models.URLField("Facebook page URL", blank=True, default="https://www.facebook.com/")
    instagram = models.URLField("Instagram page URL", blank=True, default="https://www.instagram.com/")
    twitter = models.URLField("X (Twitter) page URL", blank=True, default="https://x.com/")
    meta = models.URLField("Meta page URL", blank=True, default="https://www.meta.com/")
    class Meta: verbose_name = "Contact page details"; verbose_name_plural = "Contact page details"
    def __str__(self): return "Contact page"
