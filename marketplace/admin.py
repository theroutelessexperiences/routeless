from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import (
    Location,
    Experience,
    ExperienceImage,
    Booking,
    UserProfile,
    Review,
    ReviewReport,
    HostRequest,
    HostVerification,
    HeroSlide,
    Message,
)

@admin.action(description="Flag selected items")
def flag_items(modeladmin, request, queryset):
    queryset.update(is_flagged=True)

@admin.action(description="Unflag selected items")
def unflag_items(modeladmin, request, queryset):
    queryset.update(is_flagged=False)

@admin.action(description="Hide selected items")
def hide_items(modeladmin, request, queryset):
    queryset.update(is_hidden=True)

@admin.action(description="Unhide selected items")
def unhide_items(modeladmin, request, queryset):
    queryset.update(is_hidden=False)

moderation_actions = [flag_items, unflag_items, hide_items, unhide_items]

@admin.action(description="Approve selected experiences")
def approve_experiences(modeladmin, request, queryset):
    queryset.update(status=Experience.Status.APPROVED)


@admin.action(description="Reject selected experiences")
def reject_experiences(modeladmin, request, queryset):
    queryset.update(status=Experience.Status.REJECTED)


@admin.register(Location)
class LocationAdmin(ModelAdmin):
    list_display = ("name", "state", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "state", "slug")


@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = ("user", "is_host", "phone_number", "is_flagged", "is_hidden")
    list_filter = ("is_host", "is_flagged", "is_hidden")
    search_fields = ("user__username", "phone_number")
    list_select_related = ("user",)
    actions = moderation_actions


class ExperienceImageInline(TabularInline):
    model = ExperienceImage
    extra = 1


@admin.register(Experience)
class ExperienceAdmin(ModelAdmin):
    list_display = (
        "title",
        "location",
        "category",
        "host",
        "price_per_person",
        "status",
        "is_active",
        "is_featured",
        "is_flagged",
        "is_hidden",
    )
    list_filter = (
        "status",
        "is_active",
        "is_featured",
        "is_flagged",
        "is_hidden",
        "location",
        "category",
    )
    search_fields = ("title", "location", "host__username")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ExperienceImageInline]
    list_select_related = ("host",)
    actions = [approve_experiences, reject_experiences] + moderation_actions


@admin.register(Booking)
class BookingAdmin(ModelAdmin):
    list_display = (
        "experience",
        "traveler_name",
        "check_in_date",
        "check_out_date",
        "booking_status",
        "created_at",
    )
    list_filter = ("booking_status", "created_at")
    search_fields = ("experience__title", "user__username", "traveler_name")
    readonly_fields = ("created_at",)
    list_select_related = ("experience", "user")


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ("experience", "rating", "reviewer", "host", "is_flagged", "is_hidden", "created_at")
    list_filter = ("rating", "is_flagged", "is_hidden", "created_at")
    search_fields = ("experience__title", "reviewer__username", "host__username", "comment")
    readonly_fields = ("created_at",)
    list_select_related = ("experience", "reviewer", "host")
    actions = moderation_actions

@admin.register(Message)
class MessageAdmin(ModelAdmin):
    list_display = ("sender", "conversation", "is_flagged", "is_hidden", "created_at")
    list_filter = ("is_flagged", "is_hidden", "created_at")
    search_fields = ("text", "sender__username")
    actions = moderation_actions

@admin.action(description="Delete selected flagged reviews")
def delete_flagged_reviews(modeladmin, request, queryset):
    count = 0
    for report in queryset:
        if report.review:
            report.review.delete()
            count += 1
    modeladmin.message_user(request, f"{count} underlying review(s) deleted.")

@admin.register(ReviewReport)
class ReviewReportAdmin(ModelAdmin):
    list_display = ("review", "reporter", "created_at")
    search_fields = ("review__comment", "reporter__username", "reason")
    actions = [delete_flagged_reviews]
    list_select_related = ("review", "reporter")


@admin.register(HostRequest)
class HostRequestAdmin(ModelAdmin):
    list_display = ("user", "phone_number", "is_approved", "created_at")
    list_filter = ("is_approved", "created_at")
    search_fields = ("user__username", "user__email", "phone_number")
    actions = ["approve_requests"]
    list_select_related = ("user",)

    def approve_requests(self, request, queryset):
        approved_count = 0
        for req in queryset:
            if not req.is_approved:
                req.is_approved = True
                req.save(update_fields=["is_approved"])
                approved_count += 1

            profile = getattr(req.user, "userprofile", None)
            if profile:
                profile.is_host = True
                profile.save(update_fields=["is_host"])

        self.message_user(
            request,
            f"{approved_count} host request(s) approved and users marked as hosts."
        )

    approve_requests.short_description = "Approve selected host requests"


@admin.register(HostVerification)
class HostVerificationAdmin(ModelAdmin):
    list_display = ("user", "verified")
    list_filter = ("verified",)
    search_fields = ("user__username", "user__email")
    actions = ["approve_verifications"]
    list_select_related = ("user",)
    
    def approve_verifications(self, request, queryset):
        approved_count = 0
        for verification in queryset:
            if not verification.verified:
                verification.verified = True
                verification.save(update_fields=["verified"])
                approved_count += 1
                
                profile = getattr(verification.user, "userprofile", None)
                if profile:
                    profile.is_host = True
                    profile.save(update_fields=["is_host"])
                    
        self.message_user(
            request,
            f"{approved_count} host verification(s) approved and users updated to hosts."
        )
        
    approve_verifications.short_description = "Approve selected host verifications"


@admin.register(HeroSlide)
class HeroSlideAdmin(ModelAdmin):
    list_display = (
        "sort_order",
        "title",
        "media_type",
        "is_active",
        "show_search_card",
        "show_trust_chips",
        "interval_ms",
    )
    list_display_links = ("title",)  # fix admin.E124
    list_editable = (
        "sort_order",
        "is_active",
        "show_search_card",
        "show_trust_chips",
        "interval_ms",
    )
    list_filter = ("is_active", "media_type", "show_search_card", "show_trust_chips")
    search_fields = ("title", "subtitle", "badge_text")
    ordering = ("sort_order", "id")

    fieldsets = (
        ("Content", {
            "fields": ("title", "subtitle", "badge_text", "badge_icon")
        }),
        ("Media", {
            "fields": ("media_type", "image", "video", "video_poster")
        }),
        ("Buttons (CTA)", {
            "fields": (
                ("cta_primary_label", "cta_primary_url"),
                ("cta_secondary_label", "cta_secondary_url"),
            )
        }),
        ("Display & Behavior", {
            "fields": (
                ("interval_ms", "sort_order"),
                ("overlay_opacity_top", "overlay_opacity_bottom"),
                ("show_search_card", "show_trust_chips"),
                "is_active",
            )
        }),
    )
