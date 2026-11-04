from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.middleware.csrf import get_token
from django.views.decorators.http import require_POST

from django_countries import countries
from users.models import (
    AdminWallet,
    Profile,
    Trade,
    TradeParticipation,
    TradeWatchlist,
    Transaction,
    Wallet,
)
from users.decorators import update_user_ip, deposit_before
from users.trades import add_to_watchlist, remove_from_watchlist, take_trade


@update_user_ip
@deposit_before
def dashboard_home_view(request):
    if request.user.is_authenticated:
        if not Wallet.objects.filter(user=request.user.profile):
            Wallet.objects.create(user=request.user.profile)
        qs = Wallet.objects.filter(user=request.user.profile).first()
        bal = f"{float(qs.balance)}".split(".")
        first_bal = bal[0]
        second_bal = bal[1]
        transactions = Transaction.objects.filter(wallet=request.user.profile.wallet)
        visible_transactions = transactions.exclude(status="hidden")
        amount_invested = float(qs.amount_invested)
        if amount_invested == 0:
            for transaction in (
                transactions.exclude(status="pending")
                .exclude(status="processing")
                .exclude(status="confirming")
                .exclude(status="error")
                .exclude(status="failed")
            ):
                amount_invested += float(transaction.amount)

        context = {
            "title": "Dashboard",
            "crumbs": ["Dashboard"],
            "bal": qs.balance,
            "first_bal": first_bal,
            "amount_invested": amount_invested,
            "second_bal": second_bal,
            "crumbs_count": 1,
            "transactions": visible_transactions,
            "dashboard_data": {
                "balance": str(qs.balance),
                "invested": str(amount_invested),
                "transactionCount": visible_transactions.count(),
                "userName": request.user.get_full_name() or request.user.username,
                "transactions": [
                    {
                        "id": transaction.pk,
                        "status": transaction.status,
                        "msg": transaction.msg,
                        "amount": transaction.amount,
                        "transactionId": transaction.transactionId,
                        "timestamp": transaction.timestamp.isoformat(),
                    }
                    for transaction in visible_transactions[:8]
                ],
                "urls": {
                    "deposit": reverse("deposit"),
                    "payments": reverse("dashboard-payment"),
                    "referral": reverse("dashboard-referral"),
                    "profile": reverse("dashboard-profile"),
                },
            },
        }
        return render(request, "dashboard/dashboard_home.html", context)
    else:
        redirect("/auth/account/login?next=/dashboard/")


@update_user_ip
def dashboard_profile_view(request):
    if request.user.is_authenticated:
        if not Wallet.objects.filter(user=request.user.profile):
            Wallet.objects.create(user=request.user.profile)
        context = {
            "title": "Profile",
            "crumbs": ["Profile"],
            "crumbs_count": 2,
            "countries": countries,
        }
        return render(request, "dashboard/dashboard_profile.html", context)
    else:
        redirect("/auth/account/login?next=/dashboard/profile/")


@update_user_ip
def dashboard_profile_auth_view(request):
    if request.method == "POST":
        form = request.POST
        profile_image = form.get("profile_image")
        if "profile_image" in request.FILES:
            profile_image = request.FILES["profile_image"]
        full_name = form.get("full_name").strip()
        full_name_list = full_name.split(" ")
        full_name = []
        for name in full_name_list:
            full_name.append(name.strip())
        email = form.get("email").strip()
        phone_number = form.get("phone_number").strip()
        gender = form["gender"]
        country = form["country"]

        user = request.user
        user_ = User.objects.filter(username=user.username).first()
        user_profile = Profile.objects.filter(user=user).first()

        try:
            if len(full_name) > 1:
                user_.first_name = full_name[0]
                # user_profile.first_name = full_name[0]
                user_.last_name = full_name[1]
                # user_profile.last_name = full_name[1]
            elif len(full_name) == 1:
                user_.first_name = full_name[0]
                # user_profile.first_name = full_name[0]

        except:
            user_.first_name = ""
            # user_profile.first_name = ""

            user_.last_name = ""
            # user_profile.last_name = ""

        user_.email = email

        # deleting old uploaded image.
        # image_path = user_profile.image
        # if os.path.exists(image_path):
        #     os.remove(image_path)

        user_profile.email = email
        user_profile.image = profile_image
        user_profile.phone_number = phone_number
        user_profile.gender = gender
        user_profile.country = country

        user_.save()
        user_profile.save()

        return redirect(
            "/dashboard/profile/?success=yes&msg=your+profile+has+been+updated"
        )
    return redirect("dashboard-profile")


