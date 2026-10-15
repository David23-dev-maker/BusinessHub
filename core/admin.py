
from django.contrib import admin
from django import forms

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
    Payment,
    BusinessHubSubscription,
    ListingPromotion,
)

from geopy.geocoders import Nominatim


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
            language="en"
        )

        if location_data:

            return (
                float(location_data.latitude),
                float(location_data.longitude)
            )

    except Exception as error:

        print(
            "Geocoding error:",
            error
        )

    return None, None


# =================================================
# PACKAGE ADMIN FORM
# =================================================

class PackageAdminForm(forms.ModelForm):

    tracking_number = forms.CharField(
        required=False,
        help_text="Leave blank to generate automatically."
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

    inlines = [
        TrackingUpdateInline
    ]

    def save_model(
        self,
        request,
        obj,
        form,
        change
    ):

        if not obj.tracking_number:

            import uuid

            obj.tracking_number = (
                "BH-" +
                uuid.uuid4().hex[:8].upper()
            )

        old_status = None

        if change:

            old_package = Package.objects.get(
                pk=obj.pk
            )

            old_status = old_package.status

        if obj.destination:

            (
                destination_latitude,
                destination_longitude
            ) = get_coordinates(
                obj.destination
            )

            if (
                destination_latitude is not None
                and
                destination_longitude is not None
            ):

                obj.destination_latitude = (
                    destination_latitude
                )

                obj.destination_longitude = (
                    destination_longitude
                )

        if obj.current_location:

            (
                current_latitude,
                current_longitude
            ) = get_coordinates(
                obj.current_location
            )

            if (
                current_latitude is not None
                and
                current_longitude is not None
            ):

                obj.latitude = current_latitude
                obj.longitude = current_longitude

        super().save_model(
            request,
            obj,
            form,
            change
        )

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
                )
            )

            if obj.notification_user:

                Notification.objects.create(
                    user=obj.notification_user,
                    notification_type="tracking",
                    title="Package created",
                    message=(
                        f"Your package "
                        f"{obj.tracking_number} "
                        f"has been created and is ready "
                        f"for tracking."
                    ),
                    link=(
                        "/tracking/"
                        f"?tracking_number="
                        f"{obj.tracking_number}"
                    )
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
                    f"Package status changed to "
                    f"{obj.get_status_display()}."
                )
            )

            if obj.notification_user:

                if obj.status == "out_for_delivery":

                    title = "Package out for delivery"

                    message = (
                        f"Your package "
                        f"{obj.tracking_number} "
                        f"is now out for delivery."
                    )

                elif obj.status == "delivered":

                    title = "Package delivered"

                    message = (
                        f"Your package "
                        f"{obj.tracking_number} "
                        f"has been delivered."
                    )

                elif obj.status == "in_transit":

                    title = "Package in transit"

                    message = (
                        f"Your package "
                        f"{obj.tracking_number} "
                        f"is now in transit."
                    )

                elif obj.status == "processing":

                    title = "Package processing"

                    message = (
                        f"Your package "
                        f"{obj.tracking_number} "
                        f"is now being processed."
                    )

                elif obj.status == "received":

                    title = "Package received"

                    message = (
                        f"Your package "
                        f"{obj.tracking_number} "
                        f"has been received."
                    )

                elif obj.status == "cancelled":

                    title = "Package cancelled"

                    message = (
                        f"Package cancelled"

                    )

                else:

                    title = "Package status updated"

                    message = (
                        f"Your package "
                        f"{obj.tracking_number} "
                        f"is now "
                        f"{obj.get_status_display()}."
                    )

                Notification.objects.create(
                    user=obj.notification_user,
                    notification_type="tracking",
                    title=title,
                    message=message,
                    link=(
                        "/tracking/"
                        f"?tracking_number="
                        f"{obj.tracking_number}"
                    )
                )

    def save_formset(
        self,
        request,
        form,
        formset,
        change
    ):

        instances = formset.save(commit=False)

        for obj in instances:

            if obj.location:

                (
                    latitude,
                    longitude
                ) = get_coordinates(
                    obj.location
                )

                if (
                    latitude is not None
                    and
                    longitude is not None
                ):

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
                        f"Your package "
                        f"{package.tracking_number} "
                        f"is now in "
                        f"{obj.location or 'an updated location'}."
                    ),
                    link=(
                        "/tracking/"
                        f"?tracking_number="
                        f"{package.tracking_number}"
                    )
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
    )

    search_fields = (
        "package__tracking_number",
        "location",
        "description",
    )

    ordering = (
        "-created_at",
    )

    def save_model(
        self,
        request,
        obj,
        form,
        change
    ):

        if obj.location:

            (
                latitude,
                longitude
            ) = get_coordinates(
                obj.location
            )

            if (
                latitude is not None
                and
                longitude is not None
            ):

                obj.latitude = latitude
                obj.longitude = longitude

        super().save_model(
            request,
            obj,
            form,
            change
        )

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
                    f"Your package "
                    f"{package.tracking_number} "
                    f"is now in "
                    f"{obj.location or 'an updated location'}."
                ),
                link=(
                    "/tracking/"
                    f"?tracking_number="
                    f"{package.tracking_number}"
                )
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
        "created_at",
    )

    list_filter = (
        "category",
        "region",
    )

    search_fields = (
        "name",
        "owner__username",
        "city",
        "region",
        "phone",
        "email",
    )

    ordering = (
        "-created_at",
    )


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

    ordering = (
        "-updated_at",
    )


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
    )

    search_fields = (
        "text",
        "sender__username",
        "conversation__business__name",
    )

    ordering = (
        "-created_at",
    )

    def text_preview(
        self,
        obj
    ):

        return obj.text[:50]

    text_preview.short_description = "Message"


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
    )

    search_fields = (
        "user__username",
        "title",
        "message",
    )

    ordering = (
        "-created_at",
    )


# =================================================
# ITEM IMAGE INLINE
# =================================================

class ItemImageInline(admin.TabularInline):

    model = ItemImage
    extra = 3
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
        "created_at",
    )

    list_filter = (
        "category",
        "condition",
        "status",
        "negotiable",
    )

    search_fields = (
        "title",
        "description",
        "location",
        "seller__username",
    )

    ordering = (
        "-created_at",
    )

    inlines = [
        ItemImageInline
    ]


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
    )

    search_fields = (
        "user__username",
        "service_reference",
        "transaction_id",
        "provider_reference",
    )

    ordering = (
        "-created_at",
    )


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
    )

    search_fields = (
        "user__username",
    )

    ordering = (
        "-created_at",
    )


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
    )

    search_fields = (
        "item__title",
        "user__username",
    )

    ordering = (
        "-created_at",
    )

admin.site.register(BusinessView)
