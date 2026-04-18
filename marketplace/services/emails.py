import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

logger = logging.getLogger(__name__)

def _send_html_email_safe(subject, template_name, context, recipient_list):
    """
    Helper function to send HTML emails safely.
    It renders the HTML template, generates a plaintext alternative,
    and uses 'fail_silently=True'.
    """
    try:
        # Add a default site_url to context for links in emails
        if 'site_url' not in context:
            context['site_url'] = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8080')
            
        html_content = render_to_string(template_name, context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@routeless.com'),
            to=recipient_list,
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=True)
        
    except Exception as e:
        logger.error(f"Failed to send HTML email {template_name} to {recipient_list}: {e}")

def send_booking_created_email(booking):
    """
    Sent to the traveler immediately when a booking request is created.
    """
    subject = f"Booking Request Received - {booking.experience.title}"
    context = {
        'traveler_name': booking.traveler_name,
        'experience': booking.experience,
        'booking': booking,
    }
    _send_html_email_safe(subject, 'emails/booking_confirmation.html', context, [booking.traveler_email])

def send_payment_success_email(booking):
    """
    Sent to the traveler when payment is successful and booking is confirmed.
    """
    subject = f"Booking Confirmed! - {booking.experience.title}"
    context = {
        'traveler_name': booking.traveler_name,
        'experience': booking.experience,
        'booking': booking,
    }
    _send_html_email_safe(subject, 'emails/payment_success.html', context, [booking.traveler_email])

def send_host_new_booking_email(booking):
    """
    Sent to the host when a new booking is confirmed.
    """
    host = booking.experience.host
    if not host or not host.email:
        return
        
    subject = f"New Booking Confirmed - {booking.experience.title}"
    context = {
        'host': host,
        'experience': booking.experience,
        'booking': booking,
    }
    _send_html_email_safe(subject, 'emails/host_new_booking.html', context, [host.email])

def send_booking_status_update_email(booking):
    """
    Sent to the traveler when the host manually changes the booking status 
    (e.g., Completed, Cancelled). Fallback using old templates if needed,
    but here we can just dispatch a generic text update for now if HTML isn't built yet.
    """
    subject = f"Update on your booking for {booking.experience.title}"
    message = f"""Hi {booking.traveler_name},

The status of your booking for {booking.experience.title} has been updated.

New Status: {booking.booking_status}

Thank you,
The THEROUTELESS Team
"""
    try:
        from django.core.mail import send_mail
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@routeless.com'),
            recipient_list=[booking.traveler_email],
            fail_silently=True, 
        )
    except Exception as e:
        logger.error(f"Failed to send status update email to {booking.traveler_email}: {e}")

def send_payment_failed_email(booking):
    """
    New function to trigger the payment failure template if a retry loop causes issues.
    """
    subject = f"Payment Action Required - {booking.experience.title}"
    context = {
        'traveler_name': booking.traveler_name,
        'experience': booking.experience,
        'booking': booking,
    }
    _send_html_email_safe(subject, 'emails/payment_failed.html', context, [booking.traveler_email])

def send_otp_email(user, otp_code):
    """
    Send OTP code for email login. 
    Using text fallback directly if we don't have an html template yet.
    """
    try:
        from django.core.mail import send_mail
        subject = "Your THEROUTELESS Login OTP"
        message = f"Hello {user.username},\n\nYour login code is: {otp_code}\n\nThis code will expire in 5 minutes.\nIf you did not request this, please ignore."
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@routeless.com'),
            recipient_list=[user.email],
            fail_silently=True, 
        )
    except Exception as e:
        logger.error(f"Failed to send OTP email to {user.email}: {e}")

def send_review_request_email(booking):
    """
    Sent to the traveler after their booking is completed, asking for a review.
    """
    subject = f"How was your trip? - {booking.experience.title}"
    context = {
        'traveler_name': booking.traveler_name,
        'experience': booking.experience,
        'booking': booking,
    }
    _send_html_email_safe(subject, 'emails/review_request.html', context, [booking.traveler_email])

def send_new_message_email(message, recipient):
    """
    Sent to the recipient of a new message.
    """
    subject = f"New Message - {message.conversation.experience.title}"
    context = {
        'recipient_name': recipient.username,
        'sender_name': message.sender.username,
        'experience': message.conversation.experience,
        'message_text': message.text,
    }
    _send_html_email_safe(subject, 'emails/new_message.html', context, [recipient.email])

def send_new_review_email(review):
    """
    Sent to the host when a new review is posted for their experience.
    """
    if not review.host or not review.host.email:
        return
        
    subject = f"New Review for {review.experience.title}"
    context = {
        'host_name': review.host.username,
        'reviewer_name': review.reviewer.username,
        'experience': review.experience,
        'rating': review.rating,
        'comment': review.comment,
    }
    _send_html_email_safe(subject, 'emails/new_review.html', context, [review.host.email])
