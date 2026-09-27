from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Business , Package , TrackingUpdate
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from geopy.geocoders import Nominatim

@login_required
def list_business(request):
    if request.method == "POST":
        Business.objects.create(
            owner=request.user,
            name=request.POST.get("name"),
            category=request.POST.get("category"),
            phone=request.POST.get("phone"),
            email=request.POST.get("email"),
            description=request.POST.get("description"),
            city=request.POST.get("city"),
            region=request.POST.get("region"),
            opening_time=request.POST.get("opening_time") or None,
            closing_time=request.POST.get("closing_time") or None,
            logo=request.FILES.get("logo"),
        )

        return redirect("business_success")

    businesses = Business.objects.all().order_by("-created_at")

    return render(
        request,
        "core/list-business.html",
        {"businesses": businesses}
    )


def business_success(request):
    return render(request, "business-success.html")


def business_list(request):
    query = request.GET.get("q", "").strip()

    businesses = Business.objects.all().order_by("-created_at")

    if query:
        businesses = businesses.filter(
            name__icontains=query
        ) | businesses.filter(
            category__icontains=query
        ) | businesses.filter(
            city__icontains=query
        ) | businesses.filter(
            region__icontains=query
        )

    return render(
        request,
        "core/businesses.html",
        {
            "businesses": businesses,
            "query": query,
        }
    )

    return render(
        request,
        "core/businesses.html",
        {"businesses": businesses}
    )



@login_required
def owner_dashboard(request):
    businesses = Business.objects.filter(
        owner=request.user
    ).order_by("-created_at")

    return render(
        request,
        "core/owner-dashboard.html",
        {"businesses": businesses}
    )


@login_required
def view_business(request, business_id):
    business = get_object_or_404(
        Business,
        id=business_id,
        owner=request.user
    )

    return render(
        request,
        "core/view-business.html",
        {"business": business}
    )

@login_required
def edit_business(request, business_id):
    business = get_object_or_404(
        Business,
        id=business_id,
        owner=request.user
    )

    if request.method == "POST":
        business.name = request.POST.get("name")
        business.category = request.POST.get("category")
        business.description = request.POST.get("description")
        business.city = request.POST.get("city")
        business.region = request.POST.get("region")
        business.phone = request.POST.get("phone")
        business.save()

        return redirect("owner_dashboard")

    return render(
        request,
        "core/edit-business.html",
        {"business": business}
    )

@login_required
def delete_business(request, business_id):
    business = get_object_or_404(
        Business,
        id=business_id,
        owner=request.user
    )

    if request.method == "POST":
        business.delete()
        return redirect("owner_dashboard")

    return render(
        request,
        "core/delete-business.html",
        {"business": business}
    )

def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect("owner_dashboard")

        return render(request, "core/login.html", {
            "error": "Invalid username or password."
        })

    return render(request, "core/login.html")
def home(request):
    return render(request, "core/index.html")
def categories(request):
    return render(request, "core/categories.html")
def tracking(request):
    tracking_number = request.GET.get("tracking_number", "").strip()

    package = None

    if tracking_number:
        package = Package.objects.filter(
            tracking_number=tracking_number
        ).first()

    return render(
        request,
        "core/tracking.html",
        {
            "tracking_number": tracking_number,
            "package": package,
        }
    )
def package_location_api(request, tracking_number):

    package = get_object_or_404(
        Package,
        tracking_number=tracking_number
    )

    return JsonResponse({
        "latitude": package.latitude,
        "longitude": package.longitude,
        "status": package.status,
        "current_location": package.current_location,
    })
def save_package_location_api(request, tracking_number):

    if request.method != "POST":
        return JsonResponse({
            "error": "POST request required"
        }, status=405)

    package = get_object_or_404(
        Package,
        tracking_number=tracking_number
    )

    latitude = request.POST.get("latitude")
    longitude = request.POST.get("longitude")

    if not latitude or not longitude:
        return JsonResponse({
            "error": "Latitude and longitude are required"
        }, status=400)

    latitude = float(latitude)
    longitude = float(longitude)

    # Check the latest tracking update
    latest_update = package.updates.first()

    # Don't create a duplicate entry
    if latest_update:

        if (
            latest_update.latitude == latitude
            and
            latest_update.longitude == longitude
        ):
            return JsonResponse({
                "saved": False,
                "message": "Location has not changed"
            })

    # Find the city/location from the coordinates
    location_name = "Location updating..."

    try:

        geolocator = Nominatim(
            user_agent="businesshub_tracking"
        )

        location_data = geolocator.reverse(
            (latitude, longitude),
            exactly_one=True,
            language="en"
        )

        if location_data:

            address = location_data.raw.get(
                "address",
                {}
            )

            location_name = (
                address.get("city")
                or address.get("town")
                or address.get("municipality")
                or address.get("village")
                or address.get("county")
                or "Location updating..."
            )

    except Exception as error:

        print(
            "Reverse geocoding error:",
            error
        )


    # Update the package's current location
    package.current_location = location_name
    package.latitude = latitude
    package.longitude = longitude
    package.save(
        update_fields=[
            "current_location",
            "latitude",
            "longitude"
        ]
    )


    # Create tracking history
    TrackingUpdate.objects.create(

        package=package,

        status=package.status,

        location=location_name,

        latitude=latitude,

        longitude=longitude,

        description=
            "Package location updated automatically."

    )


    return JsonResponse({

        "saved": True,

        "location": location_name,

        "message":
            "Location saved to tracking history"

    })
