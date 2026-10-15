from django import forms
from django.contrib import admin, messages
from django.utils import timezone

from geopy.geocoders import Nominatim

from .models import (
    Business,
    BusinessView,
    BusinessHubSubscription,
    Package,
    TrackingUpdate,
    Message,
    Conversation,
    Notification,
    Item,
    ItemImage,
    Food,
    FoodImage,
    Payment,
    ListingPromotion,
    BusinessReview,
    UserPresence,
)


# =================================================
# LISTING MODERATION ACTIONS
# =================================================

@admin.action(description="Hide selected listings from the public")
def hide_selected_listings(modeladmin, request, queryset):
    updated_count = queryset.update(is_hidden=True)

    modeladmin.message_user(
        request,
        f"{updated_count} listing(s) hidden from the public.",
        level=messages.SUCCESS,
    )


@admin.action(description="Restore selected listings to public view")
def restore_selected_listings(modeladmin, request, queryset):
    updated_count = queryset.update(is_hidden=False)

    modeladmin.message_user(
        request,
        f"{updated_count} listing(s) restored to public view.",
        level=messages.SUCCESS,
    )


# =================================================
# LOCATION HELPER
# =================================================

def get_coordinates(location_text):
    if not location_text:
        return None, None

    try:
        geolocator = Nominatim(
            user_agent="businesshub_tracking"
        )

        location_data = geolocator.geocode(
            location_text,
            exactly_one=True,
            language="en",
        )

        if location_data:
            return (
                float(location_data.latitude),
                float(location_data.longitude),
            )

    except Exception as error:
        print("Geocoding error:", error)

    return None, None


# =================================================
# PACKAGE ADMIN FORM
# =================================================

class PackageAdminForm(forms.ModelForm):
    tracking_number = forms.CharField(
        required=False,
        help_text="Leave blank to generate automatically.",
    )

    class Meta:
        model = Package
        fields = "__all__"


# =================================================
# TRACKING UPDATE INLINE
# =================================================

class TrackingUpdateInline(admin.TabularInline):
    model = TrackingUpdate
    extra = 1
    ordering = ("-created_at",)


# =================================================
# PACKAGE ADMIN
# =================================================

@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    form = PackageAdminForm

    list_display = (
        "tracking_number",
        "sender_name",
        "receiver_name",
        "status",
        "current_location",
        "latitude",
        "longitude",
        "origin",
        "destination",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "tracking_number",
        "sender_name",
        "receiver_name",
        "receiver_phone",
        "origin",
        "destination",
        "current_location",
    )

    readonly_fields = (
        "created_at",
    )

    inlines = [
        TrackingUpdateInline,
    ]

    def save_model(self, request, obj, form, change):
        if not obj.tracking_number:
            import uuid

            obj.tracking_number = (
                "BH-" + uuid.uuid4().hex[:8].upper()
            )

        old_status = None

        if change:
            old_package = Package.objects.get(pk=obj.pk)
            old_status = old_package.status

        if obj.destination:
            (
                destination_latitude,
                destination_longitude,
            ) = get_coordinates(obj.destination)

            if destination_latitude is not None:
                obj.destination_latitude = destination_latitude
                obj.destination_longitude = destination_longitude

        if obj.current_location:
            (
                current_latitude,
                current_longitude,
            ) = get_coordinates(obj.current_location)

            if current_latitude is not None:
                obj.latitude = current_latitude
                obj.longitude = current_longitude

        super().save_model(request, obj, form, change)

        if not change:
            TrackingUpdate.objects.create(
                package=obj,
                status=obj.status,
                location=(
                    obj.current_location
                    or "Location updating..."
                ),
                latitude=obj.latitude,
                longitude=obj.longitude,
                description=(
                    "Package created and added "
                    "to BusinessHub tracking."
                ),
            )

            if obj.notification_user:
                Notification.objects.create(
                    user=obj.notification_user,
                    notification_type="tracking",
                    title="Package created",
                    message=(
                        f"Your package {obj.tracking_number} "
                        "has been created and is ready "
                        "for tracking."
                    ),
                    link=(
                        "/tracking/?tracking_number="
                        f"{obj.tracking_number}"
                    ),
                )

        elif old_status != obj.status:
            TrackingUpdate.objects.create(
                package=obj,
                status=obj.status,
                location=(
                    obj.current_location
                    or "Location updating..."
                ),
                latitude=obj.latitude,
                longitude=obj.longitude,
                description=(
                    "Package status changed to "
                    f"{obj.get_status_display()}."
                ),
            )

            if obj.notification_user:
                if obj.status == "out_for_delivery":
                    title = "Package out for delivery"
                    message = (
                        f"Your package {obj.tracking_number} "
                        "is now out for delivery."
                    )

                elif obj.status == "delivered":
                    title = "Package delivered"
                    message = (
                        f"Your package {obj.tracking_number} "
                        "has been delivered."
                    )

                elif obj.status == "in_transit":
                    title = "Package in transit"
                    message = (
                        f"Your package {obj.tracking_number} "
                        "is now in transit."
                    )

                elif obj.status == "processing":
                    title = "Package processing"
                    message = (
                        f"Your package {obj.tracking_number} "
                        "is now being processed."
                    )

                elif obj.status == "received":
                    title = "Package received"
                    message = (
                        f"Your package {obj.tracking_number} "
                        "has been received."
                    )

                elif obj.status == "cancelled":
                    title = "Package cancelled"
                    message = (
                        f"Your package {obj.tracking_number} "
                        "has been cancelled."
                    )

                else:
                    title = "Package status updated"
                    message = (
                        f"Your package {obj.tracking_number} "
                        f"is now {obj.get_status_display()}."
                    )

                Notification.objects.create(
                    user=obj.notification_user,
                    notification_type="tracking",
                    title=title,
                    message=message,
                    link=(
                        "/tracking/?tracking_number="
                        f"{obj.tracking_number}"
                    ),
                )

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)

        for obj in instances:
            if obj.location:
                latitude, longitude = get_coordinates(
                    obj.location
                )

                if latitude is not None:
                    obj.latitude = latitude
                    obj.longitude = longitude

            obj.save()

            package = obj.package

            if obj.location:
                package.current_location = obj.location

            if obj.latitude is not None:
                package.latitude = obj.latitude

            if obj.longitude is not None:
                package.longitude = obj.longitude

            package.status = obj.status

            package.save(
                update_fields=[
                    "current_location",
                    "latitude",
                    "longitude",
                    "status",
                ]
            )

            if package.notification_user:
                Notification.objects.create(
                    user=package.notification_user,
                    notification_type="tracking",
                    title="Package location updated",
                    message=(
                        f"Your package {package.tracking_number} "
                        "is now in "
                        f"{obj.location or 'an updated location'}."
                    ),
                    link=(
                        "/tracking/?tracking_number="
                        f"{package.tracking_number}"
                    ),
                )

        for obj in formset.deleted_objects:
            obj.delete()

        formset.save_m2m()


