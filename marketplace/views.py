from datetime import date, datetime, timedelta
from urllib.parse import quote_plus
import json
import random

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.text import slugify
from django_ratelimit.decorators import ratelimit

from .forms import (
    ExperienceForm,
    SafarUserCreationForm,
    UserProfileForm,
    UserUpdateForm,
)
from .models import (
    Booking,
    CATEGORY_CHOICES,
    Conversation,
    Experience,
    ExperienceAvailabilityBlock,
    ExperienceImage,
    HeroSlide,
    Location,
    UserProfile,
)

# Optional email services (won't crash app if file/module not ready yet)
try:
    from marketplace.services.emails import (
        send_booking_created_email,
        send_payment_success_email,
        send_host_new_booking_email,
        send_booking_status_update_email,
    )
except Exception:
    def send_booking_created_email(*args, **kwargs):
        return None

    def send_payment_success_email(*args, **kwargs):
        return None

    def send_host_new_booking_email(*args, **kwargs):
        return None

    def send_booking_status_update_email(*args, **kwargs):
        return None


# -------------------------------------------------------------------
# Booking State Machine
# -------------------------------------------------------------------
ALLOWED_TRANSITIONS = {
    "pending": ["cancelled"],
    "payment_processing": ["cancelled"],
    "confirmed": ["completed", "cancelled", "refunded"],
    "completed": [],
    "cancelled": [],
    "refunded": [],
}


# -------------------------------------------------------------------
# Category UI metadata
# -------------------------------------------------------------------
CATEGORY_META = {
    "Adventure": {
        "icon": "bi bi-compass-fill",
        "description": "Thrilling outdoor experiences for adrenaline seekers.",
        "image": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=900&q=80",
    },
    "Spiritual": {
        "icon": "bi bi-flower1",
        "description": "Peaceful journeys, temples, retreats, and soulful escapes.",
        "image": "https://images.unsplash.com/photo-1524492412937-b28074a5d7da?auto=format&fit=crop&w=900&q=80",
    },
    "Homestay": {
        "icon": "bi bi-house-heart-fill",
        "description": "Cozy local stays with warm hospitality and comfort.",
        "image": "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=900&q=80",
    },
    "Trek": {
        "icon": "bi bi-signpost-split-fill",
        "description": "Scenic trekking routes through hills, forests, and valleys.",
        "image": "https://images.unsplash.com/photo-1551632811-561732d1e306?auto=format&fit=crop&w=900&q=80",
    },
    "Wildlife": {
        "icon": "bi bi-tree-fill",
        "description": "Nature and wildlife experiences in forests and reserves.",
        "image": "https://images.unsplash.com/photo-1474511320723-9a56873867b5?auto=format&fit=crop&w=900&q=80",
    },
    "Cultural": {
        "icon": "bi bi-camera-fill",
        "description": "Local culture, heritage, food, festivals, and traditions.",
        "image": "https://images.unsplash.com/photo-1521295121783-8a321d551ad2?auto=format&fit=crop&w=900&q=80",
    },
}

from django.http import HttpResponse

def health_check(request):
    return HttpResponse("ok", status=200)
# -------------------------------------------------------------------
# Homepage
# -------------------------------------------------------------------
def home(request):
    global_cache_key = "safar_home_global_data"
    global_data = cache.get(global_cache_key)

    if not global_data:
        from marketplace.models import ActivityFeed

        base_qs = (
            Experience.objects.filter(
                is_active=True,
                status=Experience.Status.APPROVED,
            )
            .select_related("host", "location_fk")
            .prefetch_related("images")
            .annotate(
                avg_rating=Avg("reviews__rating"),
                review_count=Count("reviews"),
            )
        )

        featured_experiences = list(base_qs.order_by("-created_at")[:6])
        trending_experiences = sorted(base_qs, key=lambda exp: exp.ranking_score, reverse=True)[:6]
        categories = [c[0] for c in CATEGORY_CHOICES]
        locations = list(Location.objects.all().order_by("name")[:10])
        hero_slides = list(HeroSlide.objects.filter(is_active=True).order_by("sort_order", "id"))
        # recent_activities = list(
        #     ActivityFeed.objects.select_related("user", "experience").all()[:5]
        # )
        recent_activities = list(
            ActivityFeed.objects.select_related(
                "user",
                "user__userprofile",
                "experience",
            )
            .filter(
                user__userprofile__isnull=False,
                experience__isnull=False,
            )
            .order_by("-created_at")[:5]
        )

        global_data = {
            "featured_experiences": featured_experiences,
            "trending_experiences": trending_experiences,
            "categories": categories,
            "locations": locations,
            "hero_slides": hero_slides,
            "recent_activities": recent_activities,
        }
        cache.set(global_cache_key, global_data, 60 * 15)

    recommended_experiences = []
    if request.user.is_authenticated:
        from marketplace.models import UserPreference

        pref = UserPreference.objects.filter(user=request.user).first()
        if pref and pref.preferred_categories:
            top_category = max(pref.preferred_categories, key=pref.preferred_categories.get)
            rec_qs = (
                Experience.objects.filter(
                    is_active=True,
                    status=Experience.Status.APPROVED,
                    category=top_category,
                )
                .select_related("host", "location_fk")
                .prefetch_related("images")
                .annotate(
                    avg_rating=Avg("reviews__rating"),
                    review_count=Count("reviews"),
                )
                .exclude(id__in=[e.id for e in global_data["trending_experiences"]])[:6]
            )
            recommended_experiences = list(rec_qs)

    if not recommended_experiences:
        recommended_experiences = global_data["featured_experiences"] or []

    return render(
        request,
        "marketplace/index.html",
        {
            "featured_listings": global_data["featured_experiences"],
            "trending_listings": global_data["trending_experiences"],
            "recommended_listings": recommended_experiences,
            "recent_activities": global_data["recent_activities"],
            "categories": global_data["categories"],
            "locations": global_data["locations"],
            "hero_slides": global_data["hero_slides"],
        },
    )


