from django.http import FileResponse, Http404
from django.utils.http import content_disposition_header
from django.utils.text import get_valid_filename
from decimal import Decimal, InvalidOperation
from datetime import timedelta
import uuid

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse

from .models import (
    Business,
    BusinessView,
    BusinessReview,
    Package,
    TrackingUpdate,
    Message,
    Conversation,
    UserPresence,
    Notification,
    Item,
    ItemImage,
    Food,
    FoodImage,
    Payment,
    BusinessHubSubscription,
    ListingPromotion,
)

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
from django.contrib import messages
from geopy.geocoders import Nominatim
from django.db.models import Q, Avg
from django.db.models import Q, Avg, Count
from django.db import transaction
# =====================================================
# NOTIFICATION HELPERS
# =====================================================

def create_message_notification(
    conversation,
    sender,
    message_text
):

    recipient = None

    # Marketplace item conversation
    if conversation.item:

        if sender.id == conversation.customer_id:
            recipient = conversation.seller

        elif conversation.seller_id == sender.id:
            recipient = conversation.customer

    # Food marketplace conversation
    elif conversation.food:

        if sender.id == conversation.customer_id:
            recipient = conversation.seller

        elif conversation.seller_id == sender.id:
            recipient = conversation.customer

    # Business conversation
    elif conversation.business:

        if sender.id == conversation.customer_id:
            recipient = conversation.business.owner

        elif conversation.business.owner_id == sender.id:
            recipient = conversation.customer

    if not recipient:
        return

    # Don't notify someone about their own message
    if recipient.id == sender.id:
        return

    Notification.objects.create(
        user=recipient,
        notification_type="message",
        title="New message",
        message=(
            f"{sender.username} sent you a new message."
        ),
        link=reverse(
            "conversation_detail",
            args=[conversation.id]
        )
    )


def create_tracking_notification(
    package,
    title,
    message
):

    if not package.notification_user:
        return

    Notification.objects.create(
        user=package.notification_user,
        notification_type="tracking",
        title=title,
        message=message,
        link=(
            reverse("tracking")
            + "?tracking_number="
            + package.tracking_number
        )
    )


# =====================================================
# NOTIFICATIONS
# =====================================================

@login_required
def notifications(request):

    user_notifications = Notification.objects.filter(
        user=request.user
    ).order_by(
        "-created_at"
    )

    return render(
        request,
        "core/notifications.html",
        {
            "notifications": user_notifications,
        }
    )


@login_required
def notification_detail(
    request,
    notification_id
):

    notification = get_object_or_404(
        Notification,
        id=notification_id,
        user=request.user
    )

    if not notification.is_read:

        notification.is_read = True

        notification.save(
            update_fields=["is_read"]
        )

    if notification.link:

        return redirect(
            notification.link
        )

    return redirect(
        "notifications"
    )


@login_required
def mark_all_notifications_read(request):

    if request.method != "POST":

        return redirect(
            "notifications"
        )

    Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(
        is_read=True
    )

    return redirect(
        "notifications"
    )
@login_required
def unread_notifications_count(request):

    count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    return JsonResponse({
        "count": count
    })

@login_required
def latest_unread_notification(request):

    notification = (
        Notification.objects
        .filter(
            user=request.user,
            is_read=False
        )
        .order_by(
            "-created_at",
            "-id"
        )
        .first()
    )

    if not notification:
        return JsonResponse({
            "notification": None
        })

    return JsonResponse({
        "notification": {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "link": notification.link,
            "created_at": notification.created_at.isoformat(),
        }
    })


# =====================================================
# BUSINESS
# =====================================================


@login_required
def list_business(request):
    # ============================================================
    # BUSINESSHUB FREE-LAUNCH PLAN
    # Unlimited business listings during the free-launch period
    # ============================================================

    business_limit = "Unlimited"
    plan_name = "BusinessHub Free Launch"

    # ============================================================
    # HANDLE BUSINESS CREATION
    # ============================================================

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        category = request.POST.get("category", "").strip()
        phone = request.POST.get("phone", "").strip()
        email = request.POST.get("email", "").strip()
        description = request.POST.get("description", "").strip()
        city = request.POST.get("city", "").strip()
        region = request.POST.get("region", "").strip()

        opening_time = request.POST.get("opening_time") or None
        closing_time = request.POST.get("closing_time") or None
        logo = request.FILES.get("logo")

        Business.objects.create(
            owner=request.user,
            name=name,
            category=category,
            phone=phone,
            email=email,
            description=description,
            city=city,
            region=region,
            opening_time=opening_time,
            closing_time=closing_time,
            logo=logo,
        )

        messages.success(
            request,
            "Your business has been created successfully."
        )

        return redirect("business_success")

    # ============================================================
    # DISPLAY BUSINESSES
    # ============================================================

    businesses = Business.objects.all().order_by("-created_at")

    return render(
        request,
        "core/list-business.html",
        {
            "businesses": businesses,
            "business_limit": business_limit,
            "plan_name": plan_name,
            "categories": Business.CATEGORY_CHOICES,
        }
    )
def business_success(request):

    return render(
        request,
        "business-success.html"
    )


def business_list(request):
    from datetime import date

    query = request.GET.get("q", "").strip()
    selected_category = request.GET.get("category", "").strip()

    # ============================================================
    # CHECK FREE-LAUNCH PERIOD
    # ============================================================

    today = timezone.localdate()

    free_launch = (
        date(2026, 10, 12)
        <= today
        < date(2027, 10, 12)
    )

    # ============================================================
    # GET BUSINESSES
    # ============================================================

    businesses = (
        Business.objects
        .select_related("owner")
        .annotate(
            average_rating=Avg("reviews__rating"),
            review_count=Count(
                "reviews",
                distinct=True,
            ),
        )
        .all()
    )

    # ============================================================
    # SEARCH
    # ============================================================

    if query:
        businesses = businesses.filter(
            Q(name__icontains=query)
            | Q(category__icontains=query)
            | Q(city__icontains=query)
            | Q(region__icontains=query)
        )

    # ============================================================
    # CATEGORY FILTER
    # ============================================================

    category_mapping = {
        "Restaurants & Food": ["food"],
        "Shopping & Retail": ["shopping"],
        "Electronics & Computers": ["electronics"],
        "Home & Living": ["home"],
        "Health & Beauty": ["beauty"],
        "Transport & Logistics": ["transport"],
        "Education & Training": ["education"],
        "Business Services": ["services"],
        "Sports & Recreation": ["sports"],
        "Pets & Animals": ["pets"],
        "Other Services": ["other"],
        "Travel & Tourism": ["travel"],
    }

    if selected_category:
        matching_categories = category_mapping.get(
            selected_category,
            [],
        )

        if matching_categories:
            businesses = businesses.filter(
                category__in=matching_categories
            )
        else:
            businesses = businesses.none()

    # ============================================================
    # GET ACTIVE SUBSCRIPTIONS
    # ============================================================

    now = timezone.now()

    active_subscriptions = (
        BusinessHubSubscription.objects
        .filter(
            is_active=True,
            expiry_date__gt=now,
        )
        .select_related("user")
    )

    subscription_map = {
        subscription.user_id: subscription
        for subscription in active_subscriptions
    }

    business_list_data = []

    # ============================================================
    # ASSIGN BUSINESS RANKINGS
    # ============================================================

    for business in businesses:
        subscription = subscription_map.get(
            business.owner_id
        )

        if free_launch:
            plan_name = "BusinessHub Free Launch"
            plan_rank = 1
            plan_badge = ""

        elif subscription:
            if subscription.plan == "pro":
                plan_name = "BusinessHub Pro"
                plan_rank = 3
                plan_badge = "PRO"

            elif subscription.plan == "plus":
                plan_name = "BusinessHub Plus"
                plan_rank = 2
                plan_badge = "PLUS"

            else:
                plan_name = "Free"
                plan_rank = 1
                plan_badge = ""

        else:
            plan_name = "Free"
            plan_rank = 1
            plan_badge = ""

        business.plan_name = plan_name
        business.plan_rank = plan_rank
        business.plan_badge = plan_badge

        business_list_data.append(business)

    # ============================================================
    # SORT BUSINESSES
    # ============================================================

    business_list_data.sort(
        key=lambda business: (
            business.plan_rank,
            business.created_at,
        ),
        reverse=True,
    )

    # ============================================================
    # DISPLAY
    # ============================================================

    return render(
        request,
        "core/businesses.html",
        {
            "businesses": business_list_data,
            "query": query,
            "selected_category": selected_category,
        },
    )

@login_required
def owner_dashboard(request):

    businesses = Business.objects.filter(
        owner=request.user
    ).order_by(
        "-created_at"
    )

    return render(
        request,
        "core/owner-dashboard.html",
        {
            "businesses": businesses
        }
    )


def view_business(
    request,
    business_id
):

    business = get_object_or_404(
        Business,
        id=business_id
    )

    # Record business view
    BusinessView.objects.create(
        business=business,
        viewer=request.user if request.user.is_authenticated else None
    )

    # Get all reviews
    reviews = (
        BusinessReview.objects
        .filter(business=business)
        .select_related("reviewer")
        .order_by("-created_at")
    )

    # Calculate rating statistics
    review_stats = reviews.aggregate(
        average_rating=Avg("rating")
    )

    average_rating = review_stats["average_rating"] or 0
    review_count = reviews.count()

    # Prepare star display for each review
    for review in reviews:

        review.star_range = range(1, 6)

    # Current user's review
    user_review = None

    if request.user.is_authenticated:

        user_review = BusinessReview.objects.filter(
            business=business,
            reviewer=request.user
        ).first()

    return render(
        request,
        "core/view-business.html",
        {
            "business": business,
            "reviews": reviews,
            "average_rating": average_rating,
            "review_count": review_count,
            "user_review": user_review,
        }
    )
@login_required
def edit_business_review(request, business_id):

    if request.method != "POST":
        return redirect(
            "view_business",
            business_id=business_id
        )

    business = get_object_or_404(
        Business,
        id=business_id
    )

    review = get_object_or_404(
        BusinessReview,
        business=business,
        reviewer=request.user
    )

    try:
        rating = int(
            request.POST.get(
                "rating",
                0
            )
        )
    except (TypeError, ValueError):
        rating = 0

    comment = request.POST.get(
        "comment",
        ""
    ).strip()

    if rating < 1 or rating > 5:

        messages.error(
            request,
            "Please select a rating from 1 to 5 stars."
        )

        return redirect(
            "view_business",
            business_id=business_id
        )

    if not comment:

        messages.error(
            request,
            "Please write a review comment."
        )

        return redirect(
            "view_business",
            business_id=business_id
        )

    review.rating = rating
    review.comment = comment

    review.save(
        update_fields=[
            "rating",
            "comment",
            "updated_at"
        ]
    )

    messages.success(
        request,
        "Your review has been updated successfully."
    )

    return redirect(
        "view_business",
        business_id=business_id
    )


@login_required
def delete_business_review(request, business_id):

    if request.method != "POST":
        return redirect(
            "view_business",
            business_id=business_id
        )

    business = get_object_or_404(
        Business,
        id=business_id
    )

    review = get_object_or_404(
        BusinessReview,
        business=business,
        reviewer=request.user
    )

    review.delete()

    messages.success(
        request,
        "Your review has been deleted."
    )

    return redirect(
        "view_business",
        business_id=business_id
    )
@login_required
def submit_business_review(
    request,
    business_id
):

    business = get_object_or_404(
        Business,
        id=business_id
    )

    # Business owners cannot review their own business
    if business.owner == request.user:

        messages.error(
            request,
            "You cannot review your own business."
        )

        return redirect(
            "view_business",
            business_id=business.id
        )

    # Only accept POST submissions
    if request.method != "POST":

        return redirect(
            "view_business",
            business_id=business.id
        )

    # Prevent duplicate reviews
    existing_review = BusinessReview.objects.filter(
        business=business,
        reviewer=request.user
    ).first()

    if existing_review:

        messages.warning(
            request,
            "You have already reviewed this business."
        )

        return redirect(
            "view_business",
            business_id=business.id
        )

    rating = request.POST.get("rating")
    comment = request.POST.get("comment", "").strip()

    # Validate rating
    try:

        rating = int(rating)

    except (TypeError, ValueError):

        messages.error(
            request,
            "Please select a valid rating."
        )

        return redirect(
            "view_business",
            business_id=business.id
        )

    if rating < 1 or rating > 5:

        messages.error(
            request,
            "Rating must be between 1 and 5 stars."
        )

        return redirect(
            "view_business",
            business_id=business.id
        )

    # Require a comment
    if not comment:

        messages.error(
            request,
            "Please write a review before submitting."
        )

        return redirect(
            "view_business",
            business_id=business.id
        )

    BusinessReview.objects.create(
        business=business,
        reviewer=request.user,
        rating=rating,
        comment=comment
    )

    messages.success(
        request,
        "Your review has been submitted successfully."
    )

    return redirect(
        "view_business",
        business_id=business.id
    )
