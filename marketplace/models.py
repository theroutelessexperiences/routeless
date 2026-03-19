from django.apps import apps
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify
import os


# -------------------------------------------------------------------
# Validators & helpers
# -------------------------------------------------------------------
def validate_image_file(value):
    ext = os.path.splitext(value.name)[1]
    valid_extensions = [".jpg", ".jpeg", ".png"]
    if ext.lower() not in valid_extensions:
        raise ValidationError("Unsupported file extension. Allowed are: .jpg, .jpeg, .png.")
    limit = 5 * 1024 * 1024
    if value.size > limit:
        raise ValidationError("File size cannot exceed 5MB.")


def generate_unique_slug(instance, source_text, model_class, slug_field="slug"):
    """
    Generate a unique slug for a model.
    """
    base_slug = slugify(source_text) or "item"
    slug = base_slug
    counter = 1

    while model_class.objects.filter(**{slug_field: slug}).exclude(pk=instance.pk).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def normalize_booking_status(value: str) -> str:
    if not value:
        return "pending"

    raw = str(value).strip().lower().replace("-", "_")
    mapping = {
        "pending": "pending",
        "payment created": "payment_processing",
        "payment_created": "payment_processing",
        "payment processing": "payment_processing",
        "payment_processing": "payment_processing",
        "confirmed": "confirmed",
        "completed": "completed",
        "cancelled": "cancelled",
        "canceled": "cancelled",
        "refunded": "refunded",
    }
    return mapping.get(raw, raw)


def map_payment_status_to_legacy_display(raw_status: str) -> str:
    """
    Maps payment model statuses to the legacy display values used in older views.
    """
    raw = (raw_status or "").strip().lower()
    mapping = {
        "pending": "Created",
        "created": "Created",
        "success": "Paid",
        "captured": "Paid",
        "paid": "Paid",
        "failed": "Failed",
        "refunded": "Refunded",
    }
    return mapping.get(raw, raw_status or "Created")


def map_legacy_payment_to_internal(value: str) -> str:
    raw = (value or "").strip().lower()
    mapping = {
        "created": "pending",
        "pending": "pending",
        "paid": "success",
        "success": "success",
        "captured": "success",
        "failed": "failed",
        "refunded": "refunded",
    }
    return mapping.get(raw, raw)


# -------------------------------------------------------------------
# Static choices
# -------------------------------------------------------------------
CATEGORY_CHOICES = (
    ("Adventure", "Adventure"),
    ("Spiritual", "Spiritual"),
    ("Homestay", "Homestay"),
    ("Trek", "Trek"),
    ("Wildlife", "Wildlife"),
    ("Cultural", "Cultural"),
)


# -------------------------------------------------------------------
# User & Profile
# -------------------------------------------------------------------
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_host = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=20, blank=True)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, validators=[validate_image_file])
    bio = models.TextField(blank=True)
    is_flagged = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False)
    moderation_reason = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    @property
    def average_rating(self):
        avg = self.user.host_reviews.aggregate(Avg("rating"))["rating__avg"]
        return round(avg, 1) if avg else 0.0

    @property
    def total_reviews(self):
        return self.user.host_reviews.count()

    @property
    def avatar(self):
        """
        Compatibility alias used by some templates.
        """
        return self.profile_picture


class EmailOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)

    def __str__(self):
        return f"OTP for {self.user.username} - Verified: {self.verified}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    UserProfile.objects.get_or_create(user=instance)


# -------------------------------------------------------------------
# Locations & Experiences
# -------------------------------------------------------------------
class Location(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    state = models.CharField(max_length=100)
    image = models.ImageField(upload_to="locations/", blank=True, null=True, validators=[validate_image_file])

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.name, Location)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}, {self.state}"