# -------------------------------------------------------------------
# Location fallback helpers
# -------------------------------------------------------------------
LOCATION_FALLBACKS = {
    "rishikesh": "https://images.unsplash.com/photo-1477587458883-47145ed94245?auto=format&fit=crop&w=1200&q=80",
    "mussoorie": "https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=1200&q=80",
    "nainital": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1200&q=80",
    "dehradun": "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&w=1200&q=80",
    "haridwar": "https://images.unsplash.com/photo-1524492412937-b28074a5d7da?auto=format&fit=crop&w=1200&q=80",
    "shimla": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1200&q=80",
    "manali": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1200&q=80",
    "goa": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200&q=80",
    "jaipur": "https://images.unsplash.com/photo-1477587458883-47145ed94245?auto=format&fit=crop&w=1200&q=80",
    "varanasi": "https://images.unsplash.com/photo-1524492412937-b28074a5d7da?auto=format&fit=crop&w=1200&q=80",
    "leh": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1200&q=80",
}


def _fallback_location_img(name: str) -> str:
    q = quote_plus(f"{name} India travel mountains nature")
    return f"https://source.unsplash.com/900x600/?{q}"


# -------------------------------------------------------------------
# Listings
# -------------------------------------------------------------------
def listing_list(request):
    listings = (
        Experience.objects.filter(
            is_active=True,
            status=Experience.Status.APPROVED,
        )
        .select_related("host", "location_fk")
        .prefetch_related("images")
        .annotate(avg_rating=Avg("reviews__rating"), review_count=Count("reviews"))
    )

    location_slug = (request.GET.get("location") or "").strip().lower()
    category_slug = (request.GET.get("category") or "").strip().lower()
    min_price = (request.GET.get("min_price") or "").strip()
    max_price = (request.GET.get("max_price") or "").strip()
    sort = (request.GET.get("sort") or "newest").strip().lower()

    start_date_str = request.GET.get("start_date", "").strip()
    end_date_str = request.GET.get("end_date", "").strip()
    guests_str = (request.GET.get("guests") or "").strip()

    active_filters = []

    def _remove_params(*params):
        q = request.GET.copy()
        for param in params:
            if param in q:
                del q[param]
        if "page" in q:
            del q["page"]
        return "?" + q.urlencode() if q else "?"

    query = Q()

    # Location filter
    if location_slug:
        selected_location_obj = Location.objects.filter(slug__iexact=location_slug).first()

        if selected_location_obj:
            query &= Q(location_fk=selected_location_obj)
            active_filters.append(
                {
                    "label": f"Location: {selected_location_obj.name}",
                    "remove_url": _remove_params("location"),
                }
            )
        else:
            location_text = location_slug.replace("-", " ")
            query &= Q(location__icontains=location_text) | Q(location_fk__name__icontains=location_text)
            active_filters.append(
                {
                    "label": f"Location: {location_text.title()}",
                    "remove_url": _remove_params("location"),
                }
            )

    # Category filter
    category_slug_map = {slugify(c[0]).lower(): c[0] for c in CATEGORY_CHOICES}
    if category_slug:
        actual_category = category_slug_map.get(category_slug)
        if actual_category:
            query &= Q(category__iexact=actual_category)
            active_filters.append(
                {
                    "label": f"Category: {actual_category}",
                    "remove_url": _remove_params("category"),
                }
            )

    # Price filters
    if min_price:
        try:
            min_val = float(min_price)
            if min_val >= 0:
                query &= Q(price_per_person__gte=min_val)
                active_filters.append(
                    {
                        "label": f"Min: ₹{min_val:g}",
                        "remove_url": _remove_params("min_price"),
                    }
                )
        except ValueError:
            pass

    if max_price:
        try:
            max_val = float(max_price)
            if max_val >= 0:
                query &= Q(price_per_person__lte=max_val)
                active_filters.append(
                    {
                        "label": f"Max: ₹{max_val:g}",
                        "remove_url": _remove_params("max_price"),
                    }
                )
        except ValueError:
            pass

    # Date & guest filters
    start_date = None
    end_date = None
    guests = 1

    if guests_str:
        try:
            guests = int(guests_str)
            if guests > 1:
                active_filters.append(
                    {
                        "label": f"{guests} Guests",
                        "remove_url": _remove_params("guests"),
                    }
                )
        except ValueError:
            guests = 1

    if start_date_str:
        try:
            from .models import AvailabilitySlot
            from django.db.models import F

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            if end_date_str:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

            date_label = start_date.strftime("%b %d")
            if end_date and end_date > start_date:
                date_label += f" - {end_date.strftime('%b %d')}"

            active_filters.append(
                {
                    "label": f"Dates: {date_label}",
                    "remove_url": _remove_params("start_date", "end_date"),
                }
            )

            available_experience_ids = AvailabilitySlot.objects.filter(
                date=start_date,
                is_available=True,
                capacity__gte=F("booked_count") + guests,
            ).values_list("experience_id", flat=True)

            query &= Q(id__in=available_experience_ids)
        except ValueError:
            pass

    if not start_date and guests > 1:
        query &= Q(max_guests__gte=guests)

    listings = listings.filter(query)

    valid_sorts = {
        "newest": "-created_at",
        "price_asc": "price_per_person",
        "price_desc": "-price_per_person",
        "rating_desc": "-avg_rating",
        "reviews_desc": "-review_count",
        "recommended": "ranking_score",
    }
    sort_field = valid_sorts.get(sort, "recommended")

    if sort_field == "ranking_score":
        listings = sorted(listings, key=lambda exp: exp.ranking_score, reverse=True)
    else:
        listings = listings.order_by(sort_field, "-created_at", "-id")

    paginator = Paginator(listings, 6)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    q_copy = request.GET.copy()
    if "page" in q_copy:
        del q_copy["page"]
    query_string = q_copy.urlencode()
    pagination_base_url = f"?{query_string}&page=" if query_string else "?page="

    location_rows = cache.get("safar_location_options")
    if not location_rows:
        location_rows = list(Location.objects.all().order_by("name"))
        cache.set("safar_location_options", location_rows, 60 * 60 * 24)

    location_options = [
        {
            "label": f"{loc.name}" + (f", {loc.state}" if getattr(loc, "state", None) else ""),
            "value": loc.slug.lower(),
            "selected": (loc.slug.lower() == location_slug),
        }
        for loc in location_rows
    ]

    categories = [c[0] for c in CATEGORY_CHOICES]
    category_options = [
        {
            "label": cat,
            "value": slugify(cat).lower(),
            "selected": (slugify(cat).lower() == category_slug),
        }
        for cat in categories
    ]

    sort_options = [
        {"value": "recommended", "label": "Recommended", "selected": (sort == "recommended")},
        {"value": "newest", "label": "Newest", "selected": (sort == "newest" or not sort)},
        {"value": "price_asc", "label": "Price: Low to High", "selected": (sort == "price_asc")},
        {"value": "price_desc", "label": "Price: High to Low", "selected": (sort == "price_desc")},
        {"value": "rating_desc", "label": "Rating: High to Low", "selected": (sort == "rating_desc")},
        {"value": "reviews_desc", "label": "Most Reviewed", "selected": (sort == "reviews_desc")},
    ]

    return render(
        request,
        "marketplace/experiences_v3.html",
        {
            "page_obj": page_obj,
            "location_options": location_options,
            "category_options": category_options,
            "selected_location": location_slug,
            "selected_category": category_slug,
            "active_filters": active_filters,
            "current_sort": sort,
            "sort_options": sort_options,
            "pagination_base_url": pagination_base_url,
        },
    )


