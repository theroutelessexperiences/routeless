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
    HostApplication,
    ListingDocument,
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
        "host",
        "category",
        "location",
        "price_per_person",
        "max_guests",
        "listing_status",
        "status",
        "is_active",
        "is_featured",
        "created_at",
        "submitted_at",
    )
    list_filter = (
        "listing_status",
        "status",
        "category",
        "is_active",
        "is_featured",
        "is_flagged",
        "is_hidden",
        "location",
    )
    search_fields = (
        "title",
        "location",
        "host__username",
        "host__email",
        "host__first_name",
        "host__last_name",
        "category",
    )
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ExperienceImageInline]
    list_select_related = ("host",)
    readonly_fields = ("created_at", "updated_at", "submitted_at")
    ordering = ("-created_at",)

    fieldsets = (
        ("Basic Info", {
            "fields": (
                "title", "slug", "category", "location", "location_fk",
                "host", "short_description", "description",
                "experience_highlights",
            ),
        }),
        ("Pricing & Capacity", {
            "fields": (
                "price_per_person", "max_guests", "duration",
            ),
        }),
        ("Included / Excluded", {
            "fields": ("what_is_included", "what_is_not_included", "amenities"),
            "classes": ("collapse",),
        }),
        ("Category Details (JSON)", {
            "fields": ("category_details",),
            "classes": ("collapse",),
        }),
        ("Listing Workflow", {
            "fields": (
                "listing_status", "status",
                "is_active", "is_featured",
                "cancellation_policy_accepted", "listing_declaration_accepted",
                "admin_notes",
                "submitted_at", "created_at", "updated_at",
            ),
        }),
        ("Moderation", {
            "fields": ("is_flagged", "is_hidden", "moderation_reason"),
            "classes": ("collapse",),
        }),
    )

    actions = [
        approve_experiences, reject_experiences,
        "mark_listing_approved",
        "mark_listing_rejected",
        "mark_listing_more_info",
        "mark_listing_paused",
        "mark_listing_doc_expired",
        "feature_listings",
        "unfeature_listings",
    ] + moderation_actions

    @admin.action(description="✅ Approve listing (set active)")
    def mark_listing_approved(self, request, queryset):
        count = queryset.update(
            listing_status=Experience.ListingStatus.APPROVED,
            is_active=True,
        )
        self.message_user(request, f"{count} listing(s) approved and activated.")

    @admin.action(description="❌ Reject listing")
    def mark_listing_rejected(self, request, queryset):
        count = queryset.update(
            listing_status=Experience.ListingStatus.REJECTED,
            is_active=False,
        )
        self.message_user(request, f"{count} listing(s) rejected.")

    @admin.action(description="ℹ️ Request more info")
    def mark_listing_more_info(self, request, queryset):
        count = queryset.update(
            listing_status=Experience.ListingStatus.MORE_INFO,
        )
        self.message_user(request, f"{count} listing(s) marked as needing more info.")

    @admin.action(description="⏸️ Pause listing")
    def mark_listing_paused(self, request, queryset):
        count = queryset.update(
            listing_status=Experience.ListingStatus.PAUSED,
            is_active=False,
        )
        self.message_user(request, f"{count} listing(s) paused.")

    @admin.action(description="📄 Mark documents expired")
    def mark_listing_doc_expired(self, request, queryset):
        count = queryset.update(
            listing_status=Experience.ListingStatus.DOC_EXPIRED,
            is_active=False,
        )
        self.message_user(request, f"{count} listing(s) marked with expired documents.")

    @admin.action(description="⭐ Feature listings")
    def feature_listings(self, request, queryset):
        count = queryset.update(is_featured=True)
        self.message_user(request, f"{count} listing(s) featured.")

    @admin.action(description="Remove from featured")
    def unfeature_listings(self, request, queryset):
        count = queryset.update(is_featured=False)
        self.message_user(request, f"{count} listing(s) unfeatured.")


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