# =================================================
# TRACKING UPDATE ADMIN
# =================================================

@admin.register(TrackingUpdate)
class TrackingUpdateAdmin(admin.ModelAdmin):
    list_display = (
        "package",
        "status",
        "location",
        "latitude",
        "longitude",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "package__tracking_number",
        "location",
        "description",
    )

    ordering = ("-created_at",)

    def save_model(self, request, obj, form, change):
        if obj.location:
            latitude, longitude = get_coordinates(
                obj.location
            )

            if latitude is not None:
                obj.latitude = latitude
                obj.longitude = longitude

        super().save_model(request, obj, form, change)

        package = obj.package

        if obj.location:
            package.current_location = obj.location

        if obj.latitude is not None:
            package.latitude = obj.latitude

        if obj.longitude is not None:
            package.longitude = obj.longitude

        package.status = obj.status

        package.save(
            update_fields=[
                "current_location",
                "latitude",
                "longitude",
                "status",
            ]
        )

        if package.notification_user:
            Notification.objects.create(
                user=package.notification_user,
                notification_type="tracking",
                title="Package location updated",
                message=(
                    f"Your package {package.tracking_number} "
                    "is now in "
                    f"{obj.location or 'an updated location'}."
                ),
                link=(
                    "/tracking/?tracking_number="
                    f"{package.tracking_number}"
                ),
            )


# =================================================
# BUSINESS ADMIN
# =================================================

@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "owner",
        "category",
        "city",
        "region",
        "is_hidden",
        "created_at",
    )

    list_filter = (
        "category",
        "region",
        "is_hidden",
        "created_at",
    )

    search_fields = (
        "name",
        "owner__username",
        "city",
        "region",
        "phone",
        "email",
        "moderation_note",
    )

    ordering = ("-created_at",)

    actions = (
        hide_selected_listings,
        restore_selected_listings,
    )


# =================================================
# BUSINESS VIEW ADMIN
# =================================================

@admin.register(BusinessView)
class BusinessViewAdmin(admin.ModelAdmin):
    list_display = (
        "business",
        "viewer",
        "viewed_at",
    )

    list_filter = (
        "viewed_at",
    )

    search_fields = (
        "business__name",
        "viewer__username",
    )

    ordering = ("-viewed_at",)