class Experience(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True, db_index=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)

    # Legacy text field
    location = models.CharField(max_length=200, db_index=True)

    # New normalized location FK
    location_fk = models.ForeignKey(
        "Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="experiences",
    )

    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name="experiences", null=True)

    short_description = models.CharField(max_length=255, blank=True)
    description = models.TextField()

    price_per_person = models.DecimalField(max_digits=10, decimal_places=2)
    max_guests = models.IntegerField()
    duration = models.CharField(max_length=100)

    amenities = models.JSONField(default=list, blank=True)

    is_flagged = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False)
    moderation_reason = models.TextField(blank=True)

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.title, Experience)

        if self.location_fk:
            self.location = self.location_fk.name

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def ranking_score(self):
        """
        Dynamic ranking score.
        """
        aggs = self.reviews.aggregate(avg_rating=Avg("rating"))
        rating = float(aggs["avg_rating"] or 0.0)
        review_count = self.reviews.count()
        booking_count = self.bookings.filter(
            booking_status__in=["confirmed", "completed"]
        ).count()
        host_bonus = 1.0 if self.host and self.host.is_active else 0.0

        score = (
            (rating * 0.4)
            + ((min(review_count, 100) / 100) * 2.0)
            + ((min(booking_count, 100) / 100) * 3.0)
            + (host_bonus * 1.0)
        )
        return round(score, 2)

    @property
    def main_image(self):
        primary = self.images.filter(is_primary=True).first()
        if primary:
            return primary.image
        first = self.images.first()
        if first:
            return first.image
        return None

    @property
    def display_location(self):
        if self.location_fk:
            return self.location_fk.name
        return self.location

    @property
    def average_rating(self):
        avg = self.reviews.aggregate(Avg("rating"))["rating__avg"]
        return round(avg, 1) if avg else 0.0

    @property
    def total_reviews(self):
        return self.reviews.count()


class ExperienceImage(models.Model):
    experience = models.ForeignKey(Experience, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="experiences/", validators=[validate_image_file])
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.experience.title}"


class AvailabilitySlot(models.Model):
    experience = models.ForeignKey(Experience, on_delete=models.CASCADE, related_name="availability_slots")
    date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    capacity = models.IntegerField()
    booked_count = models.IntegerField(default=0)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "start_time"]
        unique_together = ("experience", "date", "start_time")

    def __str__(self):
        time_str = self.start_time.strftime("%H:%M") if self.start_time else "All Day"
        return f"{self.experience.title} - {self.date} at {time_str}"


class ExperienceAvailabilityBlock(models.Model):
    experience = models.ForeignKey(Experience, on_delete=models.CASCADE, related_name="blocked_dates")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gt=models.F("start_date")),
                name="block_end_gt_start",
            ),
        ]
        ordering = ["start_date"]

    def clean(self):
        if self.start_date and self.end_date:
            if self.end_date <= self.start_date:
                raise ValidationError("End date must be strictly after start date.")

            overlapping = ExperienceAvailabilityBlock.objects.filter(
                experience=self.experience,
                start_date__lt=self.end_date,
                end_date__gt=self.start_date,
            )
            if self.pk:
                overlapping = overlapping.exclude(pk=self.pk)

            if overlapping.exists():
                raise ValidationError("This block overlaps with an existing availability block.")

    def __str__(self):
        return f"Block for {self.experience.title} ({self.start_date} to {self.end_date})"


