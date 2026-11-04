from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import CommandError
from django.core.management import call_command
from django.test import TestCase, override_settings

from users.models import Trade, TradeParticipation, TradeWatchlist, Transaction
from users.trades import settle_trade_participations, take_trade


class ProfileImageSaveTests(TestCase):
    def setUp(self):
        self.media_root = TemporaryDirectory()
        self.addCleanup(self.media_root.cleanup)
        media_settings = override_settings(MEDIA_ROOT=self.media_root.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)

        self.profile = User.objects.create_user(username="profile-test").profile

    @patch("users.models.image_resize")
    def test_saving_profile_with_unchanged_image_skips_image_resize(self, image_resize):
        self.profile.phone_number = "555-0100"

        self.profile.save()

        image_resize.assert_not_called()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.phone_number, "555-0100")

    @patch("users.models.image_resize")
    def test_saving_profile_with_replaced_image_resizes_image(self, image_resize):
        self.profile.image = SimpleUploadedFile(
            "avatar.png", b"image content", content_type="image/png"
        )

        self.profile.save()

        image_resize.assert_called_once_with(self.profile.image, 512, 512)


class TradeInvestmentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="trade-investor")
        self.wallet = self.user.profile.wallet
        self.wallet.balance = "1000.00"
        self.wallet.save(update_fields=["balance"])
        self.trade = Trade.objects.create(
            title="Example opportunity",
            symbol="EXM",
            entry_price="25.00",
            target_price="30.00",
            minimum_investment="100.00",
        )

    def test_taking_trade_debits_wallet_and_records_transaction(self):
        position = take_trade(user=self.user, trade_id=self.trade.pk, amount="250.00")

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, "750.00")
        self.assertEqual(position.amount, Decimal("250.00"))
        transaction = Transaction.objects.get(wallet=self.wallet)
        self.assertEqual(transaction.status, "trade-debit")
        self.assertEqual(transaction.amount, "-250.00")

    def test_taking_trade_rejects_amount_below_minimum(self):
        with self.assertRaises(ValidationError):
            take_trade(user=self.user, trade_id=self.trade.pk, amount="99.99")

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, "1000.00")
        self.assertFalse(TradeParticipation.objects.exists())

    def test_taking_trade_rejects_insufficient_wallet_balance(self):
        with self.assertRaises(ValidationError):
            take_trade(user=self.user, trade_id=self.trade.pk, amount="1000.01")

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, "1000.00")
        self.assertFalse(TradeParticipation.objects.exists())

    def test_settling_closed_trade_credits_wallet_once(self):
        position = take_trade(user=self.user, trade_id=self.trade.pk, amount="250.00")
        second_position = take_trade(
            user=self.user, trade_id=self.trade.pk, amount="100.00"
        )
        self.trade.status = Trade.STATUS_CLOSED
        self.trade.save(update_fields=["status"])
        position.payout_amount = Decimal("275.00")
        position.save(update_fields=["payout_amount"])
        second_position.payout_amount = Decimal("120.00")
        second_position.save(update_fields=["payout_amount"])

        settle_trade_participations(
            participations=TradeParticipation.objects.filter(
                pk__in=[position.pk, second_position.pk]
            )
        )

        self.wallet.refresh_from_db()
        position.refresh_from_db()
        self.assertEqual(self.wallet.balance, "1045.00")
        self.assertIsNotNone(position.paid_at)
        self.assertEqual(
            Transaction.objects.filter(wallet=self.wallet, status="credit").count(), 2
        )

        with self.assertRaises(ValidationError):
            settle_trade_participations(
                participations=TradeParticipation.objects.filter(
                    pk__in=[position.pk, second_position.pk]
                )
            )

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, "1045.00")


class SeedDemoTradesCommandTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="demo-investor")
        self.wallet = self.user.profile.wallet
        self.wallet.balance = "1000.00"
        self.wallet.save(update_fields=["balance"])

    def test_command_creates_profile_specific_demo_trades_and_positions(self):
        call_command("seed_demo_trades", username=self.user.username, verbosity=0)

        demo_trades = Trade.objects.filter(demo_owner=self.user, is_demo=True)
        self.assertEqual(demo_trades.count(), 6)
        self.assertEqual(
            TradeParticipation.objects.filter(user=self.user).count(), 4
        )
        self.assertEqual(
            TradeWatchlist.objects.filter(user=self.user).count(), 2
        )
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, "300.00")
        self.assertEqual(
            Transaction.objects.filter(
                wallet=self.wallet, status="trade-debit"
            ).count(),
            4,
        )
        self.assertEqual(
            demo_trades.filter(status=Trade.STATUS_CLOSED).count(), 2
        )

    def test_command_is_idempotent_and_does_not_double_debit(self):
        call_command("seed_demo_trades", username=self.user.username, verbosity=0)
        call_command("seed_demo_trades", username=self.user.username, verbosity=0)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, "300.00")
        self.assertEqual(Trade.objects.filter(demo_owner=self.user).count(), 6)
        self.assertEqual(TradeParticipation.objects.filter(user=self.user).count(), 4)

    def test_command_rolls_back_if_wallet_cannot_fund_sample_positions(self):
        self.wallet.balance = "10.00"
        self.wallet.save(update_fields=["balance"])

        with self.assertRaises(CommandError):
            call_command("seed_demo_trades", username=self.user.username, verbosity=0)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, "10.00")
        self.assertFalse(Trade.objects.filter(demo_owner=self.user).exists())
        self.assertFalse(Transaction.objects.filter(wallet=self.wallet).exists())
