from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from creyp.utils import random_string_generator, file_cleanup, image_resize

from PIL import Image
from django_countries.fields import CountryField


STATUS = (
    ("pending", "pending"),
    ("hidden", "hidden"),
    ("credit", "credit"),
    ("trade-debit", "trade debit"),
    ("processing", "processing"),
    ("confirming", "confirming"),
    ("error", "error"),
    ("failed", "failed"),
)
GENDER = (("female", "female"), ("male", "male"), ("other", "other"))


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(
        blank=True,
        upload_to="profile-image/%h/%Y/",
        default="profile-image-placeholder.png",
    )
    gender = models.CharField(max_length=15, choices=GENDER, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    country = CountryField(blank=True)
    signup_confirmation = models.BooleanField(default=False)
    deposit_before = models.BooleanField(default=False)
    referred_by = models.ForeignKey(
        "Profile", on_delete=models.CASCADE, blank=True, null=True
    )
    refer_clicks = models.IntegerField(default=0, blank=True, null=True)
    refers = models.ManyToManyField(User, related_name="refers", blank=True)
    ip_address = models.CharField(max_length=100, blank=True, null=True)
    has_upgraded = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

    @property
    def first_name(self):
        return self.user.first_name

    @property
    def last_name(self):
        return self.user.last_name

    def save(self, *args, **kwargs):
        image_changed = self._state.adding
        if self.pk:
            original_image_name = (
                type(self).objects.filter(pk=self.pk)
                .values_list("image", flat=True)
                .first()
            )
            image_changed = (
                self.image.name != original_image_name or not self.image._committed
            )

        super().save(*args, **kwargs)

        if image_changed and self.image and self.image.storage.exists(self.image.name):
            image_resize(self.image, 512, 512)


class Wallet(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE)
    btc_address = models.TextField(blank=True, null=True)
    balance = models.CharField(max_length=100, default="00.00", blank=True)
    pin = models.CharField(max_length=6, blank=True)
    amount_invested = models.CharField(max_length=100, default="00.00", blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.btc_address} - bal : {self.balance}"


class Transaction(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    amount = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=15, choices=STATUS)
    msg = models.TextField(blank=True)
    transactionId = models.CharField(max_length=17, blank=True)
    hash_id = models.CharField(max_length=17, blank=True, null=True, unique=True)
    timestamp = models.DateTimeField(auto_now_add=True, blank=True)

    class Meta:
        ordering = ["-timestamp", "-id"]

    def __str__(self):
        return f"user has {self.wallet.balance} | TID: {self.transactionId}"

    def save(self, *args, **kwargs):
        self.hash_id = random_string_generator(size=17)
        super().save(*args, **kwargs)


class AdminWallet(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    btc_address = models.TextField(unique=True)
    returns = models.CharField(max_length=100, blank=True)
    bad = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.btc_address}"


class AdminTransaction(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    plan = models.CharField(max_length=100, blank=True)
    amount = models.CharField(max_length=100, blank=True)
    btc_address = models.TextField()
    msg = models.TextField(blank=True)
    transactionId = models.CharField(max_length=17, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        if self.plan == "withdraw":
            return f"{self.wallet.btc_address} debited ${self.amount}"
        else:
            return f"{self.wallet.btc_address} transfered ${self.amount}"


class Trade(models.Model):
    STATUS_OPEN = "open"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = (
        (STATUS_OPEN, "Open"),
        (STATUS_CLOSED, "Closed"),
    )

    title = models.CharField(max_length=120)
    symbol = models.CharField(max_length=20)
    description = models.TextField(blank=True)
    is_demo = models.BooleanField(default=False)
    demo_owner = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="demo_trades",
    )
    entry_price = models.DecimalField(
        max_digits=14, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    target_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
    )
    minimum_investment = models.DecimalField(
        max_digits=14, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_OPEN
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.symbol} - {self.title}"


class TradeParticipation(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    trade = models.ForeignKey(Trade, on_delete=models.PROTECT, related_name="positions")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    payout_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        help_text="Amount to credit when an admin settles this closed trade position.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    @property
    def is_closed(self):
        return self.trade.status == Trade.STATUS_CLOSED

    def __str__(self):
        return f"{self.user.username} - {self.trade.symbol} - ${self.amount}"


class TradeWatchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    trade = models.ForeignKey(Trade, on_delete=models.PROTECT, related_name="watchers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "trade"], name="unique_user_trade_watchlist"
            )
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} watching {self.trade.symbol}"


@receiver(post_save, sender=User)
def update_profile_signal(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()


@receiver(post_save, sender=Profile)
def update_wallet_signal(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance)


post_delete.connect(
    file_cleanup, sender=Image, dispatch_uid="profile.image.file_cleanup"
)
