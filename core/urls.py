from django.urls import path
from . import views

urlpatterns = [
# ============================================================
# BUSINESS
# ============================================================


path("list-business/", views.list_business, name="list_business"),
path("business-success/", views.business_success, name="business_success"),
path("businesses/", views.business_list, name="business_list"),
path("owner-dashboard/", views.owner_dashboard, name="owner_dashboard"),

path(
    "view-business/<int:business_id>/",
    views.view_business,
    name="view_business",
),
path(
    "view-business/<int:business_id>/review/",
    views.submit_business_review,
    name="submit_business_review",
),
path(
    "view-business/<int:business_id>/review/edit/",
    views.edit_business_review,
    name="edit_business_review",
),
path(
    "view-business/<int:business_id>/review/delete/",
    views.delete_business_review,
    name="delete_business_review",
),
path(
    "business/<int:business_id>/review/edit/",
    views.edit_business_review,
    name="edit_business_review",
),
path(
    "business/<int:business_id>/review/delete/",
    views.delete_business_review,
    name="delete_business_review",
),
path(
    "edit-business/<int:business_id>/",
    views.edit_business,
    name="edit_business",
),
path(
    "delete-business/<int:business_id>/",
    views.delete_business,
    name="delete_business",
),

# ============================================================
# AUTHENTICATION
# ============================================================

path("login/", views.user_login, name="login"),
path("register/", views.register, name="register"),
path("logout/", views.user_logout, name="logout"),

# ============================================================
# ACCOUNT
# ============================================================

path("account/", views.account, name="account"),
path("account/edit/", views.edit_account, name="edit_account"),
path(
    "account/password/",
    views.change_password,
    name="change_password",
),

# ============================================================
# NOTIFICATIONS
# ============================================================

path("notifications/", views.notifications, name="notifications"),
path(
    "notifications/<int:notification_id>/",
    views.notification_detail,
    name="notification_detail",
),
path(
    "notifications/mark-all-read/",
    views.mark_all_notifications_read,
    name="mark_all_notifications_read",
),
path(
    "notifications/unread-count/",
    views.unread_notifications_count,
    name="unread_notifications_count",
),
path(
    "notifications/latest-unread/",
    views.latest_unread_notification,
    name="latest_unread_notification",
),

# ============================================================
# MAIN
# ============================================================

path("", views.home, name="home"),
path("categories/", views.categories, name="categories"),
path("tracking/", views.tracking, name="tracking"),

# ============================================================
# ITEMS
# ============================================================

path("items/", views.items_marketplace, name="items_marketplace"),
path("items/sell/", views.sell_item, name="sell_item"),
path("items/my-items/", views.my_items, name="my_items"),
path(
    "items/<int:item_id>/message/",
    views.message_item_seller,
    name="message_item_seller",
),
path(
    "items/<int:item_id>/boost/",
    views.boost_item,
    name="boost_item",
),
path(
    "items/<int:item_id>/feature/",
    views.feature_item,
    name="feature_item",
),
path("items/<int:item_id>/", views.item_detail, name="item_detail"),
path(
    "items/<int:item_id>/edit/",
    views.edit_item,
    name="edit_item",
),
path(
    "items/image/<int:image_id>/delete/",
    views.delete_item_image,
    name="delete_item_image",
),
path(
    "items/<int:item_id>/delete/",
    views.delete_item,
    name="delete_item",
),
path(
    "items/<int:item_id>/sold/",
    views.mark_item_sold,
    name="mark_item_sold",
),

# ============================================================
# FOOD
# ============================================================

path("food/", views.food_marketplace, name="food_marketplace"),
path("food/sell/", views.sell_food, name="sell_food"),
path("food/my-food/", views.my_food, name="my_food"),
path(
    "food/<int:food_id>/boost/",
    views.boost_food,
    name="boost_food",
),
path(
    "food/<int:food_id>/feature/",
    views.feature_food,
    name="feature_food",
),
path("food/<int:food_id>/", views.food_detail, name="food_detail"),
path(
    "food/<int:food_id>/edit/",
    views.edit_food,
    name="edit_food",
),
path(
    "food/image/<int:image_id>/delete/",
    views.delete_food_image,
    name="delete_food_image",
),
path(
    "food/<int:food_id>/delete/",
    views.delete_food,
    name="delete_food",
),
path(
    "food/<int:food_id>/unavailable/",
    views.mark_food_unavailable,
    name="mark_food_unavailable",
),
path(
    "food/<int:food_id>/message/",
    views.message_food_seller,
    name="message_food_seller",
),
# ============================================================
# SELLER SHIPMENT MANAGEMENT
# ============================================================

path(
    "my-shipments/",
    views.my_shipments,
    name="my_shipments",
),
path(
    "shipments/create/",
    views.create_shipment,
    name="create_shipment",
),
path(
    "shipments/<int:package_id>/update/",
    views.update_shipment,
    name="update_shipment",
),
path(
    "shipments/<int:package_id>/delete/",
    views.delete_shipment,
    name="delete_shipment",
),
# ============================================================
# TRACKING APIs
# ============================================================

path(
    "api/package-location/<str:tracking_number>/",
    views.package_location_api,
    name="package_location_api",
),
path(
    "api/save-package-location/<str:tracking_number>/",
    views.save_package_location_api,
    name="save_package_location_api",
),

# ============================================================
# MESSAGING
# ============================================================

path(
    "message-business/<int:business_id>/",
    views.message_business,
    name="message_business",
),
path("messages/", views.messages_inbox, name="messages_inbox"),
path(
    "conversation/<int:conversation_id>/",
    views.conversation_detail,
    name="conversation_detail",
),
path(
    "api/conversation/<int:conversation_id>/messages/",
    views.conversation_messages_api,
    name="conversation_messages_api",
),
path(
    "message-attachment/<int:message_id>/",
    views.message_attachment,
    name="message_attachment",
),

# ============================================================
# PRESENCE
# ============================================================

path(
    "api/update-presence/",
    views.update_presence,
    name="update_presence",
),
path(
    "user-presence/<int:user_id>/",
    views.get_user_presence,
    name="get_user_presence",
),

# ============================================================
# BUSINESSHUB SERVICES / PAYMENTS
# ============================================================

path(
    "services/",
    views.businesshub_services,
    name="businesshub_services",
),
path(
    "payments/checkout/",
    views.payment_checkout,
    name="payment_checkout",
),
path(
    "payments/<str:reference>/check/",
    views.check_payment_status,
    name="check_payment_status",
),
path(
    "payments/<str:reference>/",
    views.payment_status,
    name="payment_status",
),
path(
    "analytics/",
    views.business_analytics,
    name="business_analytics",
),


]
