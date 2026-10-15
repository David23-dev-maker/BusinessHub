
import os

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


# ============================================================
# BUSINESSHUB UPLOAD CONFIGURATION
# ============================================================

MESSAGE_ATTACHMENT_MAX_SIZE = 50 * 1024 * 1024  # 50 MB


def message_attachment_upload_path(instance, filename):
    """
    Store message attachments in conversation-specific directories.
    Files will be served through an authorization-checked view later.
    """
    extension = os.path.splitext(filename)[1].lower()

    return (
        f"message_attachments/"
        f"conversation_{instance.conversation_id}/"
        f"message_{instance.pk or 'new'}{extension}"
    )


def validate_message_attachment_size(file):
    """Reject attachments larger than 50 MB."""
    if file and file.size > MESSAGE_ATTACHMENT_MAX_SIZE:
        raise ValidationError(
            "Attachments cannot exceed 50 MB."
        )


# ============================================================
# BUSINESS
# ============================================================

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
        ("transport", "Transport & Delivery"),
        ("education", "Education & Training"),
        ("services", "Professional Services"),
        ("sports", "Sports & Fitness"),
        ("pets", "Pets & Animals"),
        ("travel", "Travel & Tourism"),
        ("other", "Other"),
    ]

    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    description = models.TextField(blank=True)
    city = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)

    logo = models.ImageField(
        upload_to="business_logos/",
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# ============================================================
# PACKAGE TRACKING
# ============================================================

class Package(models.Model):

    STATUS_CHOICES = [
        ("received", "Received"),
        ("processing", "Processing"),
        ("in_transit", "In Transit"),
        ("out_for_delivery", "Out for Delivery"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]

    tracking_number = models.CharField(max_length=50, unique=True)
    sender_name = models.CharField(max_length=200)
    receiver_name = models.CharField(max_length=200)
    receiver_phone = models.CharField(max_length=50)
    origin = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)

    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default="received"
    )

    current_location = models.CharField(
        max_length=255,
        blank=True
    )

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    destination_latitude = models.FloatField(
        null=True,
        blank=True
    )

    destination_longitude = models.FloatField(
        null=True,
        blank=True
    )

    notification_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tracked_packages"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.tracking_number


class TrackingUpdate(models.Model):

    package = models.ForeignKey(
        Package,
        on_delete=models.CASCADE,
        related_name="updates"
    )

    status = models.CharField(
        max_length=50,
        choices=Package.STATUS_CHOICES
    )

    location = models.CharField(max_length=255, blank=True)

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.package.tracking_number} - {self.status}"


# ============================================================
# MESSAGING
# ============================================================

class Conversation(models.Model):

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="conversations",
        null=True,
        blank=True
    )

    item = models.ForeignKey(
        "Item",
        on_delete=models.CASCADE,
        related_name="conversations",
        null=True,
        blank=True
    )

    food = models.ForeignKey(
        "Food",
        on_delete=models.CASCADE,
        related_name="conversations",
        null=True,
        blank=True
    )

    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="customer_conversations"
    )

    seller = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="seller_conversations",
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):

        if self.item:
            return (
                f"{self.customer.username} - "
                f"{self.item.title}"
            )

        if self.food:
            return (
                f"{self.customer.username} - "
                f"{self.food.title}"
            )

        if self.business:
            return (
                f"{self.customer.username} - "
                f"{self.business.name}"
            )

        return f"Conversation {self.id}"


class Message(models.Model):

    ATTACHMENT_KIND_CHOICES = [
        ("image", "Image"),
        ("audio", "Voice Message"),
        ("file", "File"),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages"
    )

    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_messages"
    )

    # Blank text allows a message to contain only an attachment.
    text = models.TextField(blank=True)

    attachment = models.FileField(
        upload_to=message_attachment_upload_path,
        blank=True,
        null=True,
        validators=[validate_message_attachment_size]
    )

    attachment_original_name = models.CharField(
        max_length=255,
        blank=True
    )

    attachment_content_type = models.CharField(
        max_length=100,
        blank=True
    )

    attachment_size = models.PositiveBigIntegerField(
        default=0
    )

    attachment_kind = models.CharField(
        max_length=20,
        choices=ATTACHMENT_KIND_CHOICES,
        blank=True
    )

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def clean(self):
        super().clean()

        if not self.text.strip() and not self.attachment:
            raise ValidationError(
                "A message must contain text or an attachment."
            )

        if self.attachment and self.attachment.size > MESSAGE_ATTACHMENT_MAX_SIZE:
            raise ValidationError({
                "attachment": "Attachments cannot exceed 50 MB."
            })

    def __str__(self):
        if self.text:
            preview = self.text[:40]
        elif self.attachment_original_name:
            preview = self.attachment_original_name[:40]
        else:
            preview = "Attachment"

        return f"{self.sender.username}: {preview}"


# ============================================================
# USER PRESENCE
# ============================================================

class UserPresence(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="presence"
    )

    is_online = models.BooleanField(default=False)

    last_seen = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):

        status = "Online" if self.is_online else "Offline"

        return f"{self.user.username} - {status}"


# ============================================================
# NOTIFICATIONS
# ============================================================

class Notification(models.Model):

    TYPE_CHOICES = [
        ("message", "New Message"),
        ("tracking", "Tracking Update"),
        ("business", "Business Activity"),
        ("system", "System"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    notification_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default="system"
    )

    title = models.CharField(max_length=255)
    message = models.TextField()

    link = models.CharField(max_length=500, blank=True)

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.title}"


# ============================================================
# ITEMS MARKETPLACE
# ============================================================

