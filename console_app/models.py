from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models


# Create your models here.
class CustomUser(AbstractUser):
    user_id = models.CharField(max_length=100, null=False, blank=False)
    first_name = models.CharField(max_length=100, null=False, blank=False)
    last_name = models.CharField(max_length=100, null=False, blank=False)
    username = models.CharField(max_length=100, null=False, blank=False, unique=True)
    email = models.EmailField(max_length=250, null=False, blank=False)
    password1 = models.CharField(max_length=100, null=False, blank=False)
    password2 = models.CharField(max_length=100, null=False, blank=False)
    api_revoked = models.BooleanField(default=False)
    account_approved = models.BooleanField(default=False)
    approval_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.username


class ServiceStatus(models.Model):
    service_name = models.CharField(max_length=100, null=False, blank=False)
    service_status = models.BooleanField(default=False)

    def __str__(self):
        return self.service_name


class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    business_name = models.CharField(max_length=100, null=False, blank=False, default="Business")
    sms_sender_name = models.CharField(max_length=100, null=False, blank=False, default="Bundle")
    phone = models.PositiveIntegerField(null=True, blank=True)
    bundle_balance = models.PositiveBigIntegerField(null=True, blank=True)
    sms_api = models.CharField(max_length=250, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}"


class NewTransaction(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    account_number = models.CharField(max_length=200, blank=False, null=False)
    receiver = models.CharField(max_length=200, blank=False, null=False)
    reference = models.CharField(max_length=100, blank=False, null=False, default="Failed")
    bundle_amount = models.FloatField(blank=False, null=False)
    transaction_date = models.DateTimeField(auto_now_add=True)
    transaction_status = models.CharField(max_length=100, blank=False, null=False, default="Failed")
    batch_id = models.CharField(max_length=100, blank=False, null=False, default="Failed")
    mode_choices = (
        ("Console", "Console"),
        ("API", "API")
    )
    mode = models.CharField(choices=mode_choices, max_length=100, blank=False, null=False, default="Console")

    def __str__(self):
        return f"{self.user} {self.receiver}"


class CreditingHistory(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    amount_credited = models.FloatField(null=False, blank=False)
    date = models.DateTimeField(auto_now_add=True)
    credited = models.BooleanField(default=False)
    choices = (
        ("Paystack", "Paystack"),
        ("Manual", "Manual")
    )
    channel = models.CharField(max_length=100, null=False, blank=False, choices=choices, default="Manual")

    def __str__(self):
        return self.user.username + " " + str(self.amount_credited)


class Notice(models.Model):
    title = models.CharField(max_length=200, blank=False, null=False)
    message = models.CharField(max_length=200, blank=False, null=False)
    is_active = models.BooleanField(default=True)


class BundlePrice(models.Model):
    price = models.FloatField(null=False, blank=False)
    bundle_volume = models.FloatField(null=False, blank=False)
    active = models.BooleanField(default=True)

    def __str__(self):
        if self.bundle_volume >= 1000:
            return f"GHS{self.price} - {self.bundle_volume / 1000}GB"
        return f"GHS{self.price} - {self.bundle_volume}MB"
