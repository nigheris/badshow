from django import forms
from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import ValidationError

from users.models import (
    AdminTransaction,
    AdminWallet,
    Profile,
    Trade,
    TradeParticipation,
    TradeWatchlist,
    Transaction,
    Wallet,
)
from users.trades import settle_trade_participations


class TradeAdminForm(forms.ModelForm):
    class Meta:
        model = Trade
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        is_demo = cleaned_data.get("is_demo")
        demo_owner = cleaned_data.get("demo_owner")
        if is_demo and not demo_owner:
            self.add_error("demo_owner", "Choose an owner for this demo trade.")
        elif demo_owner and not is_demo:
            self.add_error("is_demo", "Mark this trade as a demo to set an owner.")
        return cleaned_data

    def clean_status(self):
        status = self.cleaned_data["status"]
        if (
            status == Trade.STATUS_OPEN
            and self.instance.pk
            and self.instance.positions.filter(paid_at__isnull=False).exists()
        ):
            raise forms.ValidationError(
                "A trade with settled positions cannot be reopened."
            )
        return status


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    form = TradeAdminForm
    list_display = (
        "title",
        "symbol",
        "is_demo",
        "demo_owner",
        "entry_price",
        "target_price",
        "minimum_investment",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("title", "symbol", "description")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "title",
                    "symbol",
                    "description",
                    "is_demo",
                    "demo_owner",
                    "entry_price",
                    "target_price",
                    "minimum_investment",
                    "status",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(TradeParticipation)
class TradeParticipationAdmin(admin.ModelAdmin):
    list_display = (
        "trade",
        "user",
        "amount",
        "payout_amount",
        "paid_at",
        "created_at",
    )
    list_filter = ("trade__status", "paid_at", "created_at")
    search_fields = ("trade__title", "trade__symbol", "user__username", "user__email")
    readonly_fields = ("user", "trade", "amount", "created_at", "paid_at")
    actions = ("settle_positions",)

    @admin.action(description="Pay out selected positions on closed trades")
    def settle_positions(self, request, queryset):
        try:
            settle_trade_participations(participations=queryset)
        except ValidationError as error:
            self.message_user(
                request, " ".join(error.messages), level=messages.ERROR
            )
        else:
            self.message_user(
                request, "Selected trade positions were paid out.", level=messages.SUCCESS
            )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.paid_at:
            fields.append("payout_amount")
        return fields


@admin.register(TradeWatchlist)
class TradeWatchlistAdmin(admin.ModelAdmin):
    list_display = ("user", "trade", "created_at")
    list_filter = ("trade__status", "created_at")
    search_fields = ("user__username", "trade__title", "trade__symbol")
    readonly_fields = ("user", "trade", "created_at")

    def has_add_permission(self, request):
        return False


admin.site.register(AdminWallet)
admin.site.register(AdminTransaction)
admin.site.register(Profile)
admin.site.register(Wallet)
admin.site.register(Transaction)