class Item(models.Model):

    CATEGORY_CHOICES = [
        ("electronics", "Electronics"),
        ("fashion", "Fashion & Clothing"),
        ("vehicles", "Vehicles"),
        ("home", "Home & Furniture"),
        ("beauty", "Beauty"),
        ("games", "Games & Consoles"),
        ("sports", "Sports"),
        ("books", "Books & Education"),
        ("pets", "Pets & Animals"),
        ("tools", "Tools & Equipment"),
        ("other", "Other"),
    ]

    CONDITION_CHOICES = [
        ("new", "New"),
        ("used", "Used"),
    ]

    STATUS_CHOICES = [
        ("available", "Available"),
        ("sold", "Sold"),
    ]

    seller = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="items"
    )

    title = models.CharField(max_length=200)

    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    description = models.TextField()

    condition = models.CharField(
        max_length=20,
        choices=CONDITION_CHOICES,
        default="used"
    )

    location = models.CharField(max_length=255)

    negotiable = models.BooleanField(default=False)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="available"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class ItemImage(models.Model):

    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="images"
    )

    image = models.ImageField(upload_to="item_images/")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.item.title} image"


# ============================================================
# FOOD MARKETPLACE
# ============================================================

class Food(models.Model):

    CATEGORY_CHOICES = [
        ("meals", "Meals"),
        ("cakes_desserts", "Cakes & Desserts"),
        ("meat_chicken", "Meat & Chicken"),
        ("fish_seafood", "Fish & Seafood"),
        ("snacks_pastries", "Snacks & Pastries"),
        ("fruits_vegetables", "Fruits & Vegetables"),
        ("packaged_food", "Packaged Food"),
        ("drinks", "Drinks"),
        ("catering", "Catering"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("available", "Available"),
        ("unavailable", "Unavailable"),
    ]

    seller = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="food_listings"
    )

    title = models.CharField(max_length=200)

    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    description = models.TextField()

    location = models.CharField(max_length=255)

    quantity = models.PositiveIntegerField(default=1)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="available"
    )

    pickup_available = models.BooleanField(default=True)

    delivery_available = models.BooleanField(default=False)

    delivery_information = models.CharField(
        max_length=500,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class FoodImage(models.Model):

    food = models.ForeignKey(
        Food,
        on_delete=models.CASCADE,
        related_name="images"
    )

    image = models.ImageField(upload_to="food_images/")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.food.title} image"


# ============================================================
# BUSINESSHUB PAYMENTS
# ============================================================

class Payment(models.Model):

    PAYMENT_METHOD_CHOICES = [
        ("mtn_momo", "MTN MoMo"),
        ("orange_money", "Orange Money"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("successful", "Successful"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    SERVICE_CHOICES = [
        ("subscription", "Premium Subscription"),
        ("boost", "Listing Boost"),
        ("featured", "Featured Listing"),
        ("promotion", "Promotion"),
        ("other", "Other BusinessHub Service"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    currency = models.CharField(max_length=10, default="XAF")

    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHOD_CHOICES
    )

    service_type = models.CharField(
        max_length=30,
        choices=SERVICE_CHOICES
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    transaction_id = models.CharField(max_length=255, blank=True)

    reference = models.CharField(max_length=255, unique=True)

    service_reference = models.CharField(max_length=255, blank=True)

    provider_response = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.user.username} - "
            f"{self.amount} {self.currency} - "
            f"{self.status}"
        )


class BusinessHubSubscription(models.Model):

    PLAN_CHOICES = [
        ("plus", "BusinessHub Plus"),
        ("pro", "BusinessHub Pro"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="businesshub_subscriptions"
    )

    plan = models.CharField(max_length=20, choices=PLAN_CHOICES)

    start_date = models.DateTimeField()
    expiry_date = models.DateTimeField()

    is_active = models.BooleanField(default=True)

    payment = models.OneToOneField(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscription"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.user.username} - "
            f"{self.get_plan_display()} - "
            f"{'Active' if self.is_active else 'Expired'}"
        )


# ============================================================
# BUSINESSHUB LISTING PROMOTIONS
# ============================================================

class ListingPromotion(models.Model):

    SERVICE_TYPE_CHOICES = [
        ("boost", "Listing Boost"),
        ("featured", "Featured Listing"),
        ("promotion", "Promotion"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="listing_promotions"
    )

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="promotions",
        null=True,
        blank=True
    )

    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="promotions",
        null=True,
        blank=True
    )

    food = models.ForeignKey(
        Food,
        on_delete=models.CASCADE,
        related_name="promotions",
        null=True,
        blank=True
    )

    service_type = models.CharField(
        max_length=20,
        choices=SERVICE_TYPE_CHOICES
    )

    payment = models.OneToOneField(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="listing_promotion"
    )

    start_date = models.DateTimeField()
    expiry_date = models.DateTimeField()

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):

        listing = (
            self.business.name
            if self.business
            else self.item.title
            if self.item
            else self.food.title
            if self.food
            else "Unknown Listing"
        )

        return (
            f"{listing} - "
            f"{self.get_service_type_display()}"
        )


# ============================================================
# BUSINESS ANALYTICS
# ============================================================

class BusinessView(models.Model):

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="views"
    )

    viewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="business_views"
    )

    viewed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.business.name} - {self.viewed_at}"


class BusinessReview(models.Model):

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    reviewer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="business_reviews"
    )

    rating = models.PositiveSmallIntegerField()

    comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["business", "reviewer"],
                name="unique_business_reviewer"
            )
        ]

    def __str__(self):
        return (
            f"{self.business.name} - "
            f"{self.reviewer.username} - "
            f"{self.rating}/5"
        )

