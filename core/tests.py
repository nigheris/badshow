from django.test import TestCase
from django.template.loader import render_to_string
from django.urls import reverse


class SpecialOffersPageTests(TestCase):
    def test_special_offers_page_renders_each_offer(self):
        response = self.client.get(reverse("special-offers"), secure=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Retirement investing")
        self.assertContains(response, "Real estate bonds")
        self.assertContains(response, "Investing as a couple")

    def test_pricing_component_links_to_special_offers(self):
        rendered_pricing = render_to_string("pages/pricing.html")

        self.assertIn(reverse("special-offers"), rendered_pricing)
        self.assertIn("Explore all special offers", rendered_pricing)


class AboutPageTests(TestCase):
    def test_about_page_shows_mission_and_five_illustrative_roles(self):
        response = self.client.get(reverse("about-us"), secure=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "More people deserve a clearer path to private markets.")
        self.assertContains(response, "Family Wealth Planning Lead")
        self.assertEqual(response.content.count(b'class="about-leader-card"'), 5)
        self.assertContains(response, "does not imply a partnership")