def listing_detail(request, slug):
    base_qs = (
        Experience.objects.select_related("host", "location_fk")
        .prefetch_related("images", "blocked_dates", "bookings", "reviews__reviewer")
        .annotate(avg_rating=Avg("reviews__rating"), review_count=Count("reviews"))
        .filter(slug=slug, is_active=True)
    )

    if request.user.is_authenticated:
        base_qs = base_qs.filter(Q(status=Experience.Status.APPROVED) | Q(host=request.user))
    else:
        base_qs = base_qs.filter(status=Experience.Status.APPROVED)

    listing = get_object_or_404(base_qs)

    booked_ranges = []
    host_blocked_ranges = []
    unavailable_preview = []

    def _range_to_inclusive_dict(start_date, end_date, reason, kind):
        if not start_date or not end_date or end_date <= start_date:
            return None
        end_inclusive = end_date - timedelta(days=1)
        if end_inclusive < start_date:
            return None
        return {
            "from": start_date.isoformat(),
            "to": end_inclusive.isoformat(),
            "reason": reason,
            "kind": kind,
        }

    def _merge_ranges(ranges):
        if not ranges:
            return []

        parsed = []
        for r in ranges:
            try:
                s = datetime.strptime(r["from"], "%Y-%m-%d").date()
                e = datetime.strptime(r["to"], "%Y-%m-%d").date()
                if e >= s:
                    parsed.append((s, e))
            except Exception:
                continue

        if not parsed:
            return []

        parsed.sort(key=lambda x: x[0])
        merged = [list(parsed[0])]

        for s, e in parsed[1:]:
            last_s, last_e = merged[-1]
            if s <= (last_e + timedelta(days=1)):
                if e > last_e:
                    merged[-1][1] = e
            else:
                merged.append([s, e])

        return [{"from": s.isoformat(), "to": e.isoformat()} for s, e in merged]

    active_bookings = listing.bookings.exclude(
        Q(booking_status__in=["cancelled", "refunded"]) |
        Q(payment__payment_status__in=["failed", "refunded"])
    )

    for b in active_bookings:
        item = _range_to_inclusive_dict(
            b.check_in_date,
            b.check_out_date,
            "Already booked",
            "booked",
        )
        if item:
            booked_ranges.append({"from": item["from"], "to": item["to"]})
            unavailable_preview.append(item)

    for blk in listing.blocked_dates.all():
        item = _range_to_inclusive_dict(
            blk.start_date,
            blk.end_date,
            blk.reason or "Blocked by host",
            "blocked",
        )
        if item:
            host_blocked_ranges.append({"from": item["from"], "to": item["to"]})
            unavailable_preview.append(item)

    calendar_unavailable_ranges = _merge_ranges(booked_ranges + host_blocked_ranges)
    unavailable_preview = sorted(unavailable_preview, key=lambda x: (x["from"], x["to"]))[:8]

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={request.path}")

        start_date_str = request.POST.get("start_date")
        end_date_str = request.POST.get("end_date")
        guests_str = request.POST.get("guests")
        traveler_name = (request.POST.get("traveler_name") or "").strip()
        traveler_email = (request.POST.get("traveler_email") or "").strip()
        traveler_phone = (request.POST.get("traveler_phone") or "").strip()
        message = request.POST.get("message", "")

        if not traveler_name or not traveler_email or not traveler_phone:
            messages.error(request, "Please fill in Full Name, Email, and Phone to continue with booking.")
            return redirect("listing_detail", slug=slug)

        try:
            from .models import AvailabilitySlot
            from marketplace.pricing_engine import calculate_dynamic_price

            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            guests = int(guests_str)

            if start_date < date.today():
                messages.error(request, "Check-in date cannot be in the past.")
                return redirect("listing_detail", slug=slug)

            if end_date <= start_date:
                messages.error(request, "Check-out must be after check-in. Please select at least 1 night.")
                return redirect("listing_detail", slug=slug)

            if guests <= 0:
                messages.error(request, "Please select at least 1 guest.")
                return redirect("listing_detail", slug=slug)

            if guests > listing.max_guests:
                messages.error(request, f"This experience allows a maximum of {listing.max_guests} guests.")
                return redirect("listing_detail", slug=slug)

            days = (end_date - start_date).days
            per_person_price = calculate_dynamic_price(listing, start_date)
            total_price = days * per_person_price * guests

            if total_price <= 0:
                messages.error(request, "Invalid booking amount. Please re-check dates and guests.")
                return redirect("listing_detail", slug=slug)

            overlapping_bookings = Booking.objects.filter(
                experience=listing,
                check_in_date__lt=end_date,
                check_out_date__gt=start_date,
            ).exclude(
                booking_status__in=["cancelled", "refunded"],
                payment__payment_status__in=["failed", "refunded"],
            )

            if overlapping_bookings.exists():
                messages.error(
                    request,
                    "Those dates are already booked. Please choose different check-in/check-out dates.",
                )
                return redirect("listing_detail", slug=slug)

            slot = AvailabilitySlot.objects.filter(
                experience=listing,
                date=start_date,
                is_available=True,
            ).first()

            if slot:
                available_capacity = slot.capacity - slot.booked_count
                if guests > available_capacity:
                    messages.error(
                        request,
                        f"Only {available_capacity} seats remaining for {start_date}. Please reduce guest count.",
                    )
                    return redirect("listing_detail", slug=slug)

            overlapping_blocks = ExperienceAvailabilityBlock.objects.filter(
                experience=listing,
                start_date__lt=end_date,
                end_date__gt=start_date,
            )

            if overlapping_blocks.exists():
                first_block = overlapping_blocks.order_by("start_date").first()
                if first_block and first_block.reason:
                    messages.error(
                        request,
                        f"These dates are unavailable ({first_block.reason}). Please select different dates.",
                    )
                else:
                    messages.error(
                        request,
                        "These dates are unavailable because the host has blocked them.",
                    )
                return redirect("listing_detail", slug=slug)

            booking = Booking.objects.create(
                experience=listing,
                user=request.user,
                traveler_name=traveler_name,
                traveler_email=traveler_email,
                traveler_phone=traveler_phone,
                check_in_date=start_date,
                check_out_date=end_date,
                guests_count=guests,
                message=message,
                booking_status="payment_processing",
                total_price=total_price,
            )

            send_booking_created_email(booking)

            from payments.services import create_razorpay_order
            ok, payment_or_error = create_razorpay_order(booking)
            if not ok:
                messages.warning(
                    request,
                    f"Booking created, but payment order could not be created: {payment_or_error}",
                )

            return redirect("checkout", pk=booking.id)

        except (ValueError, TypeError):
            messages.error(
                request,
                "Invalid booking input. Please check dates and number of guests, then try again.",
            )
            return redirect("listing_detail", slug=slug)

    review_list = listing.reviews.all().order_by("-created_at")
    paginator = Paginator(review_list, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "marketplace/experience_detail_v3.html",
        {
            "listing": listing,
            "page_obj": page_obj,
            "guest_numbers": range(1, listing.max_guests + 1),
            "booked_ranges": booked_ranges,
            "host_blocked_ranges": host_blocked_ranges,
            "calendar_unavailable_ranges": calendar_unavailable_ranges,
            "unavailable_preview": unavailable_preview,
        },
    )


