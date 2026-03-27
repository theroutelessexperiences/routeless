from django.urls import path
from . import views

urlpatterns = [
    path("health/", health_check, name="health_check"),
    path('', views.home, name='home'),
    path('experiences/', views.listing_list, name='listing_list'),
    path('experiences/<slug:slug>/', views.listing_detail, name='listing_detail'),
    path('booking-success/', views.booking_success, name='booking_success'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('login/otp/', views.otp_login_view, name='otp_login'),
    path('login/otp/verify/', views.otp_verify_view, name='otp_verify'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_router, name='dashboard_router'),
    path('profile/', views.profile_view, name='profile'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('dashboard/host/', views.host_dashboard, name='host_dashboard'),
    path('locations/', views.location_list, name='locations'),
    path('destinations/<slug:location_slug>/', views.destination_view, name='destination_view'),
    path('platform-analytics/', views.platform_analytics, name='platform_analytics'),

    # Keep ONLY this one for categories
    path('categories/', views.categories_view, name='categories'),

    path('checkout/<int:pk>/', views.checkout, name='checkout'),
    path('booking/<int:pk>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('booking/<int:pk>/review/', views.leave_review, name='leave_review'),
    path('messages/', views.inbox_view, name='inbox'),
    path('messages/<int:pk>/', views.conversation_detail_view, name='conversation_detail'),
    path('messages/start/<int:experience_id>/', views.start_conversation, name='start_conversation'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('dashboard/host/add-experience/', views.add_experience_view, name='add_experience'),
    path('dashboard/host/calendar/add/', views.add_availability_slots, name='add_availability_slots'),
    path('dashboard/host/calendar/toggle/<int:slot_id>/', views.toggle_slot_availability, name='toggle_slot_availability'),
    path('dashboard/host/pricing/add/', views.add_pricing_rule, name='add_pricing_rule'),
    path('become-host/', views.become_host, name='become_host'),
    path('api/experiences/<int:experience_id>/slots/', views.api_experience_slots, name='api_experience_slots'),
    path('api/experiences/<int:experience_id>/price/', views.api_experience_price, name='api_experience_price'),
    path('api/notifications/unread/', views.api_unread_notifications_count, name='api_unread_notifications_count'),
]