# -------------------------------------------------------------------
# Booking & Reviews
# -------------------------------------------------------------------
class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAYMENT_PROCESSING = "payment_processing", "Payment Processing"
        CONFIRMED = "confirmed", "Confirmed"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    experience = models.ForeignKey(Experience, on_delete=models.CASCADE, related_name="bookings")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_bookings", null=True)
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name="hosted_bookings", null=True)

    traveler_name = models.CharField(max_length=100)
    traveler_email = models.EmailField()
    traveler_phone = models.CharField(max_length=20)

    check_in_date = models.DateField()
    check_out_date = models.DateField()
    guests_count = models.IntegerField()

    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    booking_status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    host_payout = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(check_out_date__gt=models.F("check_in_date")),
                name="check_out_gt_check_in",
            ),
        ]

    def save(self, *args, **kwargs):
        self.booking_status = normalize_booking_status(self.booking_status)
        if not self.host and self.experience_id and self.experience and self.experience.host:
            self.host = self.experience.host
        super().save(*args, **kwargs)

    def clean(self):
        if self.check_in_date and self.check_out_date:
            if self.check_out_date <= self.check_in_date:
                raise ValidationError("Check out date must be after check in date.")

            if self.experience_id:
                overlapping_bookings = Booking.objects.filter(
                    experience=self.experience,
                    check_in_date__lt=self.check_out_date,
                    check_out_date__gt=self.check_in_date,
                ).exclude(
                    booking_status__in=["cancelled", "refunded", "Cancelled", "Refunded"]
                )

                if self.pk:
                    overlapping_bookings = overlapping_bookings.exclude(pk=self.pk)

                if overlapping_bookings.exists():
                    raise ValidationError("These dates overlap with an existing booking.")

                overlapping_blocks = ExperienceAvailabilityBlock.objects.filter(
                    experience=self.experience,
                    start_date__lt=self.check_out_date,
                    end_date__gt=self.check_in_date,
                )
                if overlapping_blocks.exists():
                    raise ValidationError("These dates are unavailable as they have been blocked by the host.")

        if self.guests_count and self.experience_id:
            if self.guests_count > self.experience.max_guests:
                raise ValidationError(
                    f"Guests cannot exceed the maximum allowed ({self.experience.max_guests})."
                )

            if self.check_in_date:
                slot = AvailabilitySlot.objects.filter(
                    experience=self.experience,
                    date=self.check_in_date,
                    is_available=True,
                ).first()

                if slot:
                    available_capacity = slot.capacity - slot.booked_count
                    if self.guests_count > available_capacity:
                        raise ValidationError(
                            f"Only {available_capacity} seats remaining for {self.check_in_date}."
                        )

    @property
    def status(self):
        """
        Legacy compatibility alias for old code using booking.status
        """
        return self.booking_status

    @status.setter
    def status(self, value):
        self.booking_status = normalize_booking_status(value)

    @property
    def payment_status(self):
        """
        Legacy compatibility bridge for old code using booking.payment_status.
        Pulls from the related Payment model if present.
        """
        try:
            payment = self.payment
        except Exception:
            return "Created"
        return map_payment_status_to_legacy_display(getattr(payment, "payment_status", "pending"))

    @payment_status.setter
    def payment_status(self, value):
        try:
            payment = self.payment
        except Exception:
            return

        payment.payment_status = map_legacy_payment_to_internal(value)
        payment.save(update_fields=["payment_status"])

    @property
    def total_estimated_price(self):
        return self.total_price

    def __str__(self):
        return f"Booking for {self.experience.title} by {self.traveler_name}"


class Review(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="review")
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE)
    host = models.ForeignKey(User, related_name="host_reviews", on_delete=models.CASCADE)
    experience = models.ForeignKey(Experience, on_delete=models.CASCADE, related_name="reviews")
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    is_flagged = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False)
    moderation_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if not (1 <= self.rating <= 5):
            raise ValidationError("Rating must be between 1 and 5.")
        if self.booking_id and self.booking.booking_status != Booking.Status.COMPLETED:
            raise ValidationError("Review can only be left for completed bookings.")

    def __str__(self):
        return f"Review for {self.experience.title} by {self.reviewer.username}"


class ReviewReport(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE)
    reporter = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report on Review {self.review.id} by {self.reporter.username}"


# -------------------------------------------------------------------
# Messaging & Notifications
# -------------------------------------------------------------------
class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    host = models.ForeignKey(User, related_name="host_conversations", on_delete=models.CASCADE)
    experience = models.ForeignKey(Experience, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "host", "experience"],
                name="unique_conversation_per_user_host_experience",
            )
        ]

    def __str__(self):
        return f"Conversation: {self.user.username} & {self.host.username} - {self.experience.title}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    read = models.BooleanField(default=False)
    is_flagged = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False)
    moderation_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Message from {self.sender.username} in Conversation {self.conversation.id}"


class Notification(models.Model):
    user = models.ForeignKey(User, related_name="notifications", on_delete=models.CASCADE)
    title = models.CharField(max_length=200, default="Notification")
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} -> {self.user.username}"


# -------------------------------------------------------------------
# Host verification & requests
# -------------------------------------------------------------------
class HostRequest(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="host_request")
    phone_number = models.CharField(max_length=20)
    bio = models.TextField()
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Host Request from {self.user.username}"


class HostVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    government_id = models.ImageField(
        upload_to="host_ids/",
        validators=[validate_image_file],
        blank=True,
        null=True,
    )
    selfie = models.ImageField(
        upload_to="host_selfie/",
        validators=[validate_image_file],
        blank=True,
        null=True,
    )
    verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} Identity Verification - {'Verified' if self.verified else 'Pending'}"