@login_required
def checkout(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related("experience", "experience__host"),
        pk=pk,
        user=request.user,
    )

    if booking.booking_status in ["completed", "cancelled", "refunded"]:
        return redirect("my_bookings")

    from payments.services import create_razorpay_order

    success, payment_or_error = create_razorpay_order(booking)

    if not success:
        messages.error(request, f"Error initializing payment: {payment_or_error}")
        return redirect("my_bookings")

    if payment_or_error.payment_status == "success":
        messages.info(request, "This booking has already been paid.")
        return redirect("my_bookings")

    context = {
        "booking": booking,
        "payment": payment_or_error,
        "razorpay_key_id": getattr(settings, "RAZORPAY_KEY_ID", ""),
        "is_demo_mode": getattr(settings, "PAYMENTS_DEMO_MODE", False),
    }
    return render(request, "marketplace/checkout.html", context)


@login_required
def booking_success(request):
    booking = None
    booking_id = request.GET.get("booking_id") or request.session.get("last_booking_success_id")

    if booking_id:
        booking = (
            Booking.objects.filter(pk=booking_id, user=request.user)
            .select_related("experience")
            .first()
        )

    return render(request, "marketplace/booking_success.html", {"booking": booking})


# -------------------------------------------------------------------
# Auth
# -------------------------------------------------------------------
def signup_view(request):
    if request.method == "POST":
        form = SafarUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful. Welcome to Safar!")

            next_url = request.GET.get("next") or request.POST.get("next")
            url_is_safe = url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            )
            return redirect(next_url if url_is_safe else "home")

        messages.error(request, "Registration failed. Please correct the errors below.")
    else:
        form = SafarUserCreationForm()

    return render(request, "marketplace/signup.html", {"form": form})


@ratelimit(key="ip", rate="5/m", block=True)
def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get("next") or request.POST.get("next")
                url_is_safe = url_has_allowed_host_and_scheme(
                    url=next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                )
                messages.success(request, f"Welcome back, {username}!")
                return redirect(next_url if url_is_safe else "home")
        messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(
        request,
        "marketplace/login.html",
        {"form": form, "next": request.GET.get("next", "")},
    )


@ratelimit(key="ip", rate="5/m", block=True)
def otp_login_view(request):
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip()
        if not email:
            messages.error(request, "Please enter your email address.")
            return redirect("otp_login")

        user = User.objects.filter(email=email).first()
        if user:
            from .models import EmailOTP
            from .services.emails import send_otp_email

            otp_code = str(random.randint(100000, 999999))
            EmailOTP.objects.create(user=user, otp=otp_code)
            send_otp_email(user, otp_code)
            request.session["otp_user_id"] = user.id
            messages.success(request, "An OTP has been sent to your email.")
            return redirect("otp_verify")

        messages.info(request, "If an account exists with this email, an OTP has been sent.")
        return redirect("otp_login")

    return render(request, "marketplace/otp_login.html")


