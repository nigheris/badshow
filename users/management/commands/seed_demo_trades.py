from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from users.models import Trade, TradeParticipation, TradeWatchlist, Wallet
from users.trades import take_trade


DEMO_TRADES = (
    {
        "symbol": "DEMO-BTC",
        "title": "Demo - Bitcoin momentum",
        "description": "Sample open position for testing the trades dashboard.",
        "entry_price": Decimal("67500.00"),
        "target_price": Decimal("71250.00"),
        "minimum_investment": Decimal("100.00"),
        "investment": Decimal("250.00"),
    },
    {
        "symbol": "DEMO-ETH",
        "title": "Demo - Ethereum trend",
        "description": "Sample open position and watchlist entry.",
        "entry_price": Decimal("2450.00"),
        "target_price": Decimal("2700.00"),
        "minimum_investment": Decimal("50.00"),
        "investment": Decimal("150.00"),
        "watch": True,
    },
    {
        "symbol": "DEMO-SOL",
        "title": "Demo - Solana watch",
        "description": "Sample open opportunity saved to the watchlist.",
        "entry_price": Decimal("148.00"),
        "target_price": Decimal("165.00"),
        "minimum_investment": Decimal("25.00"),
        "investment": None,
        "watch": True,
    },
    {
        "symbol": "DEMO-NVDA",
        "title": "Demo - Nvidia breakout",
        "description": "Sample open opportunity to try taking a trade.",
        "entry_price": Decimal("142.00"),
        "target_price": Decimal("155.00"),
        "minimum_investment": Decimal("100.00"),
        "investment": None,
    },
    {
        "symbol": "DEMO-TSLA",
        "title": "Demo - Tesla swing",
        "description": "Sample closed position awaiting admin settlement.",
        "entry_price": Decimal("315.00"),
        "target_price": Decimal("340.00"),
        "minimum_investment": Decimal("100.00"),
        "investment": Decimal("200.00"),
        "close_after_seed": True,
    },
    {
        "symbol": "DEMO-GOLD",
        "title": "Demo - Gold position",
        "description": "Sample closed position awaiting admin settlement.",
        "entry_price": Decimal("2750.00"),
        "target_price": Decimal("2825.00"),
        "minimum_investment": Decimal("100.00"),
        "investment": Decimal("100.00"),
        "close_after_seed": True,
    },
)


class Command(BaseCommand):
    help = (
        "Create clearly labeled sample trades for one username. "
        "The initial sample positions debit $700 from that user's real wallet. "
        "Run this only for an account intended for testing."
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        username = options["username"]
        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as error:
            raise CommandError(f"No user exists with username {username!r}.") from error

        try:
            Wallet.objects.get(user__user=user)
        except Wallet.DoesNotExist as error:
            raise CommandError(
                f"User {username!r} does not have a wallet. No demo data was created."
            ) from error

        trades = {}
        created_count = 0
        for sample in DEMO_TRADES:
            defaults = {
                key: value
                for key, value in sample.items()
                if key in {
                    "title",
                    "description",
                    "entry_price",
                    "target_price",
                    "minimum_investment",
                }
            }
            trade, created = Trade.objects.get_or_create(
                demo_owner=user,
                symbol=sample["symbol"],
                is_demo=True,
                defaults=defaults,
            )
            trades[sample["symbol"]] = (trade, sample)
            created_count += int(created)

        position_count = 0
        for trade, sample in trades.values():
            investment = sample["investment"]
            if investment is None:
                continue

            position_exists = TradeParticipation.objects.filter(
                user=user, trade=trade
            ).exists()
            if not position_exists:
                if trade.status != Trade.STATUS_OPEN:
                    raise CommandError(
                        f"{trade.symbol} is closed but has no demo position. "
                        "Reopen it in Django admin before seeding."
                    )
                try:
                    take_trade(user=user, trade_id=trade.pk, amount=investment)
                except ValidationError as error:
                    raise CommandError(
                        f"Could not create the demo position for {trade.symbol}: "
                        f"{' '.join(error.messages)}. No demo data was created."
                    ) from error
                position_count += 1

            if sample.get("close_after_seed") and trade.status == Trade.STATUS_OPEN:
                trade.status = Trade.STATUS_CLOSED
                trade.save(update_fields=["status", "updated_at"])

        watchlist_count = 0
        for trade, sample in trades.values():
            if not sample.get("watch") or trade.status != Trade.STATUS_OPEN:
                continue
            _, created = TradeWatchlist.objects.get_or_create(user=user, trade=trade)
            watchlist_count += int(created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo trades ready for {username}: "
                f"{created_count} listings created, "
                f"{position_count} wallet-debited positions created, "
                f"{watchlist_count} watchlist entries created."
            )
        )
