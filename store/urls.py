from django.urls import path
from . import views as v
urlpatterns = [
    path("auth/signup/", v.signup), path("auth/verify/", v.verify), path("auth/resend/", v.resend),
    path("auth/login/", v.login), path("auth/login-otp/", v.login_otp), path("auth/login-otp/verify/", v.login_otp_verify), path("auth/google/", v.google_login), path("auth/apple/", v.apple_login), path("auth/me/", v.me),
    path("products/", v.products), path("products/<int:pk>/", v.product_detail), path("products/<int:pk>/reviews/", v.add_review), path("config/", v.config), path("geocode/", v.geocode_api), path("courier/<str:number>/", v.courier), path("offer/", v.offer),
    path("orders/", v.orders), path("orders/<str:number>/", v.order_detail), path("orders/<str:number>/invoice/", v.invoice),
    path("state/", v.state), path("profile/", v.profile), path("site/", v.site), path("enquiry/", v.enquiry), path("subscribe/", v.subscribe),
]