@ratelimit(key="ip", rate="5/m", block=True)
def otp_verify_view(request):
    user_id = request.session.get("otp_user_id")
    if not user_id:
        messages.error(request, "Please initiate OTP login first.")
        return redirect("otp_login")

    if request.method == "POST":
        otp_input = request.POST.get("otp")
        user = get_object_or_404(User, id=user_id)
        from .models import EmailOTP

        five_mins_ago = timezone.now() - timezone.timedelta(minutes=5)
        valid_otp = EmailOTP.objects.filter(
            user=user,
            otp=otp_input,
            verified=False,
            created_at__gte=five_mins_ago,
        ).last()

        if valid_otp:
            valid_otp.verified = True
            valid_otp.save()
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            del request.session["otp_user_id"]

            next_url = request.GET.get("next") or request.POST.get("next")
            url_is_safe = url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            )
            messages.success(request, "Successfully verified OTP! Welcome back.")
            return redirect(next_url if url_is_safe else "home")

        messages.error(request, "Invalid or expired OTP. Please try again or request a new one.")

    return render(request, "marketplace/otp_verification.html")


def logout_view(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect("home")


@login_required
def dashboard_router(request):
    user = request.user
    if user.is_superuser:
        return redirect("/admin/")

    profile = getattr(user, "userprofile", None)
    if profile and profile.is_host:
        return redirect("host_dashboard")

    return redirect("profile")


# -------------------------------------------------------------------
# User bookings / host dashboard
# -------------------------------------------------------------------
@login_required
def my_bookings(request):
    bookings = (
        Booking.objects.filter(user=request.user)
        .select_related("experience")
        .prefetch_related("review")
        .order_by("-created_at")
    )
    return render(request, "marketplace/my_bookings.html", {"bookings": bookings})


@login_required
def host_dashboard(request):
    profile = getattr(request.user, "userprofile", None)
    is_verified_host = bool(getattr(profile, "is_host", False))

    if not is_verified_host:
        messages.error(request, "You do not have permission to access the host dashboard.")
        return redirect("home")

    listings = Experience.objects.filter(host=request.user)
    bookings = (
        Booking.objects.filter(experience__host=request.user)
        .select_related("experience", "user")
        .order_by("-created_at")
    )

    today = date.today()
    from payments.models import LedgerEntry

    aggs = bookings.aggregate(
        confirmed=Count("id", filter=Q(booking_status="confirmed")),
        completed=Count("id", filter=Q(booking_status="completed")),
        cancelled=Count("id", filter=Q(booking_status="cancelled")),
        upcoming=Count("id", filter=Q(booking_status="confirmed", check_in_date__gte=today)),
    )

    ledger_earnings_agg = LedgerEntry.objects.filter(
        booking__experience__host=request.user,
        entry_type="host_earning",
    ).aggregate(Sum("amount"))
    ledger_earnings = abs(ledger_earnings_agg["amount__sum"] or 0)

    analytics = {
        "total_listings": listings.count(),
        "total_bookings": bookings.count(),
        "confirmed_bookings": aggs["confirmed"] or 0,
        "completed_bookings": aggs["completed"] or 0,
        "cancelled_bookings": aggs["cancelled"] or 0,
        "total_earnings": ledger_earnings,
        "upcoming_checkins": aggs["upcoming"] or 0,
    }
    status_counts = list(bookings.values("booking_status").annotate(count=Count("id")))

    chart_labels = []
    chart_bookings = []
    chart_revenue = []

    curr = today.replace(day=1)
    months_list = []
    for _ in range(6):
        months_list.insert(0, curr)
        curr = (curr - timedelta(days=1)).replace(day=1)

    for m in months_list:
        chart_labels.append(m.strftime("%b %Y"))
        b_count = bookings.filter(
            booking_status__in=["confirmed", "completed"],
            created_at__year=m.year,
            created_at__month=m.month,
        ).count()
        chart_bookings.append(b_count)

        r_sum = LedgerEntry.objects.filter(
            booking__experience__host=request.user,
            entry_type="host_earning",
            created_at__year=m.year,
            created_at__month=m.month,
        ).aggregate(Sum("amount"))["amount__sum"] or 0
        chart_revenue.append(abs(float(r_sum)))

    chart_data = json.dumps(
        {
            "labels": chart_labels,
            "bookings": chart_bookings,
            "revenue": chart_revenue,
        }
    )

    if request.method == "POST":
        booking_id = request.POST.get("booking_id")
        new_status = (request.POST.get("status") or "").strip().lower()

        if booking_id and new_status:
            booking = get_object_or_404(
                Booking,
                id=booking_id,
                experience__host=request.user,
            )
            current_status = booking.booking_status

            allowed = ALLOWED_TRANSITIONS.get(current_status, [])
            if new_status not in allowed:
                messages.error(request, f"Invalid transition: '{current_status}' → '{new_status}'.")
                return redirect("host_dashboard")

            if new_status == "completed":
                if not (booking.payment_status == "Paid" and booking.check_out_date < today):
                    messages.error(
                        request,
                        "Cannot complete: booking must be Paid and past check-out date.",
                    )
                    return redirect("host_dashboard")

            if new_status == "cancelled" and booking.payment_status == "Paid":
                booking.payment_status = "Refunded"

            was_completed = current_status == "completed"
            booking.booking_status = new_status
            booking.save()
            send_booking_status_update_email(booking)

            if new_status == "completed" and not was_completed:
                from django.core.mail import send_mail

                review_url = request.build_absolute_uri(reverse("leave_review", args=[booking.id]))
                send_mail(
                    subject=f"How was your experience with {booking.experience.host.username}?",
                    message=(
                        f"Hi {booking.traveler_name or booking.user.username},\n\n"
                        f"We hope you enjoyed your trip to {booking.experience.title}!\n"
                        f"Please take a moment to leave a review for your host:\n{review_url}\n\n"
                        "Thanks,\nThe Safar Team"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[booking.traveler_email or booking.user.email],
                    fail_silently=True,
                )

            messages.success(request, f"Booking status updated to '{new_status}'.")
            return redirect("host_dashboard")

    bookings_with_transitions = [
        (b, ALLOWED_TRANSITIONS.get(b.booking_status, [])) for b in bookings
    ]

    from .models import AvailabilitySlot, DynamicPricingRule

    availability_slots = AvailabilitySlot.objects.filter(
        experience__host=request.user,
        date__gte=today,
    ).order_by("date", "start_time")

    payout_entries = LedgerEntry.objects.filter(
        booking__experience__host=request.user,
        entry_type="host_earning",
    ).select_related("booking", "booking__experience").order_by("-created_at")

    pricing_rules = DynamicPricingRule.objects.filter(
        experience__host=request.user
    ).order_by("experience__title", "-active")

    return render(
        request,
        "marketplace/host_dashboard_v3.html",
        {
            "listings": listings,
            "my_experiences": listings,
            "availability_slots": availability_slots,
            "payout_entries": payout_entries,
            "bookings": bookings,
            "bookings_with_transitions": bookings_with_transitions,
            "analytics": analytics,
            "status_counts": status_counts,
            "chart_data": chart_data,
            "is_verified_host": is_verified_host,
            "pricing_rules": pricing_rules,
        },
    )


# -------------------------------------------------------------------
# Locations / categories
# -------------------------------------------------------------------
def location_list(request):
    locations = Location.objects.all().order_by("name")
    return render(request, "marketplace/locations.html", {"locations": locations})


def categories_view(request):
    categories = []

    for value, label in CATEGORY_CHOICES:
        meta = CATEGORY_META.get(value, {})
        categories.append(
            {
                "name": label,
                "slug": slugify(value).lower(),
                "icon": meta.get("icon", "bi bi-grid-3x3-gap-fill"),
                "description": meta.get(
                    "description",
                    "Explore curated experiences in this category.",
                ),
                "image": meta.get(
                    "image",
                    "https://images.unsplash.com/photo-1488085061387-422e29b40080?auto=format&fit=crop&w=900&q=80",
                ),
            }
        )

    return render(request, "marketplace/categories.html", {"categories": categories})


def category_list(request):
    return categories_view(request)


# -------------------------------------------------------------------
# Cancel / review
# -------------------------------------------------------------------
@login_required
def cancel_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)

    if request.method == "POST":
        current_booking_status = (booking.booking_status or "").lower()

        if current_booking_status not in ["completed", "cancelled", "refunded"]:
            booking.booking_status = "cancelled"

            current_payment_status = str(getattr(booking, "payment_status", "") or "").lower()

            if current_payment_status == "paid":
                start_datetime = timezone.make_aware(
                    datetime.combine(booking.check_in_date, datetime.min.time())
                )

                if (start_datetime - timezone.now()).total_seconds() >= 48 * 3600:
                    booking.payment_status = "Refunded"
                    messages.success(request, "Booking cancelled. Full refund has been initiated.")
                else:
                    messages.warning(
                        request,
                        "Booking cancelled. No refund (within 48 hours of start date).",
                    )
            else:
                messages.success(request, "Booking cancelled successfully.")

            booking.save()

    return redirect("my_bookings")


@login_required
def leave_review(request, pk):
    booking = get_object_or_404(Booking, id=pk, user=request.user)

    if booking.booking_status != "completed":
        messages.error(request, "You can only review completed experiences.")
        return redirect("my_bookings")

    if hasattr(booking, "review"):
        messages.info(request, "You have already left a review for this booking.")
        return redirect("my_bookings")

    if request.method == "POST":
        from django.db import IntegrityError
        from .models import Review
        from chat.utils import send_realtime_notification

        rating = request.POST.get("rating")
        comment = request.POST.get("comment")

        try:
            rating = int(rating)
            if not (1 <= rating <= 5):
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "Please provide a valid rating between 1 and 5.")
            return redirect("leave_review", pk=pk)

        if not comment or not comment.strip():
            messages.error(request, "Please provide a written review.")
            return redirect("leave_review", pk=pk)

        try:
            Review.objects.create(
                booking=booking,
                reviewer=request.user,
                host=booking.experience.host,
                experience=booking.experience,
                rating=rating,
                comment=comment.strip(),
            )

            send_realtime_notification(
                user_id=booking.experience.host.id,
                title="New Review",
                message=f"{request.user.username} left a {rating}-star review on {booking.experience.title}.",
                link=f"/experiences/{booking.experience.slug}/",
            )

            messages.success(request, "Thank you for your review!")
            return redirect("my_bookings")
        except IntegrityError:
            messages.error(request, "You have already left a review.")
            return redirect("my_bookings")

    return render(request, "marketplace/leave_review.html", {"booking": booking})