@login_required
def edit_business_review(
    request,
    business_id
):

    business = get_object_or_404(
        Business,
        id=business_id
    )

    review = get_object_or_404(
        BusinessReview,
        business=business,
        reviewer=request.user
    )

    if request.method == "POST":

        rating = request.POST.get("rating")
        comment = request.POST.get("comment", "").strip()

        try:

            rating = int(rating)

        except (TypeError, ValueError):

            messages.error(
                request,
                "Please select a valid rating."
            )

            return redirect(
                "view_business",
                business_id=business.id
            )

        if rating < 1 or rating > 5:

            messages.error(
                request,
                "Rating must be between 1 and 5 stars."
            )

            return redirect(
                "view_business",
                business_id=business.id
            )

        if not comment:

            messages.error(
                request,
                "Please write a review before saving."
            )

            return redirect(
                "view_business",
                business_id=business.id
            )

        review.rating = rating
        review.comment = comment
        review.save()

        messages.success(
            request,
            "Your review has been updated."
        )

    return redirect(
        "view_business",
        business_id=business.id
    )
@login_required
def delete_business_review(
    request,
    business_id
):

    business = get_object_or_404(
        Business,
        id=business_id
    )

    review = get_object_or_404(
        BusinessReview,
        business=business,
        reviewer=request.user
    )

    if request.method == "POST":

        review.delete()

        messages.success(
            request,
            "Your review has been deleted."
        )

    return redirect(
        "view_business",
        business_id=business.id
    )

@login_required
def business_analytics(request):

    businesses = (
        Business.objects
        .filter(
            owner=request.user
        )
        .order_by(
            "-created_at"
        )
    )

    today = timezone.now().date()

    # =====================================================
    # TOTAL VIEWS
    # =====================================================

    total_views = BusinessView.objects.filter(
        business__owner=request.user
    ).count()

    views_today = BusinessView.objects.filter(
        business__owner=request.user,
        viewed_at__date=today
    ).count()

    views_this_week = BusinessView.objects.filter(
        business__owner=request.user,
        viewed_at__date__gte=today - timedelta(days=6)
    ).count()

    # =====================================================
    # YESTERDAY'S VIEWS
    # =====================================================

    yesterday = today - timedelta(days=1)

    views_yesterday = BusinessView.objects.filter(
        business__owner=request.user,
        viewed_at__date=yesterday
    ).count()

    # =====================================================
    # TODAY VS YESTERDAY
    # =====================================================

    if views_yesterday > 0:

        today_vs_yesterday_percentage = round(
            (
                (views_today - views_yesterday)
                / views_yesterday
            ) * 100
        )

    elif views_today > 0:

        today_vs_yesterday_percentage = 100

    else:

        today_vs_yesterday_percentage = 0

    # =====================================================
    # PREVIOUS 7 DAYS
    # =====================================================

    previous_week_start = today - timedelta(days=13)
    previous_week_end = today - timedelta(days=7)

    views_previous_week = BusinessView.objects.filter(
        business__owner=request.user,
        viewed_at__date__gte=previous_week_start,
        viewed_at__date__lte=previous_week_end
    ).count()

    # =====================================================
    # CURRENT 7 DAYS VS PREVIOUS 7 DAYS
    # =====================================================

    if views_previous_week > 0:

        weekly_growth_percentage = round(
            (
                (views_this_week - views_previous_week)
                / views_previous_week
            ) * 100
        )

    elif views_this_week > 0:

        weekly_growth_percentage = 100

    else:

        weekly_growth_percentage = 0

    # =====================================================
    # 7-DAY VIEWS
    # =====================================================

    weekly_views = []

    for days_ago in range(6, -1, -1):

        view_date = today - timedelta(
            days=days_ago
        )

        count = BusinessView.objects.filter(
            business__owner=request.user,
            viewed_at__date=view_date
        ).count()

        weekly_views.append({
            "date": view_date,
            "label": view_date.strftime("%a"),
            "count": count,
        })

    # =====================================================
    # BUSINESS ANALYTICS
    # =====================================================

    business_analytics = []

    for business in businesses:

        business_total_views = BusinessView.objects.filter(
            business=business
        ).count()

        business_today_views = BusinessView.objects.filter(
            business=business,
            viewed_at__date=today
        ).count()

        # =================================================
        # VIEW SHARE
        # =================================================

        if total_views > 0:

            view_share_percentage = round(
                (
                    business_total_views
                    / total_views
                ) * 100
            )

        else:

            view_share_percentage = 0

        business_analytics.append({
            "business": business,
            "total_views": business_total_views,
            "today_views": business_today_views,
            "view_share_percentage":
                view_share_percentage,
        })

    # =====================================================
    # BUSINESS PERFORMANCE RANKING
    # =====================================================

    business_analytics.sort(
        key=lambda item: item["total_views"],
        reverse=True
    )

    # =====================================================
    # MOST VIEWED BUSINESS
    # =====================================================

    most_viewed_business = None

    if business_analytics:

        top_business = business_analytics[0]

        if top_business["total_views"] > 0:

            most_viewed_business = top_business

    # =====================================================
    # VIEWER TYPES
    # =====================================================

    logged_in_views = BusinessView.objects.filter(
        business__owner=request.user,
        viewer__isnull=False
    ).count()

    guest_views = BusinessView.objects.filter(
        business__owner=request.user,
        viewer__isnull=True
    ).count()

    if total_views > 0:

        logged_in_percentage = round(
            (logged_in_views / total_views) * 100
        )

        guest_percentage = round(
            (guest_views / total_views) * 100
        )

    else:

        logged_in_percentage = 0
        guest_percentage = 0

    # =====================================================
    # RENDER
    # =====================================================

    return render(
        request,
        "core/business-analytics.html",
        {
            "business_analytics":
                business_analytics,

            "total_views":
                total_views,

            "views_today":
                views_today,

            "views_yesterday":
                views_yesterday,

            "views_this_week":
                views_this_week,

            "today_vs_yesterday_percentage":
                today_vs_yesterday_percentage,

            "views_previous_week":
                views_previous_week,

            "weekly_growth_percentage":
                weekly_growth_percentage,

            "weekly_views":
                weekly_views,

            "most_viewed_business":
                most_viewed_business,

            "logged_in_views":
                logged_in_views,

            "guest_views":
                guest_views,

            "logged_in_percentage":
                logged_in_percentage,

            "guest_percentage":
                guest_percentage,
        }
    )

@login_required
def edit_business(
    request,
    business_id
):

    business = get_object_or_404(
        Business,
        id=business_id,
        owner=request.user
    )

    if request.method == "POST":

        business.name = request.POST.get(
            "name",
            ""
        ).strip()

        business.category = request.POST.get(
            "category",
            ""
        ).strip()

        business.description = request.POST.get(
            "description",
            ""
        ).strip()

        business.city = request.POST.get(
            "city",
            ""
        ).strip()

        business.region = request.POST.get(
            "region",
            ""
        ).strip()

        business.phone = request.POST.get(
            "phone",
            ""
        ).strip()

        business.email = request.POST.get(
            "email",
            ""
        ).strip()

        business.opening_time = (
            request.POST.get(
                "opening_time"
            )
            or None
        )

        business.closing_time = (
            request.POST.get(
                "closing_time"
            )
            or None
        )

        # ========================================================
        # REMOVE EXISTING LOGO
        # ========================================================

        remove_logo = (
            request.POST.get(
                "remove_logo"
            )
            == "on"
        )

        if remove_logo:

            if business.logo:

                old_logo = business.logo

                business.logo = None

                old_logo.delete(
                    save=False
                )

        # ========================================================
        # REPLACE LOGO
        # ========================================================

        new_logo = request.FILES.get(
            "logo"
        )

        if new_logo:

            if business.logo:

                old_logo = business.logo

                business.logo = new_logo

                old_logo.delete(
                    save=False
                )

            else:

                business.logo = new_logo

        business.save()

        messages.success(
            request,
            "Your business has been updated successfully."
        )

        return redirect(
            "owner_dashboard"
        )

    return render(
        request,
        "core/edit-business.html",
        {
            "business": business,
            "categories": Business.CATEGORY_CHOICES,
        }
    )

@login_required
def delete_business(
    request,
    business_id
):

    business = get_object_or_404(
        Business,
        id=business_id,
        owner=request.user
    )

    if request.method == "POST":

        business.delete()

        return redirect(
            "owner_dashboard"
        )

    return render(
        request,
        "core/delete-business.html",
        {
            "business": business
        }
    )


# =====================================================
# ACCOUNT
# =====================================================


@login_required
def account(request):

    businesses = Business.objects.filter(
        owner=request.user
    ).order_by(
        "-created_at"
    )

    business_count = businesses.count()

    message_count = Message.objects.filter(
        sender=request.user
    ).count()

    received_message_count = Message.objects.filter(
        conversation__business__owner=request.user
    ).exclude(
        sender=request.user
    ).count()

    received_item_message_count = Message.objects.filter(
        conversation__seller=request.user
    ).exclude(
        sender=request.user
    ).count()

    received_message_count += received_item_message_count

    conversation_count = Conversation.objects.filter(
        Q(customer=request.user)
        |
        Q(business__owner=request.user)
        |
        Q(seller=request.user)
    ).distinct().count()

    # Get the user's current active BusinessHub subscription.
    active_subscription = (
        BusinessHubSubscription.objects.filter(
            user=request.user,
            is_active=True,
            expiry_date__gt=timezone.now(),
        )
        .order_by("-expiry_date")
        .first()
    )

    return render(
        request,
        "core/account.html",
        {
            "businesses": businesses,
            "business_count": business_count,
            "message_count": message_count,
            "received_message_count": received_message_count,
            "conversation_count": conversation_count,
            "active_subscription": active_subscription,
        }
    )



