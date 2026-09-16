from django.db import models
from django.contrib.auth.models import User


class Business(models.Model):

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="businesses"
    )

    CATEGORY_CHOICES = [
        ("food", "Restaurants & Food"),
        ("shopping", "Shopping & Retail"),
        ("electronics", "Electronics & Computers"),
        ("home", "Home & Living"),
        ("beauty", "Health & Beauty"),
        ("transport", "Transport & Logistics"),
        ("education", "Education & Training"),
        ("services", "Business Services"),
        ("sports", "Sports & Recreation"),
        ("pets", "Pets & Animals"),
        ("travel", "Travel & Tourism"),
        ("other", "Other Services"),
    ]

    name = models.CharField(max_length=200)

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES
    )

    phone = models.CharField(max_length=30)

    email = models.EmailField()

    description = models.TextField()

    city = models.CharField(max_length=100)

    region = models.CharField(max_length=100)

    opening_time = models.TimeField(
        null=True,
        blank=True
    )

    closing_time = models.TimeField(
        null=True,
        blank=True
    )

    logo = models.ImageField(
        upload_to="business_logos/",
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Package(models.Model):

    STATUS_CHOICES = [
        ("received", "Package Received"),
        ("transit", "In Transit"),
        ("delivery", "Out for Delivery"),
        ("delivered", "Delivered"),
    ]

    tracking_number = models.CharField(
        max_length=50,
        unique=True
    )

    sender_name = models.CharField(
        max_length=100
    )

    receiver_name = models.CharField(
        max_length=100
    )

    receiver_phone = models.CharField(
        max_length=30
    )

    origin = models.CharField(
        max_length=150
    )

    destination = models.CharField(
        max_length=150
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="received"
    )

    current_location = models.CharField(
        max_length=150,
        blank=True
    )
    latitude = models.FloatField(
    null=True,
    blank=True
    )

    longitude = models.FloatField(
    null=True,
    blank=True
    )
    destination_latitude = models.FloatField(
    null=True,
    blank=True
)

    destination_longitude = models.FloatField(
    null=True,
    blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.tracking_number


class TrackingUpdate(models.Model):

    package = models.ForeignKey(
        Package,
        on_delete=models.CASCADE,
        related_name="updates"
    )

    status = models.CharField(
        max_length=20,
        choices=Package.STATUS_CHOICES
    )

    location = models.CharField(
        max_length=150
    )
    latitude = models.FloatField(
    null=True,
    blank=True
    )

    longitude = models.FloatField(
    null=True,
    blank=True
    )

    description = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.package.tracking_number} - {self.location}"

    