# -------------------------------------------------------------------
# Host tools
# -------------------------------------------------------------------
@login_required
def add_experience_view(request):
    if not hasattr(request.user, "userprofile") or not request.user.userprofile.is_host:
        messages.error(request, "Only hosts can create experiences.")
        return redirect("home")

    if request.method == "POST":
        form = ExperienceForm(request.POST, request.FILES)
        if form.is_valid():
            experience = form.save(commit=False)
            experience.host = request.user
            experience.save()

            experience.amenities = form.cleaned_data["amenities"]
            experience.save()

            images = request.FILES.getlist("images")
            for index, image in enumerate(images):
                ExperienceImage.objects.create(
                    experience=experience,
                    image=image,
                    is_primary=(index == 0),
                )

            messages.success(request, f"Experience '{experience.title}' created successfully!")
            return redirect("host_dashboard")

        messages.error(request, "Please correct the errors below.")
    else:
        form = ExperienceForm()

    return render(
        request,
        "marketplace/add_experience.html",
        {
            "form": form,
            "title": "Add New Experience",
        },
    )


@login_required
def add_availability_slots(request):
    if request.method == "POST":
        from .models import AvailabilitySlot

        experience_id = request.POST.get("experience_id")
        start_date_str = request.POST.get("start_date")
        end_date_str = request.POST.get("end_date")
        start_time_str = request.POST.get("start_time")
        capacity = request.POST.get("capacity")

        experience = get_object_or_404(Experience, id=experience_id, host=request.user)

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else start_date
            capacity = int(capacity)

            start_time = None
            if start_time_str:
                start_time = datetime.strptime(start_time_str, "%H:%M").time()

            current_date = start_date
            created_count = 0
            while current_date <= end_date:
                _, created = AvailabilitySlot.objects.update_or_create(
                    experience=experience,
                    date=current_date,
                    start_time=start_time,
                    defaults={"capacity": capacity, "is_available": True},
                )
                if created:
                    created_count += 1
                current_date += timedelta(days=1)

            messages.success(request, f"Successfully created/updated {created_count} availability slots.")
        except ValueError:
            messages.error(request, "Invalid date/time/capacity format provided.")

    return redirect("host_dashboard")


