from django.contrib import admin
from django import forms
from .models import Business, Package, TrackingUpdate

class PackageAdminForm(forms.ModelForm):

    tracking_number = forms.CharField(
        required=False,
        help_text="Leave blank to generate automatically."
    )

    class Meta:
        model = Package
        fields = "__all__"

@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "city",
        "region",
        "phone",
        "created_at",
    )

    list_filter = (
        "category",
        "region",
        "city",
    )

    search_fields = (
        "name",
        "city",
        "region",
        "phone",
        "email",
    )


class TrackingUpdateInline(admin.TabularInline):
    model = TrackingUpdate
    extra = 1
    ordering = ("-created_at",)


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
        TrackingUpdateInline,
    ]

    def save_model(self, request, obj, form, change):

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

       super().save_model(
        request,
        obj,
        form,
        change
    )

       if old_status != obj.status:

        TrackingUpdate.objects.create(
            package=obj,
            status=obj.status,
            location=obj.current_location or "Location updating...",
            latitude=obj.latitude,
            longitude=obj.longitude,
            description=f"Package status changed to {obj.get_status_display()}."
        )
@admin.register(TrackingUpdate)
class TrackingUpdateAdmin(admin.ModelAdmin):

    list_display = (
        "package",
        "status",
        "location",
        "created_at",
    )

    list_filter = (
        "status",
        "location",
    )

    search_fields = (
        "package__tracking_number",
        "location",
        "description",
    )