# -------------------------------------------------------------------
# Hero slides
# -------------------------------------------------------------------
class HeroSlide(models.Model):
    MEDIA_IMAGE = "image"
    MEDIA_VIDEO = "video"
    MEDIA_CHOICES = [
        (MEDIA_IMAGE, "Image"),
        (MEDIA_VIDEO, "Video"),
    ]

    title = models.CharField(max_length=180)
    subtitle = models.TextField(blank=True)

    badge_text = models.CharField(
        max_length=120,
        blank=True,
        help_text="e.g., Curated Mountain Experiences",
    )
    badge_icon = models.CharField(
        max_length=60,
        blank=True,
        help_text="Bootstrap icon class, e.g. bi bi-stars or bi bi-camera-video",
    )

    media_type = models.CharField(
        max_length=10,
        choices=MEDIA_CHOICES,
        default=MEDIA_IMAGE,
    )

    image = models.ImageField(
        upload_to="hero_slides/images/",
        blank=True,
        null=True,
        help_text="Required for image slides.",
    )

    video = models.FileField(
        upload_to="hero_slides/videos/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=["mp4", "webm", "ogg"])],
        help_text="Required for video slides.",
    )

    video_poster = models.ImageField(
        upload_to="hero_slides/posters/",
        blank=True,
        null=True,
        help_text="Recommended poster image for video slide.",
    )

    cta_primary_label = models.CharField(max_length=60, blank=True)
    cta_primary_url = models.CharField(
        max_length=255,
        blank=True,
        help_text="Use absolute or relative URL, e.g. /listings/ or /listings/?category=Adventure",
    )

    cta_secondary_label = models.CharField(max_length=60, blank=True)
    cta_secondary_url = models.CharField(
        max_length=255,
        blank=True,
        help_text="Use absolute or relative URL",
    )

    interval_ms = models.PositiveIntegerField(
        default=5000,
        help_text="Per-slide interval in milliseconds",
    )
    overlay_opacity_top = models.DecimalField(max_digits=3, decimal_places=2, default=0.55)
    overlay_opacity_bottom = models.DecimalField(max_digits=3, decimal_places=2, default=0.82)

    show_search_card = models.BooleanField(
        default=False,
        help_text="Enable the large search card on this slide (usually only first slide).",
    )
    show_trust_chips = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Hero Slide"
        verbose_name_plural = "Hero Slides"

    def __str__(self):
        return f"{self.sort_order}. {self.title}"

    @property
    def video_mime_type(self):
        if not self.video:
            return "video/mp4"
        name = self.video.name.lower()
        if name.endswith(".webm"):
            return "video/webm"
        if name.endswith(".ogg"):
            return "video/ogg"
        return "video/mp4"

    def clean(self):
        super().clean()

        if self.media_type == self.MEDIA_IMAGE and not self.image:
            raise ValidationError({"image": "Image is required when media type is Image."})

        if self.media_type == self.MEDIA_VIDEO and not self.video:
            raise ValidationError({"video": "Video is required when media type is Video."})

        if self.cta_primary_label and not self.cta_primary_url:
            raise ValidationError({"cta_primary_url": "Primary CTA URL is required if label is provided."})

        if self.cta_secondary_label and not self.cta_secondary_url:
            raise ValidationError({"cta_secondary_url": "Secondary CTA URL is required if label is provided."})

        if self.show_search_card:
            qs = HeroSlide.objects.filter(show_search_card=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({
                    "show_search_card": "Only one slide should have the search card enabled."
                })


# -------------------------------------------------------------------
# Platform Intelligence & Activity Models
# -------------------------------------------------------------------
class UserEvent(models.Model):
    EVENT_CHOICES = (
        ("VIEW", "Viewed Experience"),
        ("SEARCH", "Searched Destination"),
        ("BOOK", "Booked Experience"),
        ("MESSAGE", "Messaged Host"),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="events", null=True, blank=True)
    session_key = models.CharField(max_length=100, blank=True, null=True)
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES)
    experience = models.ForeignKey(Experience, on_delete=models.SET_NULL, null=True, blank=True)
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        actor = self.user.username if self.user else "Anonymous"
        return f"{self.event_type} by {actor}"


class UserPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="preference")
    preferred_categories = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferences for {self.user.username}"


class ActivityFeed(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    experience = models.ForeignKey(Experience, on_delete=models.CASCADE)
    action_text = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.action_text


# -------------------------------------------------------------------
# Dynamic Pricing Models
# -------------------------------------------------------------------
class DynamicPricingRule(models.Model):
    RULE_TYPES = (
        ("WEEKEND", "Weekend Premium"),
        ("HOLIDAY", "Holiday Premium"),
        ("SURGE", "High Demand Surge"),
        ("DISCOUNT", "Low Demand Discount"),
    )
    experience = models.ForeignKey(Experience, on_delete=models.CASCADE, related_name="pricing_rules")
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)
    multiplier = models.DecimalField(max_digits=4, decimal_places=2, help_text="e.g., 1.25 for a 25% increase")
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.rule_type} ({self.multiplier}x) for {self.experience.title}"


class DemandSignal(models.Model):
    experience = models.ForeignKey(Experience, on_delete=models.CASCADE, related_name="demand_signals")
    date = models.DateField(auto_now_add=True)
    search_count = models.PositiveIntegerField(default=0)
    booking_attempts = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("experience", "date")

    def __str__(self):
        return f"Demand for {self.experience.title} on {self.date}"


# -------------------------------------------------------------------
# Signals
# -------------------------------------------------------------------
@receiver(post_save, sender=UserEvent)
def update_user_preference(sender, instance, created, **kwargs):
    if created and instance.user and instance.experience:
        category = instance.experience.category
        pref, _ = UserPreference.objects.get_or_create(user=instance.user)

        weight = 1
        if instance.event_type == "VIEW":
            weight = 1
        elif instance.event_type == "SEARCH":
            weight = 2
        elif instance.event_type == "MESSAGE":
            weight = 3
        elif instance.event_type == "BOOK":
            weight = 5

        current_score = pref.preferred_categories.get(category, 0)
        pref.preferred_categories[category] = current_score + weight
        pref.save()


@receiver(post_save, sender=Booking)
def create_booking_activity(sender, instance, created, **kwargs):
    """
    Create feed activity only when a booking is actually confirmed.
    Avoid duplicates on repeated saves.
    """
    if instance.user and instance.booking_status == Booking.Status.CONFIRMED:
        action_text = f"{instance.user.first_name or instance.user.username} just booked {instance.experience.title}!"
        already_exists = ActivityFeed.objects.filter(
            user=instance.user,
            experience=instance.experience,
            action_text=action_text,
            created_at__gte=instance.created_at,
        ).exists()
        if not already_exists:
            ActivityFeed.objects.create(
                user=instance.user,
                experience=instance.experience,
                action_text=action_text,
            )


@receiver(post_save, sender=Booking)
def notify_booking_created(sender, instance, created, **kwargs):
    if created and instance.experience.host:
        from chat.utils import send_realtime_notification
        send_realtime_notification(
            user_id=instance.experience.host.id,
            title="New Booking Request",
            message=f"New booking for {instance.experience.title} from {instance.traveler_name}.",
            link="/dashboard/host/",
        )


@receiver(post_save, sender=Message)
def notify_new_message(sender, instance, created, **kwargs):
    if created:
        recipient = (
            instance.conversation.host
            if instance.sender == instance.conversation.user
            else instance.conversation.user
        )

        from chat.utils import send_realtime_notification
        send_realtime_notification(
            user_id=recipient.id,
            title="New Message",
            message=f"New message from {instance.sender.username}.",
            link=f"/messages/{instance.conversation.id}/",
        )

        try:
            from marketplace.services.emails import send_new_message_email
            send_new_message_email(instance, recipient)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to send new message email: {e}")


@receiver(post_save, sender=Review)
def notify_new_review(sender, instance, created, **kwargs):
    if created and instance.host:
        from chat.utils import send_realtime_notification
        send_realtime_notification(
            user_id=instance.host.id,
            title="New Review",
            message=f"New {instance.rating}-star review on {instance.experience.title}.",
            link=f"/experiences/{instance.experience.slug}/",
        )

        try:
            from marketplace.services.emails import send_new_review_email
            send_new_review_email(instance)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to send new review email: {e}")