@login_required
def toggle_slot_availability(request, slot_id):
    if request.method == "POST":
        from .models import AvailabilitySlot

        slot = get_object_or_404(AvailabilitySlot, id=slot_id, experience__host=request.user)
        slot.is_available = not slot.is_available
        slot.save()
        status = "Unblocked" if slot.is_available else "Blocked"
        messages.success(request, f"Slot {status} successfully.")
    return redirect("host_dashboard")


@login_required
def add_pricing_rule(request):
    if request.method == "POST":
        from .models import DynamicPricingRule

        experience_id = request.POST.get("experience_id")
        rule_type = request.POST.get("rule_type")
        multiplier = request.POST.get("multiplier")
        start_date = request.POST.get("start_date") or None
        end_date = request.POST.get("end_date") or None

        try:
            exp = get_object_or_404(Experience, id=experience_id, host=request.user)
            rule = DynamicPricingRule(
                experience=exp,
                rule_type=rule_type,
                multiplier=multiplier,
                start_date=start_date,
                end_date=end_date,
            )
            rule.save()
            messages.success(request, "Dynamic pricing rule added successfully.")
        except Exception as e:
            messages.error(request, f"Failed to add pricing rule: {e}")

    return redirect("host_dashboard")


# -------------------------------------------------------------------
# APIs
# -------------------------------------------------------------------
def api_experience_slots(request, experience_id):
    from .models import AvailabilitySlot

    slots = AvailabilitySlot.objects.filter(
        experience_id=experience_id,
        date__gte=date.today(),
        is_available=True,
    )

    data = {}
    for slot in slots:
        date_str = slot.date.isoformat()
        remaining = slot.capacity - slot.booked_count
        if date_str not in data:
            data[date_str] = {"available": True, "remaining": remaining}
        else:
            data[date_str]["remaining"] += remaining

    return JsonResponse(data)


def api_experience_price(request, experience_id):
    from marketplace.pricing_engine import calculate_dynamic_price

    experience = get_object_or_404(Experience, id=experience_id)
    start_date_str = request.GET.get("start_date")

    target_date = date.today()
    if start_date_str:
        try:
            target_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    price = calculate_dynamic_price(experience, target_date)
    return JsonResponse({"price_per_person": price})


@login_required
def api_unread_notifications_count(request):
    unread_qs = request.user.notifications.filter(is_read=False).order_by("-created_at")
    count = unread_qs.count()
    items = []
    for notif in unread_qs[:3]:
        items.append(
            {
                "title": notif.title,
                "message": notif.message,
                "link": notif.link,
                "created_at": notif.created_at.strftime("%b %d, %H:%M"),
            }
        )
    return JsonResponse({"unread_count": count, "items": items})


# -------------------------------------------------------------------
# Host verification / profile
# -------------------------------------------------------------------
@login_required
def become_host(request):
    from .models import HostVerification

    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if profile.is_host:
        messages.info(request, "You already have a verified host account.")
        return redirect("host_dashboard")

    verification, created = HostVerification.objects.get_or_create(user=request.user)

    if verification.verified:
        profile.is_host = True
        profile.save()
        messages.success(request, "Your host account is activated!")
        return redirect("host_dashboard")

    if request.method == "POST":
        id_image = request.FILES.get("government_id")
        selfie_image = request.FILES.get("selfie")

        if id_image and selfie_image:
            verification.government_id = id_image
            verification.selfie = selfie_image
            verification.save()
            messages.success(
                request,
                "Your identity documents have been submitted for review. You will be notified once a Safar admin approves your request.",
            )
            return redirect("home")

        messages.error(request, "Please provide both a Government ID and a Selfie.")

    return render(
        request,
        "marketplace/become_host.html",
        {
            "pending_verification": bool(not created and verification.government_id)
        },
    )


@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("profile")

        messages.error(request, "Please correct the errors below.")
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = UserProfileForm(instance=profile)

    return render(
        request,
        "marketplace/profile.html",
        {
            "user_form": user_form,
            "profile_form": profile_form,
        },
    )


# -------------------------------------------------------------------
# Messaging / notifications
# -------------------------------------------------------------------
@login_required
def start_conversation(request, experience_id):
    experience = get_object_or_404(Experience, id=experience_id)
    if experience.host == request.user:
        messages.error(request, "You cannot message yourself.")
        return redirect("listing_detail", slug=experience.slug)

    conversation, _ = Conversation.objects.get_or_create(
        user=request.user,
        host=experience.host,
        experience=experience,
    )
    return redirect("conversation_detail", pk=conversation.pk)


@login_required
def inbox_view(request):
    conversations = Conversation.objects.filter(
        Q(user=request.user) | Q(host=request.user)
    ).distinct().order_by("-created_at")

    return render(request, "marketplace/inbox.html", {"conversations": conversations})


@login_required
def conversation_detail_view(request, pk):
    conversation = get_object_or_404(
        Conversation,
        Q(id=pk) & (Q(user=request.user) | Q(host=request.user)),
    )

    conversation.messages.exclude(sender=request.user).update(read=True)

    if request.method == "POST":
        text = request.POST.get("text")
        if text and text.strip():
            from .models import Message

            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                text=text.strip(),
            )
            return redirect("conversation_detail", pk=pk)

    messages_list = conversation.messages.all().order_by("created_at")
    return render(
        request,
        "marketplace/conversation.html",
        {
            "conversation": conversation,
            "messages_list": messages_list,
        },
    )