# -------------------------------------------------------------------
# Host Application Admin (new multi-step flow)
# -------------------------------------------------------------------
@admin.register(HostApplication)
class HostApplicationAdmin(ModelAdmin):
    list_display = (
        "full_name_or_company_name",
        "host_type",
        "mobile_number",
        "city",
        "state",
        "verification_status",
        "submitted_at",
        "police_verification_issue_date",
    )
    list_filter = ("host_type", "verification_status", "state")
    search_fields = (
        "full_name_or_company_name",
        "mobile_number",
        "email",
        "pan_number",
        "gst_number",
    )
    readonly_fields = ("created_at", "updated_at", "submitted_at")
    list_select_related = ("user",)
    ordering = ("-submitted_at", "-created_at")

    fieldsets = (
        ("Host Details (Step 1)", {
            "fields": (
                "user",
                "host_type",
                "full_name_or_company_name",
                "mobile_number",
                "email",
                "city",
                "state",
                "host_bio",
                "profile_photo_or_logo",
            ),
        }),
        ("Verification (Step 2)", {
            "fields": (
                "pan_number",
                "government_id_proof",
                "police_verification_certificate",
                "police_verification_issue_date",
                "bank_account_holder_name",
                "bank_name",
                "account_number",
                "ifsc_code",
            ),
        }),
        ("Business Details (Step 3 — Company Only)", {
            "fields": (
                "gst_number",
                "msme_udyam_number",
                "authorized_person_name",
                "business_address",
            ),
            "classes": ("collapse",),
        }),
        ("Declaration (Step 4)", {
            "fields": ("declaration_accepted",),
        }),
        ("Status & Admin", {
            "fields": (
                "verification_status",
                "admin_notes",
                "submitted_at",
                "created_at",
                "updated_at",
            ),
        }),
    )

    actions = [
        "mark_verified",
        "mark_rejected",
        "mark_suspended",
        "mark_more_info",
        "mark_doc_expired",
    ]

    @admin.action(description="Mark as Verified (activate host)")
    def mark_verified(self, request, queryset):
        count = 0
        for app in queryset:
            app.verification_status = HostApplication.VerificationStatus.VERIFIED
            app.save(update_fields=["verification_status"])
            count += 1
            # Activate host in UserProfile
            profile = getattr(app.user, "userprofile", None)
            if profile:
                profile.is_host = True
                profile.save(update_fields=["is_host"])
        self.message_user(request, f"{count} application(s) verified and host accounts activated.")

    @admin.action(description="Mark as Rejected")
    def mark_rejected(self, request, queryset):
        count = queryset.update(
            verification_status=HostApplication.VerificationStatus.REJECTED
        )
        self.message_user(request, f"{count} application(s) rejected.")

    @admin.action(description="Mark as Suspended")
    def mark_suspended(self, request, queryset):
        count = 0
        for app in queryset:
            app.verification_status = HostApplication.VerificationStatus.SUSPENDED
            app.save(update_fields=["verification_status"])
            count += 1
            # Deactivate host in UserProfile
            profile = getattr(app.user, "userprofile", None)
            if profile and profile.is_host:
                profile.is_host = False
                profile.save(update_fields=["is_host"])
        self.message_user(request, f"{count} application(s) suspended.")

    @admin.action(description="Mark as More Info Required")
    def mark_more_info(self, request, queryset):
        count = queryset.update(
            verification_status=HostApplication.VerificationStatus.MORE_INFO
        )
        self.message_user(request, f"{count} application(s) marked as needing more info.")

    @admin.action(description="Mark as Document Expired")
    def mark_doc_expired(self, request, queryset):
        count = queryset.update(
            verification_status=HostApplication.VerificationStatus.DOC_EXPIRED
        )
        self.message_user(request, f"{count} application(s) marked with expired documents.")


@admin.register(ListingDocument)
class ListingDocumentAdmin(ModelAdmin):
    list_display = ("experience", "document_type", "uploaded_at")
    list_filter = ("document_type",)
    search_fields = ("experience__title",)
    list_select_related = ("experience",)


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
