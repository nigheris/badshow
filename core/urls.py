from django.urls import path
from core.views import about, contact, send_contact_email, special_offers

urlpatterns = [
    path("about-us/", about, name="about-us"),
    path("contact-us/", contact, name="contact-us"),
    path("special-offers/", special_offers, name="special-offers"),
    path("send-mail/contact-us/", send_contact_email, name="send_contact_email"),
]
