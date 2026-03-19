from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from marketplace.models import Booking, Notification
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Process bookings that have ended and mark them as completed.'

    def handle(self, *args, **options):
        now = timezone.now()
        # Any confirmed booking with check_out_date < now - 24 hours should be completed
        # check_out_date is a DateField, so we compare with date
        threshold_date = (now - timedelta(days=1)).date()
        
        bookings_to_complete = Booking.objects.filter(
            booking_status='Confirmed',
            check_out_date__lte=threshold_date
        )

        completed_count = 0
        for booking in bookings_to_complete:
            booking.booking_status = 'Completed'
            booking.save()
            completed_count += 1
            
            # Create a notification for the traveler
            Notification.objects.create(
                user=booking.user,
                title="Review your Experience",
                message=f"Your trip to {booking.experience.title} is complete! Please leave a review.",
                link=f"/booking/{booking.id}/review/"
            )
            
            # Send review email
            try:
                from marketplace.services.emails import send_review_request_email
                send_review_request_email(booking)
            except Exception as e:
                logger.error(f"Failed to send review request email for booking {booking.id}: {e}")

        self.stdout.write(self.style.SUCCESS(f'Successfully processed {completed_count} bookings.'))