@login_required
def notifications_view(request):
    notifications = request.user.notifications.all().order_by("-created_at")
    unread = notifications.filter(is_read=False)
    if unread.exists():
        unread.update(is_read=True)

    return render(request, "marketplace/notifications.html", {"notifications": notifications})


# -------------------------------------------------------------------
# Destination pages
# -------------------------------------------------------------------
def destination_view(request, location_slug):
    location = get_object_or_404(Location, slug=location_slug)

    cache_key = f"destination_data_{location.id}"
    cached_data = cache.get(cache_key)

    if not cached_data:
        base_qs = (
            Experience.objects.select_related("host", "location_fk", "host__userprofile")
            .prefetch_related("images", "reviews")
            .annotate(avg_rating=Avg("reviews__rating"), review_count=Count("reviews"))
            .filter(location_fk=location, is_active=True, status=Experience.Status.APPROVED)
        )

        experiences = sorted(base_qs, key=lambda exp: exp.ranking_score, reverse=True)
        top_experiences = experiences[:6]

        top_hosts = []
        seen_host_ids = set()
        for exp in top_experiences:
            if (
                exp.host
                and getattr(exp.host, "userprofile", None)
                and exp.host.userprofile.is_host
                and exp.host.id not in seen_host_ids
            ):
                seen_host_ids.add(exp.host.id)
                top_hosts.append(exp.host)

        total_experiences = len(experiences)
        avg_price = base_qs.aggregate(Avg("price_per_person"))["price_per_person__avg"] or 0
        avg_price = round(avg_price, 0)

        cached_data = {
            "top_experiences": top_experiences,
            "top_hosts": top_hosts[:4],
            "total_experiences": total_experiences,
            "avg_price": avg_price,
        }

        cache.set(cache_key, cached_data, 60 * 15)

    return render(
        request,
        "marketplace/destination.html",
        {
            "location": location,
            "top_experiences": cached_data["top_experiences"],
            "top_hosts": cached_data["top_hosts"],
            "total_experiences": cached_data["total_experiences"],
            "avg_price": cached_data["avg_price"],
        },
    )


# -------------------------------------------------------------------
# Admin analytics
# -------------------------------------------------------------------
@login_required
def platform_analytics(request):
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Admins only.")
        return redirect("home")

    from django.db.models import functions
    from payments.models import LedgerEntry
    from marketplace.models import UserEvent

    today = date.today()
    six_months_ago = today - timedelta(days=180)

    cache_key = "platform_analytics_data_v1"
    cached_data = cache.get(cache_key)

    if not cached_data:
        total_platform_revenue_raw = LedgerEntry.objects.filter(
            entry_type="platform_commission"
        ).aggregate(Sum("amount"))["amount__sum"] or 0
        total_platform_revenue = abs(float(total_platform_revenue_raw))

        total_bookings_count = Booking.objects.count()
        total_users_count = User.objects.count()

        dau_count = UserEvent.objects.filter(created_at__date=today).values("user").distinct().count()
        dau_guests = UserEvent.objects.filter(
            created_at__date=today,
            user__isnull=True,
        ).values("session_key").distinct().count()
        dau_count += dau_guests

        thirty_days_ago = today - timedelta(days=30)
        recent_bookings = Booking.objects.filter(created_at__gte=thirty_days_ago).count()
        recent_visitors = UserEvent.objects.filter(created_at__gte=thirty_days_ago).values(
            "user", "session_key"
        ).distinct().count()

        conversion_rate = 0.0
        if recent_visitors > 0:
            conversion_rate = (recent_bookings / recent_visitors) * 100

        sixty_days_ago = today - timedelta(days=60)
        prev_bookings = Booking.objects.filter(
            created_at__gte=sixty_days_ago,
            created_at__lt=thirty_days_ago,
        ).count()

        booking_growth = 0.0
        if prev_bookings > 0:
            booking_growth = ((recent_bookings - prev_bookings) / prev_bookings) * 100
        elif recent_bookings > 0:
            booking_growth = 100.0

        monthly_revenue = list(
            LedgerEntry.objects.filter(
                entry_type="platform_commission",
                created_at__gte=six_months_ago,
            )
            .annotate(month=functions.TruncMonth("created_at"))
            .values("month")
            .annotate(total=Sum("amount"))
            .order_by("month")
        )

        monthly_bookings = list(
            Booking.objects.filter(created_at__gte=six_months_ago)
            .annotate(month=functions.TruncMonth("created_at"))
            .values("month")
            .annotate(total=Count("id"))
            .order_by("month")
        )

        chart_labels = []
        chart_revenue = []
        chart_bookings = []

        curr = today.replace(day=1)
        months_list = []
        for _ in range(6):
            months_list.insert(0, curr)
            curr = (curr - timedelta(days=1)).replace(day=1)

        revenue_dict = {
            item["month"].date(): abs(float(item["total"]))
            for item in monthly_revenue
            if item["month"]
        }
        bookings_dict = {
            item["month"].date(): int(item["total"])
            for item in monthly_bookings
            if item["month"]
        }

        for m in months_list:
            chart_labels.append(m.strftime("%b %Y"))
            chart_revenue.append(revenue_dict.get(m, 0.0))
            chart_bookings.append(bookings_dict.get(m, 0))

        revenue_chart_json = json.dumps(
            {
                "labels": chart_labels,
                "revenue": chart_revenue,
                "bookings": chart_bookings,
            }
        )

        cached_data = {
            "total_revenue": total_platform_revenue,
            "total_bookings": total_bookings_count,
            "total_users": total_users_count,
            "dau": dau_count,
            "conversion_rate": round(conversion_rate, 2),
            "booking_growth": round(booking_growth, 1),
            "chart_json": revenue_chart_json,
        }

        cache.set(cache_key, cached_data, 3600)

    return render(request, "admin/platform_analytics.html", cached_data)
