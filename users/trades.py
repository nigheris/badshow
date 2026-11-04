from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from users.models import Trade, TradeParticipation, TradeWatchlist, Transaction, Wallet


CENT = Decimal("0.01")
MAX_AMOUNT = Decimal("999999999999.99")


def _money(value, label):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError(f"Enter a valid {label}.")

    if not amount.is_finite():
        raise ValidationError(f"Enter a valid {label}.")
    try:
        rounded = amount.quantize(CENT)
    except InvalidOperation:
        raise ValidationError(f"Enter a valid {label}.")
    if amount != rounded or abs(amount) > MAX_AMOUNT:
        raise ValidationError(f"Enter a valid {label}.")
    amount = rounded
    return amount


def _get_trade(trade_id):
    try:
        trade_id = int(trade_id)
    except (TypeError, ValueError):
        raise ValidationError("This trade is no longer available.")
    try:
        return Trade.objects.select_for_update().get(pk=trade_id)
    except Trade.DoesNotExist:
        raise ValidationError("This trade is no longer available.")


@transaction.atomic
def take_trade(*, user, trade_id, amount):
    trade = _get_trade(trade_id)
    if trade.status != Trade.STATUS_OPEN:
        raise ValidationError("This trade is no longer open.")

    amount = _money(amount, "investment amount")
    if amount <= 0:
        raise ValidationError("Investment amount must be greater than zero.")
    if amount < trade.minimum_investment:
        raise ValidationError(
            f"The minimum investment for this trade is ${trade.minimum_investment:.2f}."
        )

    try:
        wallet = Wallet.objects.select_for_update().get(user__user=user)
    except Wallet.DoesNotExist:
        raise ValidationError("A wallet is not available for this account.")
    balance = _money(wallet.balance, "wallet balance")

    if balance < amount:
        raise ValidationError("Your wallet balance is not sufficient for this trade.")

    wallet.balance = f"{balance - amount:.2f}"
    wallet.save(update_fields=["balance"])
    Transaction.objects.create(
        wallet=wallet,
        amount=f"-{amount:.2f}",
        status="trade-debit",
        msg=f"Trade investment: {trade.symbol} - {trade.title}",
    )
    return TradeParticipation.objects.create(user=user, trade=trade, amount=amount)


@transaction.atomic
def add_to_watchlist(*, user, trade_id):
    trade = _get_trade(trade_id)
    if trade.status != Trade.STATUS_OPEN:
        raise ValidationError("Only open trades can be added to your watchlist.")

    TradeWatchlist.objects.get_or_create(user=user, trade=trade)


@transaction.atomic
def remove_from_watchlist(*, user, trade_id):
    TradeWatchlist.objects.filter(user=user, trade_id=trade_id).delete()


@transaction.atomic
def settle_trade_participations(*, participations):
    ids = list(participations.values_list("pk", flat=True))
    rows = list(
        TradeParticipation.objects.select_for_update()
        .filter(pk__in=ids)
        .select_related("trade", "user")
        .order_by("pk")
    )

    if not rows:
        raise ValidationError("Select at least one trade position to settle.")

    for row in rows:
        if row.trade.status != Trade.STATUS_CLOSED:
            raise ValidationError(
                f"Close {row.trade.symbol} before settling its positions."
            )
        if row.paid_at:
            raise ValidationError("A selected position has already been settled.")
        if row.payout_amount is None:
            raise ValidationError(
                f"Enter a payout amount for {row.user.username}'s {row.trade.symbol} position."
            )

    wallets = {}
    balances = {}
    settlements = []
    for row in rows:
        payout = _money(row.payout_amount, "payout amount")
        if payout < 0:
            raise ValidationError("Payout amounts cannot be negative.")
        if row.user_id not in wallets:
            wallet = Wallet.objects.select_for_update().filter(
                user__user_id=row.user_id
            ).first()
            if wallet is None:
                raise ValidationError(
                    f"A wallet is not available for {row.user.username}."
                )
            wallets[row.user_id] = wallet
            balances[row.user_id] = _money(wallet.balance, "wallet balance")
        wallet = wallets[row.user_id]
        balance = balances[row.user_id]
        new_balance = balance + payout
        if new_balance > MAX_AMOUNT:
            raise ValidationError("The payout would exceed the supported wallet balance.")
        balances[row.user_id] = new_balance
        settlements.append((row, wallet, payout))

    for wallet_id, wallet in wallets.items():
        wallet.balance = f"{balances[wallet_id]:.2f}"
        wallet.save(update_fields=["balance"])

    for row, wallet, payout in settlements:
        Transaction.objects.create(
            wallet=wallet,
            amount=f"{payout:.2f}",
            status="credit",
            msg=f"Trade payout: {row.trade.symbol} - {row.trade.title}",
        )
        row.paid_at = timezone.now()
        row.save(update_fields=["paid_at"])
