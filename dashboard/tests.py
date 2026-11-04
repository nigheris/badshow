from django.test import TestCase

from django.contrib.auth.models import User
from django.core.management import call_command
from django.urls import reverse

from users.models import Trade, TradeParticipation, Transaction


class DashboardTradesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="dashboard-trader")
        self.user.profile.deposit_before = True
        self.user.profile.save(update_fields=["deposit_before"])
        self.user.profile.wallet.balance = "500.00"
        self.user.profile.wallet.save(update_fields=["balance"])
        self.trade = Trade.objects.create(
            title="Example listing",
            symbol="EXM",
            description="A sample opportunity",
            entry_price="12.50",
            target_price="15.00",
            minimum_investment="50.00",
        )
        self.client.force_login(self.user)

    def test_trades_page_renders_open_trade_data(self):
        response = self.client.get(reverse("dashboard-trades"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["trade_data"]["openTrades"][0]["symbol"], "EXM"
        )

    def test_taking_trade_posts_wallet_debit(self):
        response = self.client.post(
            reverse("dashboard-trade-action"),
            {
                "action": "take",
                "trade_id": self.trade.pk,
                "amount": "125.00",
            },
        )

        self.assertRedirects(response, reverse("dashboard-trades"))
        self.user.profile.wallet.refresh_from_db()
        self.assertEqual(self.user.profile.wallet.balance, "375.00")
        self.assertEqual(TradeParticipation.objects.count(), 1)
        transaction = Transaction.objects.get(wallet=self.user.profile.wallet)
        self.assertEqual(transaction.status, "trade-debit")

    def test_taking_trade_with_invalid_amount_does_not_debit_wallet(self):
        response = self.client.post(
            reverse("dashboard-trade-action"),
            {
                "action": "take",
                "trade_id": self.trade.pk,
                "amount": "invalid",
            },
        )

        self.assertRedirects(response, reverse("dashboard-trades"))
        self.user.profile.wallet.refresh_from_db()
        self.assertEqual(self.user.profile.wallet.balance, "500.00")
        self.assertFalse(TradeParticipation.objects.exists())

    def test_watchlist_actions_add_and_remove_trade(self):
        url = reverse("dashboard-trade-action")
        self.client.post(url, {"action": "watch", "trade_id": self.trade.pk})
        response = self.client.get(reverse("dashboard-trades"))
        self.assertEqual(
            response.context["trade_data"]["watchlist"][0]["id"], self.trade.pk
        )

        self.client.post(url, {"action": "unwatch", "trade_id": self.trade.pk})
        response = self.client.get(reverse("dashboard-trades"))
        self.assertEqual(response.context["trade_data"]["watchlist"], [])

    def test_all_open_demo_trades_are_listed_but_positions_remain_private(self):
        self.user.profile.wallet.balance = "1000.00"
        self.user.profile.wallet.save(update_fields=["balance"])
        call_command("seed_demo_trades", username=self.user.username, verbosity=0)

        other_user = User.objects.create_user(username="another-trader")
        other_user.profile.deposit_before = True
        other_user.profile.save(update_fields=["deposit_before"])
        self.client.force_login(other_user)

        response = self.client.get(reverse("dashboard-trades"))

        listed_symbols = {
            trade["symbol"] for trade in response.context["trade_data"]["openTrades"]
        }
        self.assertIn("DEMO-ETH", listed_symbols)
        self.assertIn("EXM", listed_symbols)
        self.assertEqual(response.context["trade_data"]["positions"], [])
