from django.urls import path
from . import views
from . import webhook

app_name = 'payments'

urlpatterns = [
    path('checkout-verify/', views.checkout_verify, name='checkout_verify'),
    path('webhook/', webhook.razorpay_webhook_view, name='webhook'),
    path('failed/<int:pk>/', views.payment_failed, name='payment_failed'),
    path('retry/<int:booking_id>/', views.retry_payment, name='retry_payment'),
]