@login_required
def edit_account(request):

    if request.method == "POST":

        first_name = request.POST.get(
            "first_name",
            ""
        ).strip()

        last_name = request.POST.get(
            "last_name",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        username = request.POST.get(
            "username",
            ""
        ).strip()

        if not username:

            return render(
                request,
                "core/edit-account.html",
                {
                    "error": "Username cannot be empty.",
                    "form_username": username,
                    "form_email": email,
                    "form_first_name": first_name,
                    "form_last_name": last_name,
                }
            )

        if User.objects.filter(
            username__iexact=username
        ).exclude(
            pk=request.user.pk
        ).exists():

            return render(
                request,
                "core/edit-account.html",
                {
                    "error": "That username is already taken.",
                    "form_username": username,
                    "form_email": email,
                    "form_first_name": first_name,
                    "form_last_name": last_name,
                }
            )

        if email:

            if User.objects.filter(
                email__iexact=email
            ).exclude(
                pk=request.user.pk
            ).exists():

                return render(
                    request,
                    "core/edit-account.html",
                    {
                        "error": "That email is already in use.",
                        "form_username": username,
                        "form_email": email,
                        "form_first_name": first_name,
                        "form_last_name": last_name,
                    }
                )

        request.user.username = username
        request.user.email = email
        request.user.first_name = first_name
        request.user.last_name = last_name

        request.user.save()

        messages.success(
            request,
            "Your account information has been updated."
        )

        return redirect(
            "account"
        )

    return render(
        request,
        "core/edit-account.html"
    )


@login_required
def change_password(request):

    if request.method == "POST":

        current_password = request.POST.get(
            "current_password",
            ""
        )

        new_password = request.POST.get(
            "new_password",
            ""
        )

        confirm_password = request.POST.get(
            "confirm_password",
            ""
        )

        if not request.user.check_password(
            current_password
        ):

            return render(
                request,
                "core/change-password.html",
                {
                    "error": (
                        "Your current password is incorrect."
                    )
                }
            )

        if len(new_password) < 8:

            return render(
                request,
                "core/change-password.html",
                {
                    "error": (
                        "Your new password must be at least "
                        "8 characters long."
                    )
                }
            )

        if new_password != confirm_password:

            return render(
                request,
                "core/change-password.html",
                {
                    "error": (
                        "The new passwords do not match."
                    )
                }
            )

        if current_password == new_password:

            return render(
                request,
                "core/change-password.html",
                {
                    "error": (
                        "Your new password must be different "
                        "from your current password."
                    )
                }
            )

        request.user.set_password(
            new_password
        )

        request.user.save()

        update_session_auth_hash(
            request,
            request.user
        )

        messages.success(
            request,
            "Your password has been changed successfully."
        )

        return redirect(
            "account"
        )

    return render(
        request,
        "core/change-password.html"
    )


# =====================================================
# AUTHENTICATION
# =====================================================

def user_login(request):

    if request.method == "POST":

        username = request.POST.get(
            "username"
        )

        password = request.POST.get(
            "password"
        )

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(
                request,
                user
            )

            UserPresence.objects.update_or_create(
                user=user,
                defaults={
                    "is_online": True,
                    "last_seen": timezone.now(),
                }
            )

            return redirect(
                "owner_dashboard"
            )

        return render(
            request,
            "core/login.html",
            {
                "error": (
                    "Invalid username or password."
                )
            }
        )

    return render(
        request,
        "core/login.html"
    )


def register(request):

    if request.user.is_authenticated:

        return redirect(
            "owner_dashboard"
        )

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        password_confirm = request.POST.get(
            "password_confirm",
            ""
        )

        if not username or not email or not password:

            return render(
                request,
                "core/register.html",
                {
                    "error": (
                        "Please fill in all required fields."
                    ),
                    "username": username,
                    "email": email,
                }
            )

        if User.objects.filter(
            username__iexact=username
        ).exists():

            return render(
                request,
                "core/register.html",
                {
                    "error": (
                        "That username is already taken."
                    ),
                    "username": username,
                    "email": email,
                }
            )

        if User.objects.filter(
            email__iexact=email
        ).exists():

            return render(
                request,
                "core/register.html",
                {
                    "error": (
                        "An account with that email "
                        "already exists."
                    ),
                    "username": username,
                    "email": email,
                }
            )

        if password != password_confirm:

            return render(
                request,
                "core/register.html",
                {
                    "error": (
                        "The passwords do not match."
                    ),
                    "username": username,
                    "email": email,
                }
            )

        if len(password) < 8:

            return render(
                request,
                "core/register.html",
                {
                    "error": (
                        "Your password must be at least "
                        "8 characters."
                    ),
                    "username": username,
                    "email": email,
                }
            )

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        login(
            request,
            user
        )

        UserPresence.objects.update_or_create(
            user=user,
            defaults={
                "is_online": True,
                "last_seen": timezone.now(),
            }
        )

        return redirect(
            "owner_dashboard"
        )

    return render(
        request,
        "core/register.html"
    )


def user_logout(request):

    if request.user.is_authenticated:

        UserPresence.objects.update_or_create(
            user=request.user,
            defaults={
                "is_online": False,
                "last_seen": timezone.now(),
            }
        )

    logout(request)

    return redirect(
        "home"
    )


# =====================================================
# MAIN PAGES
# =====================================================

def home(request):

    from datetime import date

    # ============================================================
    # BUSINESSHUB FREE-LAUNCH PERIOD
    #
    # Start: 12 October 2026
    # End:   12 October 2027 (exclusive)
    #
    # During this period, all businesses have equal priority.
    # After this period:
    # Pro > Plus > Free
    # ============================================================

    today = timezone.localdate()

    free_launch = (
        date(2026, 10, 12)
        <= today
        < date(2027, 10, 12)
    )

    now = timezone.now()

    home_businesses_queryset = (
        Business.objects
        .select_related("owner")
        .all()
    )

    active_subscriptions = (
        BusinessHubSubscription.objects
        .filter(
            is_active=True,
            expiry_date__gt=now,
        )
        .select_related("user")
    )

    subscription_map = {
        subscription.user_id: subscription
        for subscription in active_subscriptions
    }

    business_list_data = []

    for business in home_businesses_queryset:

        subscription = subscription_map.get(
            business.owner_id
        )

        # --------------------------------------------------------
        # FREE-LAUNCH RANKING
        # --------------------------------------------------------

        if free_launch:

            business.plan_name = "BusinessHub Free Launch"
            business.plan_rank = 1
            business.plan_badge = ""

        # --------------------------------------------------------
        # NORMAL SUBSCRIPTION RANKING AFTER FREE LAUNCH
        # --------------------------------------------------------

        elif subscription:

            if subscription.plan == "pro":

                business.plan_name = "BusinessHub Pro"
                business.plan_rank = 3
                business.plan_badge = "PRO"

            elif subscription.plan == "plus":

                business.plan_name = "BusinessHub Plus"
                business.plan_rank = 2
                business.plan_badge = "PLUS"

            else:

                business.plan_name = "Free"
                business.plan_rank = 1
                business.plan_badge = ""

        else:

            business.plan_name = "Free"
            business.plan_rank = 1
            business.plan_badge = ""

        business_list_data.append(
            business
        )

    # ============================================================
    # SORT BUSINESSES
    #
    # During free launch:
    # All businesses have equal priority.
    #
    # After free launch:
    # Pro > Plus > Free.
    #
    # Newer businesses appear first within equal priority.
    # ============================================================

    business_list_data.sort(
        key=lambda business: (
            business.plan_rank,
            business.created_at,
        ),
        reverse=True,
    )

    # Show only the top 3 businesses on the homepage.

    home_businesses = business_list_data[:3]

    # ============================================================
    # ITEMS
    # ============================================================

    home_items = (
        Item.objects
        .filter(status="available")
        .prefetch_related("images")
        .order_by("-created_at")[:3]
    )

    # ============================================================
    # FOOD
    # ============================================================

    home_foods = (
        Food.objects
        .filter(status="available")
        .prefetch_related("images")
        .order_by("-created_at")[:3]
    )

    # ============================================================
    # HOMEPAGE
    # ============================================================

    return render(
        request,
        "core/index.html",
        {
            "home_businesses": home_businesses,
            "home_items": home_items,
            "home_foods": home_foods,
        }
    )

def categories(request):

    return render(
        request,
        "core/categories.html"
    )


def tracking(request):

    tracking_number = request.GET.get(
        "tracking_number",
        ""
    ).strip()

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


# =====================================================
# BUSINESSHUB SERVICES / PAYMENTS
# =====================================================

BUSINESSHUB_SERVICES = {
    "plus": {
        "name": "BusinessHub Plus",
        "price": Decimal("3000.00"),
        "service_type": "subscription",
        "description": (
            "Extra visibility and premium BusinessHub features."
        ),
        "duration": "Monthly",
    },
    "pro": {
        "name": "BusinessHub Pro",
        "price": Decimal("5000.00"),
        "service_type": "subscription",
        "description": (
            "More premium features, visibility and promotional tools."
        ),
        "duration": "Monthly",
    },
    "boost_100": {
        "name": "Listing Boost",
        "price": Decimal("100.00"),
        "service_type": "boost",
        "description": (
            "Give one eligible listing a visibility boost."
        ),
        "duration": "Boost",
    },
    "boost_500": {
        "name": "Listing Boost",
        "price": Decimal("500.00"),
        "service_type": "boost",
        "description": (
            "Give one eligible listing a stronger visibility boost."
        ),
        "duration": "Boost",
    },
    "featured_1000": {
        "name": "Featured Listing",
        "price": Decimal("1000.00"),
        "service_type": "featured",
        "description": (
            "Place an eligible listing in a featured position."
        ),
        "duration": "Featured",
    },
}


@login_required
def businesshub_services(request):

    # ============================================================
    # BUSINESSHUB FREE-LAUNCH STATUS
    # ============================================================

    free_launch = is_businesshub_free_launch()

    now = timezone.now()

    # ============================================================
    # GET THE USER'S REAL SUBSCRIPTION
    #
    # Preserve existing subscription records.
    # Do not create fake subscriptions during free launch.
    # ============================================================

    subscription = (
        BusinessHubSubscription.objects
        .filter(
            user=request.user,
            is_active=True,
            expiry_date__gt=now,
        )
        .order_by("-expiry_date")
        .first()
    )

    if free_launch:
        current_plan = "free_launch"

    elif subscription:
        current_plan = subscription.plan

    else:
        current_plan = "free"

    # ============================================================
    # PREPARE THE SERVICES
    # ============================================================

    services = []

    for service_code, service in BUSINESSHUB_SERVICES.items():

        services.append({
            "code": service_code,
            **service,
        })

    # ============================================================
    # DISPLAY SERVICES
    # ============================================================

    return render(
        request,
        "core/services.html",
        {
            "services": services,
            "current_plan": current_plan,
            "free_launch": free_launch,
        }
    )
@login_required
def payment_checkout(request):
    """
    BusinessHub free-launch checkout protection.

    During the free-launch period, paid checkout is disabled.
    Existing payment records and payment-provider integration
    are preserved.
    """

    from datetime import date

    free_launch_start = date(2026, 10, 12)
    free_launch_end = date(2027, 10, 12)
    today = timezone.localdate()

    if free_launch_start <= today < free_launch_end:
        messages.info(
            request,
            "BusinessHub is in its free-launch period! "
            "Plus, Pro, and promotional services are free "
            "during this period. No payment is required."
        )
        return redirect("businesshub_services")

    messages.info(
        request,
        "Online payments are temporarily unavailable. "
        "Please check back later."
    )
    return redirect("businesshub_services")


@login_required
def payment_status(
    request,
    reference
):

    payment = get_object_or_404(
        Payment,
        reference=reference,
        user=request.user
    )

    return render(
        request,
        "core/payment-status.html",
        {
            "payment": payment,
        }
    )


# =====================================================
# BUSINESSHUB SERVICE ACTIVATION
# =====================================================


def activate_businesshub_service(payment):

    service_reference = payment.service_reference

    # ============================================================
    # BUSINESSHUB SUBSCRIPTIONS
    # ============================================================

    if service_reference in {"plus", "pro"}:

        plan = service_reference

        now = timezone.now()

        subscription = (
            BusinessHubSubscription.objects.filter(
                user=payment.user
            )
            .order_by("-created_at")
            .first()
        )

        if subscription is None:

            subscription = (
                BusinessHubSubscription.objects.create(
                    user=payment.user,
                    plan=plan,
                    start_date=now,
                    expiry_date=(
                        now + timedelta(days=30)
                    ),
                    is_active=True,
                    payment=payment,
                )
            )

            message = (
                f"{subscription.get_plan_display()} "
                "has been activated for 30 days."
            )

        else:

            # ----------------------------------------------------
            # RENEWAL / UPGRADE
            # ----------------------------------------------------

            if (
                subscription.is_active
                and subscription.expiry_date > now
            ):

                # Preserve remaining subscription time.
                new_expiry_date = (
                    subscription.expiry_date
                    + timedelta(days=30)
                )

            else:

                # Subscription has expired.
                # Start a fresh 30-day period from now.
                new_expiry_date = (
                    now + timedelta(days=30)
                )

            subscription.plan = plan
            subscription.start_date = now
            subscription.expiry_date = new_expiry_date
            subscription.is_active = True
            subscription.payment = payment

            subscription.save()

            message = (
                f"{subscription.get_plan_display()} "
                "has been renewed for 30 days. "
                f"Your subscription is active until "
                f"{subscription.expiry_date.strftime('%b %d, %Y at %I:%M %p')}."
            )

        return True, message

    # ============================================================
    # LISTING PROMOTIONS
    # ============================================================

    listing_parts = service_reference.split(":")

    if len(listing_parts) == 3:

        service_code = listing_parts[0]
        listing_type = listing_parts[1]
        listing_id = listing_parts[2]

        # --------------------------------------------------------
        # CHECK PROMOTION SERVICE
        # --------------------------------------------------------

        if not (
            service_code.startswith("boost_")
            or service_code.startswith("featured_")
        ):

            return False, (
                "Payment was successful, but the "
                "promotion service could not be identified."
            )

        # --------------------------------------------------------
        # PROMOTION TYPE + DURATION
        # --------------------------------------------------------

        if service_code.startswith("boost_"):

            promotion_type = "boost"
            duration_days = 3
            notification_title = "🚀 Boost Activated"

        else:

            promotion_type = "featured"
            duration_days = 7
            notification_title = "⭐ Featured Activated"

        now = timezone.now()

        # ========================================================
        # ITEM PROMOTION
        # ========================================================

        if listing_type == "item":

            try:

                item_id = int(listing_id)

            except (TypeError, ValueError):

                return False, (
                    "Payment was successful, but the "
                    "listing could not be identified."
                )

            try:

                item = Item.objects.get(
                    id=item_id
                )

            except Item.DoesNotExist:

                return False, (
                    "Payment was successful, but the "
                    "item could not be found."
                )

            # ----------------------------------------------------
            # OWNERSHIP CHECK
            # ----------------------------------------------------

            if item.seller_id != payment.user_id:

                return False, (
                    "Payment was successful, but you "
                    "do not own the selected listing."
                )

            # ----------------------------------------------------
            # SUCCESS MESSAGE
            # ----------------------------------------------------

            if promotion_type == "boost":

                success_message = (
                    "🚀 Your item has been boosted for 3 days."
                )

            else:

                success_message = (
                    "⭐ Your item is now featured for 7 days."
                )

            # ----------------------------------------------------
            # CHECK EXISTING ACTIVE PROMOTION
            # ----------------------------------------------------

            existing_promotion = (
                ListingPromotion.objects.filter(
                    user=payment.user,
                    item=item,
                    service_type=promotion_type,
                    is_active=True,
                    expiry_date__gt=now,
                )
                .order_by("-expiry_date")
                .first()
            )

            # ----------------------------------------------------
            # EXTEND EXISTING PROMOTION
            # ----------------------------------------------------

            if existing_promotion:

                existing_promotion.expiry_date = (
                    existing_promotion.expiry_date
                    + timedelta(days=duration_days)
                )

                existing_promotion.payment = payment

                existing_promotion.save(
                    update_fields=[
                        "expiry_date",
                        "payment",
                        "updated_at",
                    ]
                )

                Notification.objects.create(
                    user=payment.user,
                    notification_type="system",
                    title=notification_title,
                    message=(
                        f"Your item "
                        f"'{item.title}' has been "
                        f"{promotion_type}ed again. "
                        f"Your promotion has been extended "
                        f"until "
                        f"{existing_promotion.expiry_date.strftime('%b %d, %Y at %I:%M %p')}."
                    ),
                    link=reverse(
                        "item_detail",
                        kwargs={
                            "item_id": item.id
                        }
                    ),
                )

                return True, (
                    f"{success_message} "
                    "The previous promotion was extended."
                )

            # ----------------------------------------------------
            # CREATE NEW ITEM PROMOTION
            # ----------------------------------------------------

            promotion = ListingPromotion.objects.create(
                user=payment.user,
                item=item,
                service_type=promotion_type,
                payment=payment,
                start_date=now,
                expiry_date=(
                    now
                    + timedelta(days=duration_days)
                ),
                is_active=True,
            )

            Notification.objects.create(
                user=payment.user,
                notification_type="system",
                title=notification_title,
                message=(
                    f"Your item "
                    f"'{item.title}' has been "
                    f"{'boosted' if promotion_type == 'boost' else 'featured'} successfully. "
                    f"It is active until "
                    f"{promotion.expiry_date.strftime('%b %d, %Y at %I:%M %p')}."
                ),
                link=reverse(
                    "item_detail",
                    kwargs={
                        "item_id": item.id
                    }
                ),
            )

            return True, success_message

        # ========================================================
        # FOOD PROMOTION
        # ========================================================

        elif listing_type == "food":

            try:

                food_id = int(listing_id)

            except (TypeError, ValueError):

                return False, (
                    "Payment was successful, but the "
                    "food listing could not be identified."
                )

            try:

                food = Food.objects.get(
                    id=food_id
                )

            except Food.DoesNotExist:

                return False, (
                    "Payment was successful, but the "
                    "food listing could not be found."
                )

            # ----------------------------------------------------
            # OWNERSHIP CHECK
            # ----------------------------------------------------

            if food.seller_id != payment.user_id:

                return False, (
                    "Payment was successful, but you "
                    "do not own the selected food listing."
                )

            # ----------------------------------------------------
            # SUCCESS MESSAGE
            # ----------------------------------------------------

            if promotion_type == "boost":

                success_message = (
                    "🚀 Your food listing has been boosted for 3 days."
                )

            else:

                success_message = (
                    "⭐ Your food listing is now featured for 7 days."
                )

            # ----------------------------------------------------
            # CHECK EXISTING ACTIVE PROMOTION
            # ----------------------------------------------------

            existing_promotion = (
                ListingPromotion.objects.filter(
                    user=payment.user,
                    food=food,
                    service_type=promotion_type,
                    is_active=True,
                    expiry_date__gt=now,
                )
                .order_by("-expiry_date")
                .first()
            )

            # ----------------------------------------------------
            # EXTEND EXISTING PROMOTION
            # ----------------------------------------------------

            if existing_promotion:

                existing_promotion.expiry_date = (
                    existing_promotion.expiry_date
                    + timedelta(days=duration_days)
                )

                existing_promotion.payment = payment

                existing_promotion.save(
                    update_fields=[
                        "expiry_date",
                        "payment",
                        "updated_at",
                    ]
                )

                Notification.objects.create(
                    user=payment.user,
                    notification_type="system",
                    title=notification_title,
                    message=(
                        f"Your food listing "
                        f"'{food.title}' has been "
                        f"{promotion_type}ed again. "
                        f"Your promotion has been extended "
                        f"until "
                        f"{existing_promotion.expiry_date.strftime('%b %d, %Y at %I:%M %p')}."
                    ),
                    link=reverse(
                        "food_detail",
                        kwargs={
                            "food_id": food.id
                        }
                    ),
                )

                return True, (
                    f"{success_message} "
                    "The previous promotion was extended."
                )

            # ----------------------------------------------------
            # CREATE NEW FOOD PROMOTION
            # ----------------------------------------------------

            promotion = ListingPromotion.objects.create(
                user=payment.user,
                food=food,
                service_type=promotion_type,
                payment=payment,
                start_date=now,
                expiry_date=(
                    now
                    + timedelta(days=duration_days)
                ),
                is_active=True,
            )

            Notification.objects.create(
                user=payment.user,
                notification_type="system",
                title=notification_title,
                message=(
                    f"Your food listing "
                    f"'{food.title}' has been "
                    f"{'boosted' if promotion_type == 'boost' else 'featured'} successfully. "
                    f"It is active until "
                    f"{promotion.expiry_date.strftime('%b %d, %Y at %I:%M %p')}."
                ),
                link=reverse(
                    "food_detail",
                    kwargs={
                        "food_id": food.id
                    }
                ),
            )

            return True, success_message

        # --------------------------------------------------------
        # UNKNOWN LISTING TYPE
        # --------------------------------------------------------

        return False, (
            "Payment was successful, but the "
            "listing type could not be identified."
        )

    # ============================================================
    # FALLBACK
    # ============================================================

    return False, (
        "Payment was successful, but the service "
        "could not be activated automatically."
    )


def get_active_businesshub_subscription(user):
    """
    Return the user's current active BusinessHub subscription,
    or None if they do not have one.
    """

    return (
        BusinessHubSubscription.objects.filter(
            user=user,
            is_active=True,
            expiry_date__gt=timezone.now(),
        )
        .order_by("-expiry_date")
        .first()
    )
def is_businesshub_free_launch():
    """
    Return True while BusinessHub's first-year free launch is active.

    Free-launch period:
    12 October 2026 to 11 October 2027, inclusive.
    """
    from datetime import date

    today = timezone.localdate()

    return (
        date(2026, 10, 12)
        <= today
        < date(2027, 10, 12)
    )
@login_required
def check_payment_status(request, reference):
    payment = get_object_or_404(
        Payment,
        reference=reference,
        user=request.user,
    )

    # Stop checking payments that have already reached
    # a terminal status.
    if payment.status in {
        "successful",
        "failed",
        "cancelled",
    }:
        return redirect(
            "payment_status",
            reference=payment.reference,
        )

    # Only MTN MoMo currently supports live status checks.
    if payment.payment_method != "mtn_momo":
        messages.info(
            request,
            "This payment provider does not have "
            "a live status check available yet.",
        )

        return redirect(
            "payment_status",
            reference=payment.reference,
        )

    if not payment.transaction_id:
        messages.error(
            request,
            "There is no MTN transaction reference "
            "available for this payment yet.",
        )

        return redirect(
            "payment_status",
            reference=payment.reference,
        )

    try:
        from .payment_providers.mtn_momo import (
            MTNMoMoProvider,
            MTNMoMoError,
        )

        provider = MTNMoMoProvider()

        if not provider.is_configured():
            messages.warning(
                request,
                "MTN MoMo credentials are not configured yet.",
            )

            return redirect(
                "payment_status",
                reference=payment.reference,
            )

        # Ask MTN for the actual transaction status.
        result = provider.payment_status(
            payment.transaction_id
        )

        provider_status = str(
            result.get("status", "")
        ).strip().upper()

        # Process the response using a database transaction.
        # PostgreSQL row locking prevents concurrent requests
        # from processing the same payment simultaneously.
        activation_failed = False
        activation_message = ""

        with transaction.atomic():
            locked_payment = (
                Payment.objects
                .select_for_update()
                .get(pk=payment.pk)
            )

            # Another request may have processed this payment
            # while we were waiting for MTN's response.
            if locked_payment.status in {
                "successful",
                "failed",
                "cancelled",
            }:
                return redirect(
                    "payment_status",
                    reference=locked_payment.reference,
                )

            # ---------------------------------------------
            # SUCCESSFUL PAYMENT
            # ---------------------------------------------
            if provider_status == "SUCCESSFUL":
                locked_payment.status = "successful"
                locked_payment.provider_response = str(result)

                locked_payment.save(
                    update_fields=[
                        "status",
                        "provider_response",
                        "updated_at",
                    ]
                )

                # Activate the service in the same database
                # transaction as the payment-status change.
                activated, activation_message = (
                    activate_businesshub_service(
                        locked_payment
                    )
                )

                if not activated:
                    # Undo the database changes from this
                    # attempt so activation can be retried.
                    transaction.set_rollback(True)
                    activation_failed = True

            # ---------------------------------------------
            # FAILED PAYMENT
            # ---------------------------------------------
            elif provider_status == "FAILED":
                locked_payment.status = "failed"
                locked_payment.provider_response = str(result)

                locked_payment.save(
                    update_fields=[
                        "status",
                        "provider_response",
                        "updated_at",
                    ]
                )

            # ---------------------------------------------
            # PAYMENT STILL PROCESSING
            # ---------------------------------------------
            elif provider_status in {
                "PENDING",
                "ONGOING",
            }:
                locked_payment.status = "pending"
                locked_payment.provider_response = str(result)

                locked_payment.save(
                    update_fields=[
                        "status",
                        "provider_response",
                        "updated_at",
                    ]
                )

            # ---------------------------------------------
            # UNKNOWN PROVIDER STATUS
            # ---------------------------------------------
            else:
                # Preserve the current payment status when
                # MTN returns an unfamiliar status.
                locked_payment.provider_response = str(result)

                locked_payment.save(
                    update_fields=[
                        "provider_response",
                        "updated_at",
                    ]
                )

        # The transaction has now completed.
        if activation_failed:
            # The activation transaction was rolled back.
            # Save MTN's response separately so the result
            # remains available for troubleshooting.
            payment.refresh_from_db()

            payment.provider_response = str(result)

            payment.save(
                update_fields=[
                    "provider_response",
                    "updated_at",
                ]
            )

            messages.warning(
                request,
                "MTN confirmed your payment, but BusinessHub "
                "could not activate the service. Your payment "
                "remains pending in BusinessHub so activation "
                "can be retried. Please check again or contact "
                "support if the problem continues. "
                + activation_message,
            )

        elif provider_status == "SUCCESSFUL":
            messages.success(
                request,
                activation_message,
            )

        elif provider_status == "FAILED":
            messages.error(
                request,
                "MTN MoMo confirmed that this payment failed.",
            )

        elif provider_status in {"PENDING", "ONGOING"}:
            messages.info(
                request,
                "Your MTN MoMo payment is still being processed. "
                "Please check again shortly.",
            )

        else:
            messages.warning(
                request,
                "MTN returned an unrecognized payment status. "
                "Your payment has not been marked successful.",
            )

    except MTNMoMoError:
        messages.error(
            request,
            "We could not retrieve the MTN MoMo payment status. "
            "Please try again shortly.",
        )

    except Exception:
        messages.error(
            request,
            "An unexpected error occurred while checking "
            "your payment. Please try again.",
        )

    return redirect(
        "payment_status",
        reference=payment.reference,
    )
# =====================================================
# ITEMS MARKETPLACE
# =====================================================
def items_marketplace(request):

    query = request.GET.get(
        "q",
        ""
    ).strip()

    selected_category = request.GET.get(
        "category",
        ""
    ).strip()

    items = Item.objects.filter(
        status="available"
    ).select_related(
        "seller"
    ).prefetch_related(
        "images"
    )

    if query:
        items = items.filter(
            Q(title__icontains=query)
            |
            Q(description__icontains=query)
            |
            Q(location__icontains=query)
            |
            Q(category__icontains=query)
        )

    if selected_category:
        items = items.filter(
            category=selected_category
        )

    # ---------------------------------------------------------
    # ACTIVE PROMOTIONS
    # ---------------------------------------------------------

    items = list(
        items.order_by(
            "-created_at"
        )
    )

    now = timezone.now()

    item_ids = [
        item.id
        for item in items
    ]

    active_promotions = list(
        ListingPromotion.objects.filter(
            item_id__in=item_ids,
            is_active=True,
            expiry_date__gt=now,
        ).values(
            "item_id",
            "service_type",
            "expiry_date",
        )
    )

    promotion_priority = {}

    for promotion in active_promotions:

        item_id = promotion["item_id"]
        service_type = promotion["service_type"]

        if service_type == "featured":
            priority = 2

        elif service_type == "boost":
            priority = 1

        else:
            priority = 0

        current_priority = promotion_priority.get(
            item_id,
            0
        )

        if priority > current_priority:
            promotion_priority[item_id] = priority

    # ---------------------------------------------------------
    # ATTACH ACTIVE PROMOTION INFORMATION
    # ---------------------------------------------------------

    for item in items:
        item.active_boost = None
        item.active_featured = None

    for promotion in active_promotions:

        item_id = promotion["item_id"]
        service_type = promotion["service_type"]

        for item in items:

            if item.id == item_id:

                if service_type == "boost":
                    item.active_boost = promotion

                elif service_type == "featured":
                    item.active_featured = promotion

                break

    # ---------------------------------------------------------
    # MARKETPLACE ORDER
    # ---------------------------------------------------------

    items.sort(
        key=lambda item: (
            promotion_priority.get(
                item.id,
                0
            ),
            item.created_at,
        ),
        reverse=True
    )

    return render(
        request,
        "core/items.html",
        {
            "items": items,
            "query": query,
            "selected_category": selected_category,
            "categories": Item.CATEGORY_CHOICES,
            "free_launch": is_businesshub_free_launch(),
        }
    )
@login_required
def boost_item(request, item_id):
    from datetime import date

    item = get_object_or_404(Item, id=item_id)

    # Only the seller can boost the item.
    if item.seller != request.user:
        messages.error(
            request,
            "You can only boost your own items."
        )
        return redirect("item_detail", item_id=item.id)

    # Only available items can be boosted.
    if item.status != "available":
        messages.error(
            request,
            "Only available items can be boosted."
        )
        return redirect("item_detail", item_id=item.id)

    # Free-launch period: 12 October 2026 to 11 October 2027.
    today = timezone.localdate()
    free_launch = (
        date(2026, 10, 12)
        <= today
        < date(2027, 10, 12)
    )

    if not free_launch:
        return redirect(
            f"{reverse('payment_checkout')}?service=boost_100&item_id={item.id}"
        )

    now = timezone.now()
    duration = timedelta(days=3)

    existing_promotion = (
        ListingPromotion.objects.filter(
            user=request.user,
            item=item,
            service_type="boost",
            is_active=True,
            expiry_date__gt=now,
        )
        .order_by("-expiry_date")
        .first()
    )

    if existing_promotion:
        existing_promotion.expiry_date += duration
        existing_promotion.save(
            update_fields=["expiry_date", "updated_at"]
        )
        expiry_date = existing_promotion.expiry_date
        message_text = (
            f"Your item '{item.title}' has been boosted again. "
            f"Your promotion has been extended until "
            f"{expiry_date.strftime('%b %d, %Y at %I:%M %p')}."
        )
        success_message = (
            "Your item has been boosted for another 3 days."
        )
    else:
        promotion = ListingPromotion.objects.create(
            user=request.user,
            item=item,
            service_type="boost",
            payment=None,
            start_date=now,
            expiry_date=now + duration,
            is_active=True,
        )
        expiry_date = promotion.expiry_date
        message_text = (
            f"Your item '{item.title}' has been boosted successfully. "
            f"It is active until "
            f"{expiry_date.strftime('%b %d, %Y at %I:%M %p')}."
        )
        success_message = (
            "Your item has been boosted for 3 days for free!"
        )

    Notification.objects.create(
        user=request.user,
        notification_type="system",
        title="🚀 Boost Activated",
        message=message_text,
        link=reverse("item_detail", kwargs={"item_id": item.id}),
    )

    messages.success(request, success_message)
    return redirect("item_detail", item_id=item.id)


@login_required
def feature_item(request, item_id):
    from datetime import date

    item = get_object_or_404(Item, id=item_id)

    # Only the seller can feature the item.
    if item.seller != request.user:
        messages.error(
            request,
            "You can only feature your own items."
        )
        return redirect("item_detail", item_id=item.id)

    # Only available items can be featured.
    if item.status != "available":
        messages.error(
            request,
            "Only available items can be featured."
        )
        return redirect("item_detail", item_id=item.id)

    # Free-launch period: 12 October 2026 to 11 October 2027.
    today = timezone.localdate()
    free_launch = (
        date(2026, 10, 12)
        <= today
        < date(2027, 10, 12)
    )

    if not free_launch:
        return redirect(
            f"{reverse('payment_checkout')}?service=featured_1000&item_id={item.id}"
        )

    now = timezone.now()
    duration = timedelta(days=7)

    existing_promotion = (
        ListingPromotion.objects.filter(
            user=request.user,
            item=item,
            service_type="featured",
            is_active=True,
            expiry_date__gt=now,
        )
        .order_by("-expiry_date")
        .first()
    )

    if existing_promotion:
        existing_promotion.expiry_date += duration
        existing_promotion.save(
            update_fields=["expiry_date", "updated_at"]
        )
        expiry_date = existing_promotion.expiry_date
        message_text = (
            f"Your item '{item.title}' has been featured again. "
            f"Your promotion has been extended until "
            f"{expiry_date.strftime('%b %d, %Y at %I:%M %p')}."
        )
        success_message = (
            "Your item has been featured for another 7 days."
        )
    else:
        promotion = ListingPromotion.objects.create(
            user=request.user,
            item=item,
            service_type="featured",
            payment=None,
            start_date=now,
            expiry_date=now + duration,
            is_active=True,
        )
        expiry_date = promotion.expiry_date
        message_text = (
            f"Your item '{item.title}' has been featured successfully. "
            f"It is active until "
            f"{expiry_date.strftime('%b %d, %Y at %I:%M %p')}."
        )
        success_message = (
            "Your item is now featured for 7 days for free!"
        )

    Notification.objects.create(
        user=request.user,
        notification_type="system",
        title="⭐ Featured Activated",
        message=message_text,
        link=reverse("item_detail", kwargs={"item_id": item.id}),
    )

    messages.success(request, success_message)
    return redirect("item_detail", item_id=item.id)

@login_required
def item_detail(
    request,
    item_id
):

    item = get_object_or_404(
        Item.objects.select_related(
            "seller"
        ).prefetch_related(
            "images"
        ),
        id=item_id
    )

    now = timezone.now()

    active_boost = (
        ListingPromotion.objects.filter(
            item=item,
            service_type="boost",
            is_active=True,
            expiry_date__gt=now,
        )
        .order_by("-expiry_date")
        .first()
    )

    active_featured = (
        ListingPromotion.objects.filter(
            item=item,
            service_type="featured",
            is_active=True,
            expiry_date__gt=now,
        )
        .order_by("-expiry_date")
        .first()
    )

    return render(
        request,
        "core/item-detail.html",
        {
            "item": item,
            "active_boost": active_boost,
            "active_featured": active_featured,
        }
    )

@login_required
def sell_item(request):

    if request.method == "POST":

        title = request.POST.get(
            "title",
            ""
        ).strip()

        category = request.POST.get(
            "category",
            ""
        ).strip()

        price = request.POST.get(
            "price",
            ""
        ).strip()

        description = request.POST.get(
            "description",
            ""
        ).strip()

        condition = request.POST.get(
            "condition",
            "used"
        ).strip()

        location = request.POST.get(
            "location",
            ""
        ).strip()

        negotiable = (
            request.POST.get(
                "negotiable"
            )
            == "on"
        )

        images = request.FILES.getlist(
            "images"
        )

        form_data = {
            "categories": Item.CATEGORY_CHOICES,
            "conditions": Item.CONDITION_CHOICES,
        }

        if not title:

            form_data["error"] = (
                "Please enter an item title."
            )

            return render(
                request,
                "core/sell-item.html",
                form_data
            )

        if not category:

            form_data["error"] = (
                "Please select a category."
            )

            return render(
                request,
                "core/sell-item.html",
                form_data
            )

        if not price:

            form_data["error"] = (
                "Please enter a price."
            )

            return render(
                request,
                "core/sell-item.html",
                form_data
            )

        if not description:

            form_data["error"] = (
                "Please describe your item."
            )

            return render(
                request,
                "core/sell-item.html",
                form_data
            )

        if not location:

            form_data["error"] = (
                "Please enter your location."
            )

            return render(
                request,
                "core/sell-item.html",
                form_data
            )

        try:

            price_value = float(price)

            if price_value < 0:
                raise ValueError

        except (TypeError, ValueError):

            form_data["error"] = (
                "Please enter a valid price."
            )

            return render(
                request,
                "core/sell-item.html",
                form_data
            )

        if category not in dict(
            Item.CATEGORY_CHOICES
        ):

            form_data["error"] = (
                "Invalid category selected."
            )

            return render(
                request,
                "core/sell-item.html",
                form_data
            )

        if condition not in dict(
            Item.CONDITION_CHOICES
        ):

            form_data["error"] = (
                "Invalid condition selected."
            )

            return render(
                request,
                "core/sell-item.html",
                form_data
            )

        item = Item.objects.create(
            seller=request.user,
            title=title,
            category=category,
            price=price_value,
            description=description,
            condition=condition,
            location=location,
            negotiable=negotiable,
        )

        for image in images[:10]:

            ItemImage.objects.create(
                item=item,
                image=image
            )

        messages.success(
            request,
            "Your item has been listed successfully."
        )

        return redirect(
            "item_detail",
            item_id=item.id
        )

    return render(
        request,
        "core/sell-item.html",
        {
            "categories": Item.CATEGORY_CHOICES,
            "conditions": Item.CONDITION_CHOICES,
        }
    )


@login_required
def my_items(request):

    items = Item.objects.filter(
        seller=request.user
    ).prefetch_related(
        "images"
    ).order_by(
        "-created_at"
    )

    return render(
        request,
        "core/my-items.html",
        {
            "items": items
        }
    )


@login_required
def edit_item(
    request,
    item_id
):

    item = get_object_or_404(
        Item,
        id=item_id,
        seller=request.user
    )

    if request.method == "POST":

        title = request.POST.get(
            "title",
            ""
        ).strip()

        category = request.POST.get(
            "category",
            ""
        ).strip()

        price = request.POST.get(
            "price",
            ""
        ).strip()

        description = request.POST.get(
            "description",
            ""
        ).strip()

        condition = request.POST.get(
            "condition",
            "used"
        ).strip()

        location = request.POST.get(
            "location",
            ""
        ).strip()

        negotiable = (
            request.POST.get(
                "negotiable"
            )
            == "on"
        )

        form_data = {
            "item": item,
            "categories": Item.CATEGORY_CHOICES,
            "conditions": Item.CONDITION_CHOICES,
        }

        if not title:

            form_data["error"] = (
                "Please enter an item title."
            )

            return render(
                request,
                "core/edit-item.html",
                form_data
            )

        if not category:

            form_data["error"] = (
                "Please select a category."
            )

            return render(
                request,
                "core/edit-item.html",
                form_data
            )

        if not price:

            form_data["error"] = (
                "Please enter a price."
            )

            return render(
                request,
                "core/edit-item.html",
                form_data
            )

        if not description:

            form_data["error"] = (
                "Please describe your item."
            )

            return render(
                request,
                "core/edit-item.html",
                form_data
            )

        if not location:

            form_data["error"] = (
                "Please enter your location."
            )

            return render(
                request,
                "core/edit-item.html",
                form_data
            )

        try:

            price_value = float(price)

            if price_value < 0:
                raise ValueError

        except (TypeError, ValueError):

            form_data["error"] = (
                "Please enter a valid price."
            )

            return render(
                request,
                "core/edit-item.html",
                form_data
            )

        if category not in dict(
            Item.CATEGORY_CHOICES
        ):

            form_data["error"] = (
                "Invalid category selected."
            )

            return render(
                request,
                "core/edit-item.html",
                form_data
            )

        if condition not in dict(
            Item.CONDITION_CHOICES
        ):

            form_data["error"] = (
                "Invalid condition selected."
            )

            return render(
                request,
                "core/edit-item.html",
                form_data
            )

        item.title = title
        item.category = category
        item.price = price_value
        item.description = description
        item.condition = condition
        item.location = location
        item.negotiable = negotiable

        item.save()

        new_images = request.FILES.getlist(
            "images"
        )

        for image in new_images:

            if item.images.count() >= 10:
                break

            ItemImage.objects.create(
                item=item,
                image=image
            )

        messages.success(
            request,
            "Your item has been updated."
        )

        return redirect(
            "item_detail",
            item_id=item.id
        )

    return render(
        request,
        "core/edit-item.html",
        {
            "item": item,
            "categories": Item.CATEGORY_CHOICES,
            "conditions": Item.CONDITION_CHOICES,
        }
    )

@login_required
def delete_item_image(request, image_id):
    image = get_object_or_404(
        ItemImage,
        id=image_id,
        item__seller=request.user
    )

    item_id = image.item.id

    if request.method == "POST":
        if image.image:
            image.image.delete(save=False)

        image.delete()

        messages.success(
            request,
            "Item image deleted successfully."
        )

    return redirect("edit_item", item_id=item_id)

@login_required
def delete_item(
    request,
    item_id
):

    item = get_object_or_404(
        Item,
        id=item_id,
        seller=request.user
    )

    if request.method == "POST":

        item.delete()

        messages.success(
            request,
            "Your item has been deleted."
        )

        return redirect(
            "my_items"
        )

    return render(
        request,
        "core/delete-item.html",
        {
            "item": item
        }
    )


@login_required
def mark_item_sold(
    request,
    item_id
):

    item = get_object_or_404(
        Item,
        id=item_id,
        seller=request.user
    )

    if request.method == "POST":

        item.status = "sold"

        item.save(
            update_fields=[
                "status",
                "updated_at"
            ]
        )

        messages.success(
            request,
            "Your item has been marked as sold."
        )

    return redirect(
        "my_items"
    )


# =====================================================
# FOOD MARKETPLACE
# =====================================================

def food_marketplace(request):

    query = request.GET.get(
        "q",
        ""
    ).strip()

    selected_category = request.GET.get(
        "category",
        ""
    ).strip()

    foods = Food.objects.filter(
        status="available"
    ).select_related(
        "seller"
    ).prefetch_related(
        "images"
    )

    if query:
        foods = foods.filter(
            Q(title__icontains=query)
            |
            Q(description__icontains=query)
            |
            Q(location__icontains=query)
            |
            Q(category__icontains=query)
        )

    if selected_category:
        foods = foods.filter(
            category=selected_category
        )

    foods = list(
        foods.order_by(
            "-created_at"
        )
    )

    now = timezone.now()

    food_ids = [
        food.id
        for food in foods
    ]

    active_promotions = list(
        ListingPromotion.objects.filter(
            food_id__in=food_ids,
            is_active=True,
            expiry_date__gt=now,
        ).values(
            "food_id",
            "service_type",
            "expiry_date",
        )
    )

    promotion_priority = {}

    for promotion in active_promotions:

        food_id = promotion["food_id"]
        service_type = promotion["service_type"]

        if service_type == "featured":
            priority = 2

        elif service_type == "boost":
            priority = 1

        else:
            priority = 0

        current_priority = promotion_priority.get(
            food_id,
            0
        )

        if priority > current_priority:
            promotion_priority[food_id] = priority

    for food in foods:
        food.active_boost = None
        food.active_featured = None

    for promotion in active_promotions:

        food_id = promotion["food_id"]
        service_type = promotion["service_type"]

        for food in foods:

            if food.id == food_id:

                if service_type == "boost":
                    food.active_boost = promotion

                elif service_type == "featured":
                    food.active_featured = promotion

                break

    foods.sort(
        key=lambda food: (
            promotion_priority.get(
                food.id,
                0
            ),
            food.created_at,
        ),
        reverse=True,
    )

    return render(
        request,
        "core/food.html",
        {
            "foods": foods,
            "query": query,
            "selected_category": selected_category,
            "categories": Food.CATEGORY_CHOICES,
            "free_launch": is_businesshub_free_launch(),
        }
    )
def food_detail(
    request,
    food_id
):

    food = get_object_or_404(
        Food.objects.select_related(
            "seller"
        ).prefetch_related(
            "images"
        ),
        id=food_id
    )

    now = timezone.now()

    active_promotions = ListingPromotion.objects.filter(
        food=food,
        is_active=True,
        expiry_date__gt=now
    )

    food.active_boost = active_promotions.filter(
        service_type="boost"
    ).first()

    food.active_featured = active_promotions.filter(
        service_type="featured"
    ).first()

    return render(
        request,
        "core/food-detail.html",
        {
            "food": food
        }
    )



@login_required
def sell_food(request):

    if request.method == "POST":

        title = request.POST.get(
            "title",
            ""
        ).strip()

        category = request.POST.get(
            "category",
            ""
        ).strip()

        price = request.POST.get(
            "price",
            ""
        ).strip()

        description = request.POST.get(
            "description",
            ""
        ).strip()

        location = request.POST.get(
            "location",
            ""
        ).strip()

        quantity = request.POST.get(
            "quantity",
            "1"
        ).strip()

        pickup_available = (
            request.POST.get(
                "pickup_available"
            )
            == "on"
        )

        delivery_available = (
            request.POST.get(
                "delivery_available"
            )
            == "on"
        )

        delivery_information = request.POST.get(
            "delivery_information",
            ""
        ).strip()

        images = request.FILES.getlist(
            "images"
        )

        form_data = {
            "categories": Food.CATEGORY_CHOICES,
        }

        if not title:

            form_data["error"] = (
                "Please enter a food name."
            )

            return render(
                request,
                "core/sell-food.html",
                form_data
            )

        if not category:

            form_data["error"] = (
                "Please select a food category."
            )

            return render(
                request,
                "core/sell-food.html",
                form_data
            )

        if not price:

            form_data["error"] = (
                "Please enter a price."
            )

            return render(
                request,
                "core/sell-food.html",
                form_data
            )

        if not description:

            form_data["error"] = (
                "Please describe the food."
            )

            return render(
                request,
                "core/sell-food.html",
                form_data
            )

        if not location:

            form_data["error"] = (
                "Please enter your location."
            )

            return render(
                request,
                "core/sell-food.html",
                form_data
            )

        try:

            price_value = Decimal(price)

            if price_value < 0:
                raise InvalidOperation

        except (InvalidOperation, ValueError, TypeError):

            form_data["error"] = (
                "Please enter a valid price."
            )

            return render(
                request,
                "core/sell-food.html",
                form_data
            )

        try:

            quantity_value = int(quantity)

            if quantity_value < 1:
                raise ValueError

        except (TypeError, ValueError):

            form_data["error"] = (
                "Quantity must be at least 1."
            )

            return render(
                request,
                "core/sell-food.html",
                form_data
            )

        if category not in dict(
            Food.CATEGORY_CHOICES
        ):

            form_data["error"] = (
                "Invalid food category selected."
            )

            return render(
                request,
                "core/sell-food.html",
                form_data
            )

        food = Food.objects.create(
            seller=request.user,
            title=title,
            category=category,
            price=price_value,
            description=description,
            location=location,
            quantity=quantity_value,
            status="available",
            pickup_available=pickup_available,
            delivery_available=delivery_available,
            delivery_information=delivery_information,
        )

        for image in images[:10]:

            FoodImage.objects.create(
                food=food,
                image=image
            )

        messages.success(
            request,
            "Your food has been listed successfully."
        )

        return redirect(
            "food_detail",
            food_id=food.id
        )

    return render(
        request,
        "core/sell-food.html",
        {
            "categories": Food.CATEGORY_CHOICES,
        }
    )


@login_required
def my_food(request):

    foods = Food.objects.filter(
        seller=request.user
    ).prefetch_related(
        "images"
    ).order_by(
        "-created_at"
    )

    return render(
        request,
        "core/my-food.html",
        {
            "foods": foods
        }
    )


@login_required
def edit_food(
    request,
    food_id
):

    food = get_object_or_404(
        Food,
        id=food_id,
        seller=request.user
    )

    if request.method == "POST":

        title = request.POST.get(
            "title",
            ""
        ).strip()

        category = request.POST.get(
            "category",
            ""
        ).strip()

        price = request.POST.get(
            "price",
            ""
        ).strip()

        description = request.POST.get(
            "description",
            ""
        ).strip()

        location = request.POST.get(
            "location",
            ""
        ).strip()

        quantity = request.POST.get(
            "quantity",
            "1"
        ).strip()

        pickup_available = (
            request.POST.get(
                "pickup_available"
            )
            == "on"
        )

        delivery_available = (
            request.POST.get(
                "delivery_available"
            )
            == "on"
        )

        delivery_information = request.POST.get(
            "delivery_information",
            ""
        ).strip()

        form_data = {
            "food": food,
            "categories": Food.CATEGORY_CHOICES,
        }

        if not title:

            form_data["error"] = (
                "Please enter a food name."
            )

            return render(
                request,
                "core/edit-food.html",
                form_data
            )

        if not category:

            form_data["error"] = (
                "Please select a food category."
            )

            return render(
                request,
                "core/edit-food.html",
                form_data
            )

        if not price:

            form_data["error"] = (
                "Please enter a price."
            )

            return render(
                request,
                "core/edit-food.html",
                form_data
            )

        if not description:

            form_data["error"] = (
                "Please describe the food."
            )

            return render(
                request,
                "core/edit-food.html",
                form_data
            )

        if not location:

            form_data["error"] = (
                "Please enter your location."
            )

            return render(
                request,
                "core/edit-food.html",
                form_data
            )

        try:

            price_value = Decimal(price)

            if price_value < 0:
                raise InvalidOperation

        except (InvalidOperation, ValueError, TypeError):

            form_data["error"] = (
                "Please enter a valid price."
            )

            return render(
                request,
                "core/edit-food.html",
                form_data
            )

        try:

            quantity_value = int(quantity)

            if quantity_value < 1:
                raise ValueError

        except (TypeError, ValueError):

            form_data["error"] = (
                "Quantity must be at least 1."
            )

            return render(
                request,
                "core/edit-food.html",
                form_data
            )

        if category not in dict(
            Food.CATEGORY_CHOICES
        ):

            form_data["error"] = (
                "Invalid food category selected."
            )

            return render(
                request,
                "core/edit-food.html",
                form_data
            )

        food.title = title
        food.category = category
        food.price = price_value
        food.description = description
        food.location = location
        food.quantity = quantity_value
        food.pickup_available = pickup_available
        food.delivery_available = delivery_available
        food.delivery_information = delivery_information

        food.save()

        new_images = request.FILES.getlist(
            "images"
        )

        for image in new_images:

            if food.images.count() >= 10:
                break

            FoodImage.objects.create(
                food=food,
                image=image
            )

        messages.success(
            request,
            "Your food listing has been updated."
        )

        return redirect(
            "food_detail",
            food_id=food.id
        )

    return render(
        request,
        "core/edit-food.html",
        {
            "food": food,
            "categories": Food.CATEGORY_CHOICES,
        }
    )

@login_required
def delete_food_image(request, image_id):
    image = get_object_or_404(
        FoodImage,
        id=image_id,
        food__seller=request.user
    )

    food_id = image.food.id

    if request.method == "POST":
        if image.image:
            image.image.delete(save=False)

        image.delete()

        messages.success(
            request,
            "Food image deleted successfully."
        )

        return JsonResponse({
            "success": True
        })

    return JsonResponse(
        {"success": False},
        status=405
    )

@login_required
def delete_food(
    request,
    food_id
):

    food = get_object_or_404(
        Food,
        id=food_id,
        seller=request.user
    )

    if request.method == "POST":

        food.delete()

        messages.success(
            request,
            "Your food listing has been deleted."
        )

        return redirect(
            "my_food"
        )

    return render(
        request,
        "core/delete-food.html",
        {
            "food": food
        }
    )


@login_required
def mark_food_unavailable(
    request,
    food_id
):

    food = get_object_or_404(
        Food,
        id=food_id,
        seller=request.user
    )

    if request.method == "POST":

        food.status = "unavailable"

        food.save(
            update_fields=[
                "status",
                "updated_at"
            ]
        )

        messages.success(
            request,
            "Your food has been marked as unavailable."
        )

    return redirect(
        "my_food"
    )


@login_required
def message_food_seller(
    request,
    food_id
):

    food = get_object_or_404(
        Food.objects.select_related(
            "seller"
        ),
        id=food_id
    )

    # Seller cannot message themselves
    if food.seller_id == request.user.id:

        return redirect(
            "food_detail",
            food_id=food.id
        )

    conversation = Conversation.objects.filter(
        food=food,
        customer=request.user,
        seller=food.seller
    ).first()

    if conversation is None:

        conversation = Conversation.objects.create(
            food=food,
            customer=request.user,
            seller=food.seller,
            business=None,
            item=None
        )

    return redirect(
        "conversation_detail",
        conversation_id=conversation.id
    )


# =====================================================
# PACKAGE TRACKING API
# =====================================================

def package_location_api(
    request,
    tracking_number
):

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


def save_package_location_api(
    request,
    tracking_number
):

    if request.method != "POST":

        return JsonResponse(
            {
                "error": "POST request required"
            },
            status=405
        )

    package = get_object_or_404(
        Package,
        tracking_number=tracking_number
    )

    latitude = request.POST.get(
        "latitude"
    )

    longitude = request.POST.get(
        "longitude"
    )

    if not latitude or not longitude:

        return JsonResponse(
            {
                "error": (
                    "Latitude and longitude are required"
                )
            },
            status=400
        )

    try:

        latitude = float(latitude)
        longitude = float(longitude)

    except (TypeError, ValueError):

        return JsonResponse(
            {
                "error": (
                    "Invalid latitude or longitude."
                )
            },
            status=400
        )

    latest_update = package.updates.first()

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

    location_name = "Location updating..."

    try:

        geolocator = Nominatim(
            user_agent="businesshub_tracking"
        )

        location_data = geolocator.reverse(
            (
                latitude,
                longitude
            ),
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

    TrackingUpdate.objects.create(
        package=package,
        status=package.status,
        location=location_name,
        latitude=latitude,
        longitude=longitude,
        description=(
            "Package location updated automatically."
        )
    )

    create_tracking_notification(
        package=package,
        title="Package location updated",
        message=(
            f"Your package "
            f"{package.tracking_number} "
            f"is now in "
            f"{location_name}."
        )
    )

    return JsonResponse({
        "saved": True,
        "location": location_name,
        "message": (
            "Location saved to tracking history"
        )
    })


# =====================================================
# MESSAGING
# =====================================================

@login_required
def message_business(
    request,
    business_id
):

    business = get_object_or_404(
        Business,
        id=business_id
    )

    # Business owners should not message themselves
    if business.owner_id == request.user.id:

        return redirect(
            "messages_inbox"
        )

    conversation, created = (
        Conversation.objects.get_or_create(
            business=business,
            customer=request.user,
            defaults={
                "item": None,
                "food": None,
                "seller": None,
            }
        )
    )

    if request.method == "POST":

        message_text = request.POST.get(
            "message",
            ""
        ).strip()

        if message_text:

            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                text=message_text
            )

            conversation.save()

            create_message_notification(
                conversation=conversation,
                sender=request.user,
                message_text=message_text
            )

            return redirect(
                "conversation_detail",
                conversation_id=conversation.id
            )

    return render(
        request,
        "core/message-business.html",
        {
            "business": business,
            "conversation": conversation
        }
    )


@login_required
def message_item_seller(
    request,
    item_id
):

    item = get_object_or_404(
        Item.objects.select_related(
            "seller"
        ),
        id=item_id
    )

    # Seller cannot message themselves through this button
    if item.seller_id == request.user.id:

        return redirect(
            "item_detail",
            item_id=item.id
        )

    conversation = Conversation.objects.filter(
        item=item,
        customer=request.user,
        seller=item.seller
    ).first()

    if conversation is None:

        conversation = Conversation.objects.create(
            item=item,
            customer=request.user,
            seller=item.seller,
            business=None,
            food=None
        )

    return redirect(
        "conversation_detail",
        conversation_id=conversation.id
    )
def _businesshub_message_attachment_data(message):
    """
    Return attachment metadata for the messaging interface.

    The attachment URL will be protected by a separate view that
    verifies conversation membership before serving the file.
    """
    if not message.attachment:
        return {
            "has_attachment": False,
            "attachment_url": None,
            "attachment_name": "",
            "attachment_size": 0,
            "attachment_kind": "",
            "attachment_content_type": "",
        }

    return {
        "has_attachment": True,
        "attachment_url": (
            f"/message-attachment/{message.pk}/"
        ),
        "attachment_name": (
            message.attachment_original_name
            or "Attachment"
        ),
        "attachment_size": message.attachment_size,
        "attachment_kind": message.attachment_kind,
        "attachment_content_type": (
            message.attachment_content_type
        ),
    }
@login_required
def messages_inbox(request):
    import logging
    import os
    import mimetypes

    from django.conf import settings
    from django.core.exceptions import ValidationError
    from django.db import transaction
    from django.db.models import Q
    from django.http import JsonResponse
    from django.shortcuts import redirect, render
    from django.utils import timezone

    from PIL import Image

    logger = logging.getLogger(__name__)

    MAX_ATTACHMENT_SIZE = 50 * 1024 * 1024

    IMAGE_EXTENSIONS = {
        ".jpg", ".jpeg", ".png", ".webp", ".gif",
    }

    AUDIO_EXTENSIONS = {
        ".webm", ".ogg", ".mp3", ".wav", ".m4a", ".mp4",
    }

    DOCUMENT_EXTENSIONS = {
        ".pdf", ".txt", ".csv",
        ".doc", ".docx",
        ".xls", ".xlsx",
        ".ppt", ".pptx",
        ".odt", ".ods", ".odp",
        ".zip",
    }

    ALLOWED_EXTENSIONS = (
        IMAGE_EXTENSIONS
        | AUDIO_EXTENSIONS
        | DOCUMENT_EXTENSIONS
    )

    # ---------------------------------------------------------
    # UPDATE CURRENT USER PRESENCE
    # ---------------------------------------------------------
    UserPresence.objects.update_or_create(
        user=request.user,
        defaults={
            "is_online": True,
            "last_seen": timezone.now(),
        },
    )

    # ---------------------------------------------------------
    # GET CONVERSATIONS AVAILABLE TO THE CURRENT USER
    # ---------------------------------------------------------
    conversations = (
        Conversation.objects.filter(
            Q(customer=request.user)
            | Q(seller=request.user)
            | Q(business__owner=request.user)
            | Q(item__seller=request.user)
            | Q(food__seller=request.user)
        )
        .select_related(
            "business",
            "customer",
            "seller",
            "item",
            "food",
            "business__owner",
        )
        .prefetch_related("messages")
        .order_by("-updated_at")
    )

    selected_id = request.GET.get("conversation")
    selected_conversation = None

    if selected_id:
        selected_conversation = conversations.filter(
            id=selected_id
        ).first()

    is_ajax = (
        request.headers.get("X-Requested-With")
        == "XMLHttpRequest"
    )

    # ---------------------------------------------------------
    # HANDLE MESSAGE SUBMISSION
    # ---------------------------------------------------------
    if request.method == "POST":

        if not selected_conversation:
            if is_ajax:
                return JsonResponse(
                    {
                        "success": False,
                        "error": (
                            "This conversation could not be found. "
                            "Refresh the page and try again."
                        ),
                    },
                    status=404,
                )

            return redirect("/messages/")

        message_text = (
            request.POST.get("message")
            or request.POST.get("text")
            or ""
        ).strip()

        uploaded_file = request.FILES.get("attachment")

        # -----------------------------------------------------
        # REQUIRE TEXT OR AN ATTACHMENT
        # -----------------------------------------------------
        if not message_text and not uploaded_file:
            error = (
                "Enter a message or attach a file before sending."
            )

            if is_ajax:
                return JsonResponse(
                    {
                        "success": False,
                        "error": error,
                    },
                    status=400,
                )

            return redirect(
                f"/messages/?conversation={selected_conversation.id}"
            )

        # -----------------------------------------------------
        # VALIDATE UPLOAD
        # -----------------------------------------------------
        attachment_kind = ""
        attachment_content_type = ""
        original_filename = ""
        attachment_size = 0

        if uploaded_file:
            original_filename = os.path.basename(
                uploaded_file.name.replace("\\", "/")
            ).strip()

            extension = os.path.splitext(
                original_filename
            )[1].lower()

            if not original_filename or extension not in ALLOWED_EXTENSIONS:
                error = (
                    "This file type is not supported. "
                    "Choose an image, audio recording, "
                    "document, or ZIP file."
                )

                if is_ajax:
                    return JsonResponse(
                        {"success": False, "error": error},
                        status=400,
                    )

                return redirect(
                    f"/messages/?conversation={selected_conversation.id}"
                )

            if uploaded_file.size <= 0:
                error = "The selected file is empty."

                if is_ajax:
                    return JsonResponse(
                        {"success": False, "error": error},
                        status=400,
                    )

                return redirect(
                    f"/messages/?conversation={selected_conversation.id}"
                )

            if uploaded_file.size > MAX_ATTACHMENT_SIZE:
                error = "Attachments cannot exceed 50 MB."

                if is_ajax:
                    return JsonResponse(
                        {"success": False, "error": error},
                        status=413,
                    )

                return redirect(
                    f"/messages/?conversation={selected_conversation.id}"
                )

            # -------------------------------------------------
            # CLASSIFY THE ATTACHMENT
            # -------------------------------------------------
            if extension in IMAGE_EXTENSIONS:
                attachment_kind = "image"

                # Verify that the upload is actually an image.
                try:
                    uploaded_file.seek(0)

                    with Image.open(uploaded_file) as image:
                        image.verify()

                    uploaded_file.seek(0)

                except Exception:
                    error = (
                        "This image could not be verified. "
                        "Please choose a valid image file."
                    )

                    if is_ajax:
                        return JsonResponse(
                            {"success": False, "error": error},
                            status=400,
                        )

                    return redirect(
                        f"/messages/?conversation={selected_conversation.id}"
                    )

                # Determine the type from the decoded image,
                # rather than trusting the supplied MIME type.
                with Image.open(uploaded_file) as image:
                    detected_format = image.format

                image_types = {
                    "JPEG": "image/jpeg",
                    "PNG": "image/png",
                    "WEBP": "image/webp",
                    "GIF": "image/gif",
                }

                attachment_content_type = image_types.get(
                    detected_format,
                    "",
                )

                if not attachment_content_type:
                    error = "This image format is not supported."

                    if is_ajax:
                        return JsonResponse(
                            {"success": False, "error": error},
                            status=400,
                        )

                    return redirect(
                        f"/messages/?conversation={selected_conversation.id}"
                    )

                uploaded_file.seek(0)

            elif extension in AUDIO_EXTENSIONS:
                attachment_kind = "audio"

                audio_types = {
                    ".webm": "audio/webm",
                    ".ogg": "audio/ogg",
                    ".mp3": "audio/mpeg",
                    ".wav": "audio/wav",
                    ".m4a": "audio/mp4",
                    ".mp4": "audio/mp4",
                }

                attachment_content_type = audio_types[extension]

            else:
                attachment_kind = "file"

                attachment_content_type = (
                    mimetypes.guess_type(original_filename)[0]
                    or "application/octet-stream"
                )

            attachment_size = uploaded_file.size

        # -----------------------------------------------------
        # SAVE MESSAGE AND ATTACHMENT
        # -----------------------------------------------------
        try:
            with transaction.atomic():
                message = Message(
                    conversation=selected_conversation,
                    sender=request.user,
                    text=message_text,
                )

                if uploaded_file:
                    message.attachment = uploaded_file
                    message.attachment_original_name = (
                        original_filename[:255]
                    )
                    message.attachment_content_type = (
                        attachment_content_type[:100]
                    )
                    message.attachment_size = attachment_size
                    message.attachment_kind = attachment_kind

                message.full_clean()
                message.save()

                selected_conversation.updated_at = timezone.now()
                selected_conversation.save(
                    update_fields=["updated_at"]
                )

                message_data = {
                    "id": message.pk,
                    "message": message.text,
                    "text": message.text,
                    "sender_id": message.sender_id,
                    "sender": message.sender.username,
                    "time": message.created_at.strftime("%H:%M"),
                    "created_at": message.created_at.isoformat(),
                    "is_read": message.is_read,
                    **_businesshub_message_attachment_data(message),
                }

        except ValidationError as exc:
            logger.warning(
                "Message validation failed: %s",
                exc,
            )

            error = (
                "The message or attachment could not be validated."
            )

            if is_ajax:
                return JsonResponse(
                    {"success": False, "error": error},
                    status=400,
                )

            return redirect(
                f"/messages/?conversation={selected_conversation.id}"
            )

        except Exception:
            logger.exception(
                "Failed to save a message for conversation %s",
                selected_conversation.pk,
            )

            if is_ajax:
                return JsonResponse(
                    {
                        "success": False,
                        "error": (
                            "Your message could not be saved. "
                            "Please try again."
                        ),
                    },
                    status=500,
                )

            raise

        # -----------------------------------------------------
        # CREATE NOTIFICATION
        # -----------------------------------------------------
        notification_text = message_text

        if not notification_text and uploaded_file:
            if attachment_kind == "image":
                notification_text = "Sent an image"
            elif attachment_kind == "audio":
                notification_text = "Sent a voice message"
            else:
                notification_text = "Sent an attachment"

        try:
            create_message_notification(
                conversation=selected_conversation,
                sender=request.user,
                message_text=notification_text,
            )

        except Exception:
            logger.exception(
                "Failed to create a notification for message %s",
                message.pk,
            )

        # -----------------------------------------------------
        # RETURN SAVED MESSAGE TO AJAX
        # -----------------------------------------------------
        if is_ajax:
            return JsonResponse(
                {
                    "success": True,
                    "message": message_data,
                },
                status=200,
            )

        return redirect(
            f"/messages/?conversation={selected_conversation.id}"
        )

    # ---------------------------------------------------------
    # IDENTIFY THE OTHER PARTICIPANT
    # ---------------------------------------------------------
    other_user = None

    if selected_conversation:
        if (
            selected_conversation.item
            or selected_conversation.food
        ):
            if selected_conversation.customer_id == request.user.id:
                other_user = (
                    selected_conversation.seller
                    or (
                        selected_conversation.item.seller
                        if selected_conversation.item
                        else selected_conversation.food.seller
                    )
                )
            else:
                other_user = selected_conversation.customer

        elif selected_conversation.business:
            if selected_conversation.customer_id == request.user.id:
                other_user = selected_conversation.business.owner
            else:
                other_user = selected_conversation.customer

        else:
            if selected_conversation.customer_id == request.user.id:
                other_user = selected_conversation.seller
            else:
                other_user = selected_conversation.customer

    # ---------------------------------------------------------
    # MARK INCOMING MESSAGES AS READ
    # ---------------------------------------------------------
    if selected_conversation:
        selected_conversation.messages.filter(
            is_read=False
        ).exclude(
            sender=request.user
        ).update(
            is_read=True
        )

    # ---------------------------------------------------------
    # LOAD SELECTED CONVERSATION MESSAGES
    # ---------------------------------------------------------
    selected_messages = []

    if selected_conversation:
        selected_messages = list(
            selected_conversation.messages.select_related(
                "sender"
            ).order_by("created_at", "id")
        )

    # ---------------------------------------------------------
    # CALCULATE UNREAD COUNTS
    # ---------------------------------------------------------
    for conversation in conversations:
        conversation.unread_count = (
            conversation.messages.filter(
                is_read=False
            )
            .exclude(sender=request.user)
            .count()
        )

    # ---------------------------------------------------------
    # GET OTHER USER PRESENCE
    # ---------------------------------------------------------
    other_user_presence = None
    other_user_status = "Offline"

    if other_user:
        other_user_presence = UserPresence.objects.filter(
            user=other_user
        ).first()

    if other_user_presence and other_user_presence.last_seen:
        now = timezone.now()

        difference = (
            now - other_user_presence.last_seen
        ).total_seconds()

        if difference <= 60:
            other_user_status = "Online"

        else:
            minutes = int(difference // 60)

            if minutes < 60:
                other_user_status = (
                    f"Last seen {minutes} min ago"
                )
            else:
                hours = int(minutes // 60)

                if hours < 24:
                    other_user_status = (
                        f"Last seen {hours} hr ago"
                    )
                else:
                    days = int(hours // 24)

                    other_user_status = (
                        f"Last seen {days} "
                        f"day{'' if days == 1 else 's'} ago"
                    )

    # ---------------------------------------------------------
    # RENDER MESSAGES PAGE
    # ---------------------------------------------------------
    return render(
        request,
        "core/messages.html",
        {
            "conversations": conversations,
            "selected_conversation": selected_conversation,
            "selected_messages": selected_messages,
            "current_user_id": request.user.pk,
            "other_user": other_user,
            "other_user_presence": other_user_presence,
            "other_user_status": other_user_status,
        },
    )
@login_required
def conversation_detail(
    request,
    conversation_id
):

    conversation = get_object_or_404(
        Conversation.objects.select_related(
            "business",
            "customer",
            "seller",
            "item",
            "food",
            "business__owner"
        ),
        id=conversation_id
    )

    allowed = False

    if conversation.customer_id == request.user.id:

        allowed = True

    elif conversation.seller_id == request.user.id:

        allowed = True

    elif (
        conversation.business
        and
        conversation.business.owner_id
        ==
        request.user.id
    ):

        allowed = True

    if not allowed:

        return redirect(
            "messages_inbox"
        )

    if request.method == "POST":

        message_text = request.POST.get(
            "message",
            ""
        ).strip()

        if message_text:

            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                text=message_text
            )

            create_message_notification(
                conversation=conversation,
                sender=request.user,
                message_text=message_text
            )

            conversation.save()

        return redirect(
            "conversation_detail",
            conversation_id=conversation.id
        )

    conversation.messages.filter(
        is_read=False
    ).exclude(
        sender=request.user
    ).update(
        is_read=True
    )

    messages_list = list(
        conversation.messages.select_related(
            "sender"
        ).order_by(
            "created_at"
        )
    )

    for message in messages_list:

        if message.sender_id == request.user.pk:

            message.chat_side = "mine"

        else:

            message.chat_side = "theirs"

    other_user = None

    if conversation.item:

        if conversation.customer_id == request.user.id:

            other_user = conversation.seller

        else:

            other_user = conversation.customer

    elif conversation.food:

        if conversation.customer_id == request.user.id:

            other_user = conversation.seller

        else:

            other_user = conversation.customer

    elif conversation.business:

        if conversation.customer_id == request.user.id:

            other_user = conversation.business.owner

        else:

            other_user = conversation.customer

    other_user_presence = None

    if other_user:

        other_user_presence = (
            UserPresence.objects.filter(
                user=other_user
            ).first()
        )

    other_user_status = "Offline"

    if other_user_presence:

        if other_user_presence.last_seen:

            difference = (
                timezone.now()
                -
                other_user_presence.last_seen
            ).total_seconds()

            if difference <= 60:

                other_user_status = "Online"

            else:

                minutes = int(
                    difference // 60
                )

                if minutes < 60:

                    other_user_status = (
                        f"Last seen {minutes} min ago"
                    )

                else:

                    hours = int(
                        minutes // 60
                    )

                    if hours < 24:

                        other_user_status = (
                            f"Last seen {hours} hr ago"
                        )

                    else:

                        days = int(
                            hours // 24
                        )

                        other_user_status = (
                            f"Last seen {days} "
                            f"day"
                            f"{'' if days == 1 else 's'} ago"
                        )

    return render(
        request,
        "core/conversation-detail.html",
        {
            "conversation": conversation,
            "messages": messages_list,
            "current_user_id": request.user.pk,
            "other_user": other_user,
            "other_user_status": other_user_status,
        }
    )


@login_required
def conversation_messages_api(request, conversation_id):
    from django.db.models import Q
    from django.http import JsonResponse

    # ---------------------------------------------------------
    # FIND THE CONVERSATION
    # ---------------------------------------------------------
    conversation = get_object_or_404(
        Conversation.objects.select_related(
            "business",
            "customer",
            "seller",
            "item",
            "food",
        ),
        id=conversation_id,
    )

    # ---------------------------------------------------------
    # VERIFY CONVERSATION ACCESS
    # ---------------------------------------------------------
    allowed = (
        conversation.customer_id == request.user.id
        or conversation.seller_id == request.user.id
        or (
            conversation.business is not None
            and conversation.business.owner_id == request.user.id
        )
        or (
            conversation.item is not None
            and conversation.item.seller_id == request.user.id
        )
        or (
            conversation.food is not None
            and conversation.food.seller_id == request.user.id
        )
    )

    if not allowed:
        return JsonResponse(
            {"error": "Not allowed"},
            status=403,
        )

    # ---------------------------------------------------------
    # LOAD MESSAGES
    # ---------------------------------------------------------
    messages_list = (
        conversation.messages.select_related("sender")
        .order_by("created_at", "id")
    )

    data = []

    for message in messages_list:
        data.append(
            {
                "id": message.pk,
                "message": message.text,
                "text": message.text,
                "sender_id": message.sender_id,
                "sender": message.sender.username,
                "time": message.created_at.strftime("%H:%M"),
                "created_at": message.created_at.isoformat(),
                "is_read": message.is_read,
                **_businesshub_message_attachment_data(message),
            }
        )

    # ---------------------------------------------------------
    # MARK INCOMING MESSAGES AS READ
    # ---------------------------------------------------------
    conversation.messages.filter(
        is_read=False
    ).exclude(
        sender=request.user
    ).update(
        is_read=True
    )

    # ---------------------------------------------------------
    # RETURN MESSAGES
    # ---------------------------------------------------------
    return JsonResponse(
        {
            "success": True,
            "conversation_id": conversation.pk,
            "messages": data,
        },
        status=200,
    )
# =====================================================
# USER PRESENCE
# =====================================================

@login_required
def update_presence(request):

    if request.method != "POST":

        return JsonResponse(
            {
                "error": "POST request required"
            },
            status=405
        )

    UserPresence.objects.update_or_create(
        user=request.user,
        defaults={
            "is_online": True,
            "last_seen": timezone.now(),
        }
    )

    presence = UserPresence.objects.get(
        user=request.user
    )

    return JsonResponse({
        "online": True,
        "last_seen": presence.last_seen.isoformat()
    })


@login_required
def get_user_presence(
    request,
    user_id
):

    presence = UserPresence.objects.filter(
        user_id=user_id
    ).first()

    if not presence:

        return JsonResponse({
            "online": False,
            "last_seen": None
        })

    last_seen = presence.last_seen

    if not last_seen:

        return JsonResponse({
            "online": False,
            "last_seen": None
        })

    difference = (
        timezone.now()
        -
        last_seen
    ).total_seconds()

    online = (
        difference <= 60
    )

    return JsonResponse({
        "online": online,
        "last_seen": last_seen.isoformat()
    })
@login_required
def boost_food(request, food_id):
    from datetime import date

    food = get_object_or_404(Food, id=food_id)

    # Only the seller can boost the food listing.
    if food.seller != request.user:
        messages.error(
            request,
            "You can only boost your own food listings."
        )
        return redirect("food_detail", food_id=food.id)

    # Only available food listings can be boosted.
    if food.status != "available":
        messages.error(
            request,
            "Only available food listings can be boosted."
        )
        return redirect("food_detail", food_id=food.id)

    # Free-launch period: 12 October 2026 to 11 October 2027.
    today = timezone.localdate()
    free_launch = (
        date(2026, 10, 12)
        <= today
        < date(2027, 10, 12)
    )

    if not free_launch:
        return redirect(
            f"{reverse('payment_checkout')}?service=boost_100&food_id={food.id}"
        )

    now = timezone.now()
    duration = timedelta(days=3)

    existing_promotion = (
        ListingPromotion.objects.filter(
            user=request.user,
            food=food,
            service_type="boost",
            is_active=True,
            expiry_date__gt=now,
        )
        .order_by("-expiry_date")
        .first()
    )

    if existing_promotion:
        existing_promotion.expiry_date += duration
        existing_promotion.save(
            update_fields=["expiry_date", "updated_at"]
        )
        expiry_date = existing_promotion.expiry_date
        message_text = (
            f"Your food listing '{food.title}' has been boosted again. "
            f"Your promotion has been extended until "
            f"{expiry_date.strftime('%b %d, %Y at %I:%M %p')}."
        )
        success_message = (
            "Your food listing has been boosted for another 3 days."
        )
    else:
        promotion = ListingPromotion.objects.create(
            user=request.user,
            food=food,
            service_type="boost",
            payment=None,
            start_date=now,
            expiry_date=now + duration,
            is_active=True,
        )
        expiry_date = promotion.expiry_date
        message_text = (
            f"Your food listing '{food.title}' has been boosted successfully. "
            f"It is active until "
            f"{expiry_date.strftime('%b %d, %Y at %I:%M %p')}."
        )
        success_message = (
            "Your food listing has been boosted for 3 days for free!"
        )

    Notification.objects.create(
        user=request.user,
        notification_type="system",
        title="🚀 Boost Activated",
        message=message_text,
        link=reverse("food_detail", kwargs={"food_id": food.id}),
    )

    messages.success(request, success_message)
    return redirect("food_detail", food_id=food.id)


@login_required
def feature_food(request, food_id):
    from datetime import date

    food = get_object_or_404(Food, id=food_id)

    # Only the seller can feature the food listing.
    if food.seller != request.user:
        messages.error(
            request,
            "You can only feature your own food listings."
        )
        return redirect("food_detail", food_id=food.id)

    # Only available food listings can be featured.
    if food.status != "available":
        messages.error(
            request,
            "Only available food listings can be featured."
        )
        return redirect("food_detail", food_id=food.id)

    # Free-launch period: 12 October 2026 to 11 October 2027.
    today = timezone.localdate()
    free_launch = (
        date(2026, 10, 12)
        <= today
        < date(2027, 10, 12)
    )

    if not free_launch:
        return redirect(
            f"{reverse('payment_checkout')}?service=featured_1000&food_id={food.id}"
        )

    now = timezone.now()
    duration = timedelta(days=7)

    existing_promotion = (
        ListingPromotion.objects.filter(
            user=request.user,
            food=food,
            service_type="featured",
            is_active=True,
            expiry_date__gt=now,
        )
        .order_by("-expiry_date")
        .first()
    )

    if existing_promotion:
        existing_promotion.expiry_date += duration
        existing_promotion.save(
            update_fields=["expiry_date", "updated_at"]
        )
        expiry_date = existing_promotion.expiry_date
        message_text = (
            f"Your food listing '{food.title}' has been featured again. "
            f"Your promotion has been extended until "
            f"{expiry_date.strftime('%b %d, %Y at %I:%M %p')}."
        )
        success_message = (
            "Your food listing has been featured for another 7 days."
        )
    else:
        promotion = ListingPromotion.objects.create(
            user=request.user,
            food=food,
            service_type="featured",
            payment=None,
            start_date=now,
            expiry_date=now + duration,
            is_active=True,
        )
        expiry_date = promotion.expiry_date
        message_text = (
            f"Your food listing '{food.title}' has been featured successfully. "
            f"It is active until "
            f"{expiry_date.strftime('%b %d, %Y at %I:%M %p')}."
        )
        success_message = (
            "Your food listing is now featured for 7 days for free!"
        )

    Notification.objects.create(
        user=request.user,
        notification_type="system",
        title="⭐ Featured Activated",
        message=message_text,
        link=reverse("food_detail", kwargs={"food_id": food.id}),
    )

    messages.success(request, success_message)
    return redirect("food_detail", food_id=food.id)

@login_required
def message_attachment(request, message_id):
    """
    Serve message attachments only to authorized conversation participants.
    Images and audio files may be displayed inline.
    Other files are downloaded as attachments.
    """
    message = get_object_or_404(
        Message.objects.select_related(
            "conversation__business",
            "conversation__item",
            "conversation__food",
            "conversation__customer",
            "conversation__seller",
        ),
        pk=message_id,
    )

    conversation = message.conversation
    user = request.user

    # Authorize access to the conversation.
    is_authorized = (
        user.pk == conversation.customer_id
        or user.pk == conversation.seller_id
    )

    if conversation.business_id:
        is_authorized = is_authorized or (
            conversation.business.owner_id == user.pk
        )

    if conversation.item_id:
        is_authorized = is_authorized or (
            conversation.item.seller_id == user.pk
        )

    if conversation.food_id:
        is_authorized = is_authorized or (
            conversation.food.seller_id == user.pk
        )

    if not is_authorized:
        raise Http404("Attachment not found.")

    # Confirm that the message has an attachment.
    if not message.attachment:
        raise Http404("Attachment not found.")

    try:
        attachment_file = message.attachment.open("rb")
    except (FileNotFoundError, OSError, ValueError):
        raise Http404("Attachment not found.")

    # Only trusted image and audio types may be displayed inline.
    allowed_inline_types = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "audio/webm",
        "audio/ogg",
        "audio/mpeg",
        "audio/wav",
        "audio/mp4",
    }

    stored_content_type = (
        message.attachment_content_type or ""
    ).split(";")[0].strip().lower()

    if stored_content_type in allowed_inline_types:
        content_type = stored_content_type
        as_attachment = False
    else:
        content_type = "application/octet-stream"
        as_attachment = True

    # Sanitize the filename.
    original_name = (
        message.attachment_original_name or "attachment"
    )

    original_name = (
        original_name.replace("\\", "/").split("/")[-1]
    )

    try:
        safe_filename = get_valid_filename(original_name)
    except (TypeError, ValueError):
        safe_filename = "attachment"

    if not safe_filename or safe_filename in {".", ".."}:
        safe_filename = "attachment"

    # Stream the attachment to the authorized user.
    try:
        response = FileResponse(
            attachment_file,
            content_type=content_type,
            as_attachment=as_attachment,
            filename=safe_filename,
        )
    except (OSError, ValueError):
        attachment_file.close()
        raise Http404("Attachment not found.")

    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"

    if message.attachment_size:
        response["Content-Length"] = str(
            message.attachment_size
        )

    return response