@update_user_ip
@deposit_before
def dashboard_payments_view(request):
    if request.user.is_authenticated:
        if not Wallet.objects.filter(user=request.user.profile):
            Wallet.objects.create(user=request.user.profile)
        qs = Wallet.objects.filter(user=request.user.profile).first()
        bal = f"{float(qs.balance)}".split(".")
        first_bal = bal[0]
        second_bal = bal[1]
        transactions = Transaction.objects.filter(wallet=request.user.profile.wallet)
        amount_invested = float(qs.amount_invested)
        if amount_invested == 0:
            for transaction in (
                transactions.exclude(status="pending")
                .exclude(status="processing")
                .exclude(status="confirming")
                .exclude(status="error")
                .exclude(status="failed")
            ):
                amount_invested += float(transaction.amount)
        context = {
            "title": "Payments",
            "crumbs": ["Payment"],
            "bal": qs.balance,
            "first_bal": first_bal,
            "amount_invested": amount_invested,
            "second_bal": second_bal,
            "crumbs_count": 2,
            "transactions": transactions.exclude(status="hidden"),
        }
        return render(request, "dashboard/dashboard_payments.html", context)
    else:
        redirect("/auth/account/login?next=/dashboard/payments/")


@update_user_ip
@deposit_before
def dashboard_trades_view(request):
    if request.user.is_authenticated:
        open_trades = Trade.objects.filter(status=Trade.STATUS_OPEN)
        watchlist = TradeWatchlist.objects.filter(user=request.user).select_related(
            "trade"
        )
        positions = TradeParticipation.objects.filter(user=request.user).select_related(
            "trade"
        )

        def serialize_trade(trade):
            return {
                "id": trade.pk,
                "title": trade.title,
                "symbol": trade.symbol,
                "description": trade.description,
                "isDemo": trade.is_demo,
                "entryPrice": str(trade.entry_price),
                "targetPrice": (
                    str(trade.target_price) if trade.target_price is not None else None
                ),
                "minimumInvestment": str(trade.minimum_investment),
                "status": trade.status,
            }

        context = {
            "title": "Trades",
            "crumbs": ["Trades"],
            "crumbs_count": 2,
            "trade_data": {
                "csrfToken": get_token(request),
                "actionUrl": reverse("dashboard-trade-action"),
                "openTrades": [serialize_trade(trade) for trade in open_trades],
                "watchlist": [
                    serialize_trade(item.trade) for item in watchlist
                ],
                "positions": [
                    {
                        "id": position.pk,
                        "trade": serialize_trade(position.trade),
                        "amount": str(position.amount),
                        "status": position.trade.status,
                        "payoutAmount": (
                            str(position.payout_amount)
                            if position.payout_amount is not None
                            else None
                        ),
                        "paid": position.paid_at is not None,
                    }
                    for position in positions
                ],
                "messages": [
                    {"level": message.level_tag, "text": str(message)}
                    for message in messages.get_messages(request)
                ],
            },
        }
        return render(request, "dashboard/dashboard_trades.html", context)
    return redirect("/auth/account/login?next=/dashboard/trades/")


@login_required(login_url="account_login")
@update_user_ip
@deposit_before
@require_POST
def dashboard_trade_action_view(request):
    action = request.POST.get("action")
    trade_id = request.POST.get("trade_id")

    try:
        if action == "take":
            take_trade(
                user=request.user,
                trade_id=trade_id,
                amount=request.POST.get("amount"),
            )
            messages.success(request, "You have joined the trade.")
        elif action == "watch":
            add_to_watchlist(user=request.user, trade_id=trade_id)
            messages.success(request, "Trade added to your watchlist.")
        elif action == "unwatch":
            remove_from_watchlist(user=request.user, trade_id=trade_id)
            messages.success(request, "Trade removed from your watchlist.")
        else:
            raise ValidationError("Choose a valid trade action.")
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))

    return redirect("dashboard-trades")


@update_user_ip
@deposit_before
def dashboard_referral_view(request):
    if request.user.is_authenticated:
        user = request.user
        if not Wallet.objects.filter(user=request.user.profile):
            Wallet.objects.create(user=request.user.profile)
        refers = {"clicks": f"{user.profile.refer_clicks}"}
        context = {
            "title": "Referral",
            "crumbs": ["Referral"],
            "crumbs_count": 2,
            "refers": refers,
        }
        return render(request, "dashboard/dashboard_referral.html", context)
    else:
        redirect("/auth/account/login?next=/dashboard/referral/")

@update_user_ip
@deposit_before
def dashborad_upgrade_view(request):
    if request.user.is_authenticated:
        if not Wallet.objects.filter(user=request.user.profile):
            Wallet.objects.create(user=request.user.profile)
        qs = Wallet.objects.filter(user=request.user.profile).first()
        bal = f"{float(qs.balance)}".split(".")
        first_bal = bal[0]
        second_bal = bal[1]
        transactions = Transaction.objects.filter(wallet=request.user.profile.wallet)
        amount_invested = float(qs.amount_invested)
        if amount_invested == 0:
            for transaction in (
                transactions.exclude(status="pending")
                .exclude(status="processing")
                .exclude(status="confirming")
                .exclude(status="error")
                .exclude(status="failed")
            ):
                amount_invested += float(transaction.amount)
        context = {
            "title": "Upgrade",
            "crumbs": ["Upgrade"],
            "bal": qs.balance,
            "first_bal": first_bal,
            "amount_invested": amount_invested,
            "second_bal": second_bal,
            "crumbs_count": 2,
            "transactions": transactions.exclude(status="hidden"),
        }
        return render(request, "dashboard/dashboard_upgrade.html", context)
    else:
        redirect("/auth/account/login?next=/dashboard/upgrade/")