# =================================================
# CONVERSATION ADMIN
# =================================================

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "business",
        "customer",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "business__name",
        "customer__username",
    )

    ordering = ("-updated_at",)


# =================================================
# MESSAGE ADMIN
# =================================================

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "conversation",
        "sender",
        "text_preview",
        "is_read",
        "created_at",
    )

    list_filter = (
        "is_read",
        "created_at",
    )

    search_fields = (
        "text",
        "sender__username",
        "conversation__business__name",
    )

    ordering = ("-created_at",)

    @admin.display(description="Message")
    def text_preview(self, obj):
        return (obj.text or "")[:50]


# =================================================
# NOTIFICATION ADMIN
# =================================================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "notification_type",
        "title",
        "is_read",
        "created_at",
    )

    list_filter = (
        "notification_type",
        "is_read",
        "created_at",
    )

    search_fields = (
        "user__username",
        "title",
        "message",
    )

    ordering = ("-created_at",)


# =================================================
# ITEM IMAGE INLINE
# =================================================

class ItemImageInline(admin.TabularInline):
    model = ItemImage
    extra = 0
    max_num = 10


# =================================================
# ITEM ADMIN
# =================================================

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "seller",
        "category",
        "price",
        "condition",
        "location",
        "negotiable",
        "status",
        "is_hidden",
        "created_at",
    )

    list_filter = (
        "category",
        "condition",
        "status",
        "negotiable",
        "is_hidden",
        "created_at",
    )

    search_fields = (
        "title",
        "description",
        "location",
        "seller__username",
        "moderation_note",
    )

    ordering = ("-created_at",)

    inlines = [ItemImageInline]

    actions = (
        hide_selected_listings,
        restore_selected_listings,
    )


# =================================================
# FOOD IMAGE INLINE
# =================================================

class FoodImageInline(admin.TabularInline):
    model = FoodImage
    extra = 0
    max_num = 10


# =================================================
# FOOD ADMIN
# =================================================

@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "seller",
        "category",
        "price",
        "quantity",
        "location",
        "status",
        "pickup_available",
        "delivery_available",
        "is_hidden",
        "created_at",
    )

    list_filter = (
        "category",
        "status",
        "pickup_available",
        "delivery_available",
        "is_hidden",
        "created_at",
    )

    search_fields = (
        "title",
        "description",
        "location",
        "seller__username",
        "moderation_note",
    )

    ordering = ("-created_at",)

    inlines = [FoodImageInline]

    actions = (
        hide_selected_listings,
        restore_selected_listings,
    )


# =================================================
# BUSINESS REVIEW ADMIN
# =================================================

@admin.register(BusinessReview)
class BusinessReviewAdmin(admin.ModelAdmin):
    list_display = (
        "business",
        "reviewer",
        "rating",
        "comment_preview",
        "created_at",
    )

    list_filter = (
        "rating",
        "created_at",
    )

    search_fields = (
        "business__name",
        "reviewer__username",
        "comment",
    )

    ordering = ("-created_at",)

    @admin.display(description="Review")
    def comment_preview(self, obj):
        return (obj.comment or "")[:80]


# =================================================
# USER PRESENCE ADMIN
# =================================================

@admin.register(UserPresence)
class UserPresenceAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "is_online",
        "last_seen",
    )

    list_filter = (
        "is_online",
        "last_seen",
    )

    search_fields = (
        "user__username",
        "user__email",
    )

    ordering = ("-last_seen",)

    readonly_fields = (
        "last_seen",
    )


# =================================================
# PAYMENT ADMIN
# =================================================

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "amount",
        "currency",
        "service_reference",
        "payment_method",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "payment_method",
        "currency",
        "created_at",
    )

    search_fields = (
        "user__username",
        "service_reference",
        "transaction_id",
        "provider_reference",
    )

    ordering = ("-created_at",)


# =================================================
# BUSINESSHUB SUBSCRIPTION ADMIN
# =================================================

@admin.register(BusinessHubSubscription)
class BusinessHubSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "plan",
        "is_active",
        "start_date",
        "expiry_date",
        "created_at",
    )

    list_filter = (
        "plan",
        "is_active",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
    )

    ordering = ("-created_at",)


# =================================================
# LISTING PROMOTION ADMIN
# =================================================

@admin.register(ListingPromotion)
class ListingPromotionAdmin(admin.ModelAdmin):
    list_display = (
        "item",
        "user",
        "service_type",
        "is_active",
        "start_date",
        "expiry_date",
        "payment",
        "created_at",
    )

    list_filter = (
        "service_type",
        "is_active",
        "created_at",
    )

    search_fields = (
        "item__title",
        "user__username",
    )

    ordering = ("-created_at",)