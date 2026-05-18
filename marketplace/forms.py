from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Experience, Booking, UserProfile


from decimal import Decimal
from datetime import time
import json

from django import forms
from django.utils.text import slugify

from .models import Experience


# ---------------------------------------------------------
# Reusable choices
# ---------------------------------------------------------
YES_NO_CHOICES = [
    ("", "Select"),
    ("Yes", "Yes"),
    ("No", "No"),
]

YES_NO_OPTIONAL_CHOICES = [
    ("", "Not specified"),
    ("Yes", "Yes"),
    ("No", "No"),
]

DIFFICULTY_CHOICES = [
    ("", "Select difficulty"),
    ("Easy", "Easy"),
    ("Moderate", "Moderate"),
    ("Hard", "Hard"),
    ("Expert", "Expert"),
]

FITNESS_LEVEL_CHOICES = [
    ("", "Select fitness level"),
    ("Beginner", "Beginner"),
    ("Basic Fitness", "Basic Fitness"),
    ("Intermediate", "Intermediate"),
    ("Advanced", "Advanced"),
]

RISK_LEVEL_CHOICES = [
    ("", "Select risk level"),
    ("Low", "Low"),
    ("Medium", "Medium"),
    ("High", "High"),
]

ROOM_TYPE_CHOICES = [
    ("", "Select room type"),
    ("Private Room", "Private Room"),
    ("Shared Room", "Shared Room"),
    ("Entire Home", "Entire Home"),
    ("Dorm Bed", "Dorm Bed"),
]

MEAL_PLAN_CHOICES = [
    ("", "Select meal plan"),
    ("No Meals", "No Meals"),
    ("Breakfast Only", "Breakfast Only"),
    ("Breakfast + Dinner", "Breakfast + Dinner"),
    ("All Meals Included", "All Meals Included"),
    ("Optional Meals", "Optional Meals"),
]

TREK_TYPE_CHOICES = [
    ("", "Select trek type"),
    ("Day Trek", "Day Trek"),
    ("Weekend Trek", "Weekend Trek"),
    ("Multi-day Trek", "Multi-day Trek"),
    ("Expedition", "Expedition"),
]

TRAIL_TYPE_CHOICES = [
    ("", "Select trail type"),
    ("Forest Trail", "Forest Trail"),
    ("Rocky Trail", "Rocky Trail"),
    ("Snow Trail", "Snow Trail"),
    ("Mixed Terrain", "Mixed Terrain"),
    ("Pilgrimage Route", "Pilgrimage Route"),
]

ADVENTURE_ACTIVITY_CHOICES = [
    ("", "Select activity"),
    ("River Rafting", "River Rafting"),
    ("Zipline", "Zipline"),
    ("Bungee Jumping", "Bungee Jumping"),
    ("Paragliding", "Paragliding"),
    ("Rock Climbing", "Rock Climbing"),
    ("Camping", "Camping"),
    ("ATV Ride", "ATV Ride"),
    ("Kayaking", "Kayaking"),
    ("Caving", "Caving"),
    ("Other", "Other"),
]

SPIRITUAL_PLACE_CHOICES = [
    ("", "Select place type"),
    ("Temple", "Temple"),
    ("Ashram", "Ashram"),
    ("Monastery", "Monastery"),
    ("Retreat Center", "Retreat Center"),
    ("Pilgrimage Trail", "Pilgrimage Trail"),
    ("Meditation Center", "Meditation Center"),
    ("Other", "Other"),
]

WILDLIFE_SAFARI_CHOICES = [
    ("", "Select safari type"),
    ("Jeep Safari", "Jeep Safari"),
    ("Canter Safari", "Canter Safari"),
    ("Boat Safari", "Boat Safari"),
    ("Walking Trail", "Walking Trail"),
    ("Birding Tour", "Birding Tour"),
    ("Night Safari", "Night Safari"),
    ("Other", "Other"),
]

CULTURAL_FORMAT_CHOICES = [
    ("", "Select format"),
    ("Guided Walk", "Guided Walk"),
    ("Workshop", "Workshop"),
    ("Performance", "Performance"),
    ("Food Experience", "Food Experience"),
    ("Heritage Tour", "Heritage Tour"),
    ("Village Experience", "Village Experience"),
    ("Festival Experience", "Festival Experience"),
    ("Other", "Other"),
]

LANGUAGE_LEVEL_CHOICES = [
    ("", "Select"),
    ("Hindi Only", "Hindi Only"),
    ("English + Hindi", "English + Hindi"),
    ("Local Language + Hindi", "Local Language + Hindi"),
    ("Multilingual", "Multilingual"),
]


# ---------------------------------------------------------
# Category schemas (field names + required fields)
# ---------------------------------------------------------
CATEGORY_FIELD_SETS = {
    "Trek": {
        "fields": [
            "trek_type",
            "trek_difficulty",
            "trek_duration_days",
            "trek_duration_hours",
            "trek_distance_km",
            "trek_max_altitude_m",
            "trek_altitude_gain_m",
            "trek_fitness_level",
            "trek_trail_type",
            "trek_terrain_notes",
            "trek_group_size_min",
            "trek_group_size_max",
            "trek_guide_included",
            "trek_porter_available",
            "trek_meals_included",
            "trek_stay_type",
            "trek_permit_required",
            "trek_permit_included",
            "trek_pickup_available",
            "trek_reporting_point",
            "trek_reporting_time",
            "trek_start_point",
            "trek_end_point",
            "trek_best_season",
            "trek_what_to_carry",
            "trek_medical_restrictions",
        ],
        "required": [
            "trek_type",
            "trek_difficulty",
            "trek_duration_hours",
            "trek_distance_km",
            "trek_fitness_level",
            "trek_guide_included",
        ],
    },
    "Homestay": {
        "fields": [
            "home_room_type",
            "home_bed_type",
            "home_rooms_available",
            "home_private_bathroom",
            "home_attached_bathroom",
            "home_checkin_time",
            "home_checkout_time",
            "home_meal_plan",
            "home_wifi",
            "home_parking",
            "home_hot_water",
            "home_heating",
            "home_air_conditioning",
            "home_power_backup",
            "home_kitchen_access",
            "home_pets_allowed",
            "home_family_friendly",
            "home_smoking_allowed",
            "home_mountain_view",
            "home_work_friendly",
            "home_languages_supported",
            "home_house_rules",
            "home_nearby_attractions",
            "home_host_contact_window",
        ],
        "required": [
            "home_room_type",
            "home_rooms_available",
            "home_checkin_time",
            "home_checkout_time",
            "home_meal_plan",
            "home_wifi",
        ],
    },
    "Adventure": {
        "fields": [
            "adv_activity_type",
            "adv_activity_custom_name",
            "adv_difficulty",
            "adv_duration_hours",
            "adv_risk_level",
            "adv_min_age",
            "adv_max_age",
            "adv_min_weight_kg",
            "adv_max_weight_kg",
            "adv_min_height_cm",
            "adv_max_height_cm",
            "adv_group_size_min",
            "adv_group_size_max",
            "adv_safety_gear_included",
            "adv_instructor_certified",
            "adv_safety_briefing_minutes",
            "adv_medical_declaration_required",
            "adv_permit_required",
            "adv_permit_included",
            "adv_insurance_included",
            "adv_weather_dependent",
            "adv_pickup_available",
            "adv_reporting_point",
            "adv_reporting_time",
            "adv_batch_slots",
            "adv_restrictions_notes",
        ],
        "required": [
            "adv_activity_type",
            "adv_difficulty",
            "adv_duration_hours",
            "adv_risk_level",
            "adv_safety_gear_included",
            "adv_instructor_certified",
        ],
    },
    "Spiritual": {
        "fields": [
            "spi_place_type",
            "spi_place_name",
            "spi_experience_type",
            "spi_duration_hours",
            "spi_best_time_to_visit",
            "spi_dress_code_required",
            "spi_dress_code_notes",
            "spi_pooja_included",
            "spi_meditation_session",
            "spi_yoga_session",
            "spi_satsang_included",
            "spi_prasadam_included",
            "spi_donation_included",
            "spi_queue_assistance",
            "spi_wheelchair_access",
            "spi_senior_citizen_friendly",
            "spi_family_friendly",
            "spi_photography_allowed",
            "spi_language_support",
            "spi_reporting_time",
            "spi_meeting_point",
            "spi_special_instructions",
        ],
        "required": [
            "spi_place_type",
            "spi_place_name",
            "spi_duration_hours",
            "spi_best_time_to_visit",
            "spi_language_support",
        ],
    },
    "Wildlife": {
        "fields": [
            "wild_safari_type",
            "wild_park_name",
            "wild_zone_name",
            "wild_duration_hours",
            "wild_best_time_to_visit",
            "wild_permit_required",
            "wild_permit_included",
            "wild_entry_fee_included",
            "wild_vehicle_type",
            "wild_naturalist_included",
            "wild_guide_included",
            "wild_binoculars_included",
            "wild_camera_fee_extra",
            "wild_min_age",
            "wild_group_size_min",
            "wild_group_size_max",
            "wild_pickup_available",
            "wild_reporting_point",
            "wild_reporting_time",
            "wild_sighting_focus",
            "wild_do_donts",
        ],
        "required": [
            "wild_safari_type",
            "wild_park_name",
            "wild_duration_hours",
            "wild_best_time_to_visit",
            "wild_permit_required",
            "wild_guide_included",
        ],
    },
    "Cultural": {
        "fields": [
            "cul_format",
            "cul_theme",
            "cul_duration_hours",
            "cul_language_support",
            "cul_group_size_min",
            "cul_group_size_max",
            "cul_materials_included",
            "cul_meal_or_snacks_included",
            "cul_local_community_led",
            "cul_indoor_outdoor",
            "cul_family_friendly",
            "cul_kid_friendly",
            "cul_photography_allowed",
            "cul_wheelchair_access",
            "cul_takeaway_items_included",
            "cul_dress_code",
            "cul_meeting_point",
            "cul_reporting_time",
            "cul_special_notes",
        ],
        "required": [
            "cul_format",
            "cul_theme",
            "cul_duration_hours",
            "cul_language_support",
        ],
    },
}


ALL_DETAIL_FIELDS = sorted(
    {fname for cfg in CATEGORY_FIELD_SETS.values() for fname in cfg["fields"]}
)


# ---------------------------------------------------------
# Human-readable labels for every category field
# ---------------------------------------------------------
FIELD_LABELS = {
    # Trek
    "trek_type": "Trek type",
    "trek_difficulty": "Difficulty level",
    "trek_duration_days": "Duration (days)",
    "trek_duration_hours": "Duration (hours)",
    "trek_distance_km": "Distance (km)",
    "trek_max_altitude_m": "Maximum altitude (meters)",
    "trek_altitude_gain_m": "Altitude gain (meters)",
    "trek_fitness_level": "Fitness level",
    "trek_trail_type": "Trail type",
    "trek_terrain_notes": "Terrain notes",
    "trek_group_size_min": "Minimum group size",
    "trek_group_size_max": "Maximum group size",
    "trek_guide_included": "Guide included",
    "trek_porter_available": "Porter available",
    "trek_meals_included": "Meals included",
    "trek_stay_type": "Stay type",
    "trek_permit_required": "Permit required",
    "trek_permit_included": "Permit included",
    "trek_pickup_available": "Pickup available",
    "trek_reporting_point": "Reporting point",
    "trek_reporting_time": "Reporting time",
    "trek_start_point": "Start point",
    "trek_end_point": "End point",
    "trek_best_season": "Best season",
    "trek_what_to_carry": "What to carry",
    "trek_medical_restrictions": "Medical restrictions",
    # Homestay
    "home_room_type": "Room type",
    "home_bed_type": "Bed type",
    "home_rooms_available": "Rooms available",
    "home_private_bathroom": "Private bathroom",
    "home_attached_bathroom": "Attached bathroom",
    "home_checkin_time": "Check-in time",
    "home_checkout_time": "Check-out time",
    "home_meal_plan": "Meal plan",
    "home_wifi": "WiFi available",
    "home_parking": "Parking available",
    "home_hot_water": "Hot water",
    "home_heating": "Heating",
    "home_air_conditioning": "Air conditioning",
    "home_power_backup": "Power backup",
    "home_kitchen_access": "Kitchen access",
    "home_pets_allowed": "Pets allowed",
    "home_family_friendly": "Family friendly",
    "home_smoking_allowed": "Smoking allowed",
    "home_mountain_view": "Mountain view",
    "home_work_friendly": "Work friendly",
    "home_languages_supported": "Languages supported",
    "home_house_rules": "House rules",
    "home_nearby_attractions": "Nearby attractions",
    "home_host_contact_window": "Host contact window",
    # Adventure
    "adv_activity_type": "Activity type",
    "adv_activity_custom_name": "Custom activity name",
    "adv_difficulty": "Difficulty level",
    "adv_duration_hours": "Duration (hours)",
    "adv_risk_level": "Risk level",
    "adv_min_age": "Minimum age",
    "adv_max_age": "Maximum age",
    "adv_min_weight_kg": "Minimum weight (kg)",
    "adv_max_weight_kg": "Maximum weight (kg)",
    "adv_min_height_cm": "Minimum height (cm)",
    "adv_max_height_cm": "Maximum height (cm)",
    "adv_group_size_min": "Minimum group size",
    "adv_group_size_max": "Maximum group size",
    "adv_safety_gear_included": "Safety gear included",
    "adv_instructor_certified": "Instructor certified",
    "adv_safety_briefing_minutes": "Safety briefing duration (minutes)",
    "adv_medical_declaration_required": "Medical declaration required",
    "adv_permit_required": "Permit required",
    "adv_permit_included": "Permit included",
    "adv_insurance_included": "Insurance included",
    "adv_weather_dependent": "Weather dependent",
    "adv_pickup_available": "Pickup available",
    "adv_reporting_point": "Reporting point",
    "adv_reporting_time": "Reporting time",
    "adv_batch_slots": "Batch slots",
    "adv_restrictions_notes": "Restrictions and notes",
    # Spiritual
    "spi_place_type": "Place type",
    "spi_place_name": "Place name",
    "spi_experience_type": "Experience type",
    "spi_duration_hours": "Duration (hours)",
    "spi_best_time_to_visit": "Best time to visit",
    "spi_dress_code_required": "Dress code required",
    "spi_dress_code_notes": "Dress code notes",
    "spi_pooja_included": "Pooja included",
    "spi_meditation_session": "Meditation session",
    "spi_yoga_session": "Yoga session",
    "spi_satsang_included": "Satsang included",
    "spi_prasadam_included": "Prasadam included",
    "spi_donation_included": "Donation included",
    "spi_queue_assistance": "Queue assistance",
    "spi_wheelchair_access": "Wheelchair accessible",
    "spi_senior_citizen_friendly": "Senior citizen friendly",
    "spi_family_friendly": "Family friendly",
    "spi_photography_allowed": "Photography allowed",
    "spi_language_support": "Language support",
    "spi_reporting_time": "Reporting time",
    "spi_meeting_point": "Meeting point",
    "spi_special_instructions": "Special instructions",
    # Wildlife
    "wild_safari_type": "Safari type",
    "wild_park_name": "Park / sanctuary name",
    "wild_zone_name": "Zone name",
    "wild_duration_hours": "Duration (hours)",
    "wild_best_time_to_visit": "Best time to visit",
    "wild_permit_required": "Permit required",
    "wild_permit_included": "Permit included",
    "wild_entry_fee_included": "Entry fee included",
    "wild_vehicle_type": "Vehicle type",
    "wild_naturalist_included": "Naturalist included",
    "wild_guide_included": "Guide included",
    "wild_binoculars_included": "Binoculars included",
    "wild_camera_fee_extra": "Camera fee extra",
    "wild_min_age": "Minimum age",
    "wild_group_size_min": "Minimum group size",
    "wild_group_size_max": "Maximum group size",
    "wild_pickup_available": "Pickup available",
    "wild_reporting_point": "Reporting point",
    "wild_reporting_time": "Reporting time",
    "wild_sighting_focus": "Sighting focus",
    "wild_do_donts": "Do's and Don'ts",
    # Cultural
    "cul_format": "Format",
    "cul_theme": "Theme",
    "cul_duration_hours": "Duration (hours)",
    "cul_language_support": "Language support",
    "cul_group_size_min": "Minimum group size",
    "cul_group_size_max": "Maximum group size",
    "cul_materials_included": "Materials included",
    "cul_meal_or_snacks_included": "Meal or snacks included",
    "cul_local_community_led": "Local community led",
    "cul_indoor_outdoor": "Indoor / Outdoor",
    "cul_family_friendly": "Family friendly",
    "cul_kid_friendly": "Kid friendly",
    "cul_photography_allowed": "Photography allowed",
    "cul_wheelchair_access": "Wheelchair accessible",
    "cul_takeaway_items_included": "Takeaway items included",
    "cul_dress_code": "Dress code",
    "cul_meeting_point": "Meeting point",
    "cul_reporting_time": "Reporting time",
    "cul_special_notes": "Special notes",
    # Common fields
    "experience_start_date": "Start date",
    "experience_start_time": "Start time",
    "experience_end_time": "End time",
    "experience_available_days": "Available days",
    "experience_booking_cutoff_hours": "Booking cutoff (hours before)",
    "pickup_included": "Pickup included",
    "pickup_point": "Pickup point",
    "drop_point": "Drop point",
    "pickup_drop_extra_charge": "Pickup/drop extra charge (₹)",
    "porter_available": "Porter available",
    "porter_included_in_price": "Porter included in price",
    "porter_extra_charge": "Porter extra charge (₹)",
    "baggage_loading_included": "Baggage loading/unloading included",
    "baggage_loading_charge": "Baggage loading/unloading charge (₹)",
    "max_baggage_kg": "Maximum baggage allowed (kg)",
}

DAY_CHOICES = [
    ("Monday", "Monday"),
    ("Tuesday", "Tuesday"),
    ("Wednesday", "Wednesday"),
    ("Thursday", "Thursday"),
    ("Friday", "Friday"),
    ("Saturday", "Saturday"),
    ("Sunday", "Sunday"),
]

COMMON_DETAIL_FIELDS = [
    "experience_start_date",
    "experience_start_time",
    "experience_end_time",
    "experience_available_days",
    "experience_booking_cutoff_hours",
    "pickup_included",
    "pickup_point",
    "drop_point",
    "pickup_drop_extra_charge",
    "porter_available",
    "porter_included_in_price",
    "porter_extra_charge",
    "baggage_loading_included",
    "baggage_loading_charge",
    "max_baggage_kg",
]


# ---------------------------------------------------------
# Form
# ---------------------------------------------------------
class ExperienceForm(forms.ModelForm):
    """
    Detailed category-aware form.
    Saves category-specific inputs into Experience.category_details (JSONField).
    """

    # -------------------------
    # Trek fields
    # -------------------------
    trek_type = forms.ChoiceField(choices=TREK_TYPE_CHOICES, required=False)
    trek_difficulty = forms.ChoiceField(choices=DIFFICULTY_CHOICES, required=False)
    trek_duration_days = forms.DecimalField(required=False, min_value=0, decimal_places=1, max_digits=6)
    trek_duration_hours = forms.DecimalField(required=False, min_value=0, decimal_places=1, max_digits=6)
    trek_distance_km = forms.DecimalField(required=False, min_value=0, decimal_places=1, max_digits=8)
    trek_max_altitude_m = forms.IntegerField(required=False, min_value=0)
    trek_altitude_gain_m = forms.IntegerField(required=False, min_value=0)
    trek_fitness_level = forms.ChoiceField(choices=FITNESS_LEVEL_CHOICES, required=False)
    trek_trail_type = forms.ChoiceField(choices=TRAIL_TYPE_CHOICES, required=False)
    trek_terrain_notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    trek_group_size_min = forms.IntegerField(required=False, min_value=1)
    trek_group_size_max = forms.IntegerField(required=False, min_value=1)
    trek_guide_included = forms.ChoiceField(choices=YES_NO_CHOICES, required=False)
    trek_porter_available = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    trek_meals_included = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    trek_stay_type = forms.CharField(required=False)
    trek_permit_required = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    trek_permit_included = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    trek_pickup_available = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    trek_reporting_point = forms.CharField(required=False)
    trek_reporting_time = forms.TimeField(required=False, widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}))
    trek_start_point = forms.CharField(required=False)
    trek_end_point = forms.CharField(required=False)
    trek_best_season = forms.CharField(required=False, help_text="e.g. Mar-Jun, Sep-Nov")
    trek_what_to_carry = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    trek_medical_restrictions = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))

    # -------------------------
    # Homestay fields
    # -------------------------
    home_room_type = forms.ChoiceField(choices=ROOM_TYPE_CHOICES, required=False)
    home_bed_type = forms.CharField(required=False)
    home_rooms_available = forms.IntegerField(required=False, min_value=1)
    home_private_bathroom = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    home_attached_bathroom = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    home_checkin_time = forms.TimeField(required=False, widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}))
    home_checkout_time = forms.TimeField(required=False, widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}))
    home_meal_plan = forms.ChoiceField(choices=MEAL_PLAN_CHOICES, required=False)
    home_wifi = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    home_parking = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    home_hot_water = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    home_heating = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    home_air_conditioning = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    home_power_backup = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    home_kitchen_access = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    home_pets_allowed = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    home_family_friendly = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    home_smoking_allowed = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    home_mountain_view = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    home_work_friendly = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    home_languages_supported = forms.ChoiceField(choices=LANGUAGE_LEVEL_CHOICES, required=False)
    home_house_rules = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    home_nearby_attractions = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    home_host_contact_window = forms.CharField(required=False, help_text="e.g. 8 AM - 10 PM")

    # -------------------------
    # Adventure fields
    # -------------------------
    adv_activity_type = forms.ChoiceField(choices=ADVENTURE_ACTIVITY_CHOICES, required=False)
    adv_activity_custom_name = forms.CharField(required=False)
    adv_difficulty = forms.ChoiceField(choices=DIFFICULTY_CHOICES, required=False)
    adv_duration_hours = forms.DecimalField(required=False, min_value=0, decimal_places=1, max_digits=6)
    adv_risk_level = forms.ChoiceField(choices=RISK_LEVEL_CHOICES, required=False)
    adv_min_age = forms.IntegerField(required=False, min_value=0)
    adv_max_age = forms.IntegerField(required=False, min_value=0)
    adv_min_weight_kg = forms.DecimalField(required=False, min_value=0, decimal_places=1, max_digits=6)
    adv_max_weight_kg = forms.DecimalField(required=False, min_value=0, decimal_places=1, max_digits=6)
    adv_min_height_cm = forms.DecimalField(required=False, min_value=0, decimal_places=1, max_digits=6)
    adv_max_height_cm = forms.DecimalField(required=False, min_value=0, decimal_places=1, max_digits=6)
    adv_group_size_min = forms.IntegerField(required=False, min_value=1)
    adv_group_size_max = forms.IntegerField(required=False, min_value=1)
    adv_safety_gear_included = forms.ChoiceField(choices=YES_NO_CHOICES, required=False)
    adv_instructor_certified = forms.ChoiceField(choices=YES_NO_CHOICES, required=False)
    adv_safety_briefing_minutes = forms.IntegerField(required=False, min_value=0)
    adv_medical_declaration_required = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    adv_permit_required = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    adv_permit_included = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    adv_insurance_included = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    adv_weather_dependent = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    adv_pickup_available = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    adv_reporting_point = forms.CharField(required=False)
    adv_reporting_time = forms.TimeField(required=False, widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}))
    adv_batch_slots = forms.CharField(required=False, help_text="e.g. 9 AM, 11 AM, 2 PM")
    adv_restrictions_notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    # -------------------------
    # Spiritual fields
    # -------------------------
    spi_place_type = forms.ChoiceField(choices=SPIRITUAL_PLACE_CHOICES, required=False)
    spi_place_name = forms.CharField(required=False)
    spi_experience_type = forms.CharField(required=False, help_text="e.g. Darshan, Aarti, Meditation, Retreat")
    spi_duration_hours = forms.DecimalField(required=False, min_value=0, decimal_places=1, max_digits=6)
    spi_best_time_to_visit = forms.CharField(required=False)
    spi_dress_code_required = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    spi_dress_code_notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    spi_pooja_included = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    spi_meditation_session = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    spi_yoga_session = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    spi_satsang_included = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    spi_prasadam_included = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    spi_donation_included = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    spi_queue_assistance = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    spi_wheelchair_access = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    spi_senior_citizen_friendly = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    spi_family_friendly = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    spi_photography_allowed = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    spi_language_support = forms.ChoiceField(choices=LANGUAGE_LEVEL_CHOICES, required=False)
    spi_reporting_time = forms.TimeField(required=False, widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}))
    spi_meeting_point = forms.CharField(required=False)
    spi_special_instructions = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    # -------------------------
    # Wildlife fields
    # -------------------------
    wild_safari_type = forms.ChoiceField(choices=WILDLIFE_SAFARI_CHOICES, required=False)
    wild_park_name = forms.CharField(required=False)
    wild_zone_name = forms.CharField(required=False)
    wild_duration_hours = forms.DecimalField(required=False, min_value=0, decimal_places=1, max_digits=6)
    wild_best_time_to_visit = forms.CharField(required=False)
    wild_permit_required = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    wild_permit_included = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    wild_entry_fee_included = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    wild_vehicle_type = forms.CharField(required=False, help_text="e.g. Jeep, Canter, Boat")
    wild_naturalist_included = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    wild_guide_included = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    wild_binoculars_included = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    wild_camera_fee_extra = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    wild_min_age = forms.IntegerField(required=False, min_value=0)
    wild_group_size_min = forms.IntegerField(required=False, min_value=1)
    wild_group_size_max = forms.IntegerField(required=False, min_value=1)
    wild_pickup_available = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    wild_reporting_point = forms.CharField(required=False)
    wild_reporting_time = forms.TimeField(required=False, widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}))
    wild_sighting_focus = forms.CharField(required=False, help_text="e.g. Tiger, Birds, Elephant", widget=forms.Textarea(attrs={"rows": 2}))
    wild_do_donts = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    # -------------------------
    # Cultural fields
    # -------------------------
    cul_format = forms.ChoiceField(choices=CULTURAL_FORMAT_CHOICES, required=False)
    cul_theme = forms.CharField(required=False, help_text="e.g. Folk Music, Handloom, Local Cuisine, Heritage")
    cul_duration_hours = forms.DecimalField(required=False, min_value=0, decimal_places=1, max_digits=6)
    cul_language_support = forms.ChoiceField(choices=LANGUAGE_LEVEL_CHOICES, required=False)
    cul_group_size_min = forms.IntegerField(required=False, min_value=1)
    cul_group_size_max = forms.IntegerField(required=False, min_value=1)
    cul_materials_included = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    cul_meal_or_snacks_included = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    cul_local_community_led = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    cul_indoor_outdoor = forms.ChoiceField(
        choices=[("", "Select"), ("Indoor", "Indoor"), ("Outdoor", "Outdoor"), ("Both", "Both")],
        required=False,
    )
    cul_family_friendly = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    cul_kid_friendly = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    cul_photography_allowed = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    cul_wheelchair_access = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    cul_takeaway_items_included = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    cul_dress_code = forms.CharField(required=False)
    cul_meeting_point = forms.CharField(required=False)
    cul_reporting_time = forms.TimeField(required=False, widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}))
    cul_special_notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    # -------------------------
    # Common: Schedule & Availability
    # -------------------------
    experience_start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    experience_start_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
    )
    experience_end_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
    )
    experience_available_days = forms.MultipleChoiceField(
        choices=DAY_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select the days this experience is available.",
    )
    experience_booking_cutoff_hours = forms.IntegerField(
        required=False, min_value=0,
        help_text="How many hours before the start time should bookings close?",
    )

    # -------------------------
    # Common: Pickup & Drop
    # -------------------------
    pickup_included = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    pickup_point = forms.CharField(required=False, help_text="Where will guests be picked up?")
    drop_point = forms.CharField(required=False, help_text="Where will guests be dropped off?")
    pickup_drop_extra_charge = forms.IntegerField(
        required=False, min_value=0,
        help_text="Additional charge for pickup/drop, if any (in ₹).",
    )

    # -------------------------
    # Common: Porter & Baggage
    # -------------------------
    porter_available = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    porter_included_in_price = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    porter_extra_charge = forms.IntegerField(
        required=False, min_value=0,
        help_text="Extra charge for porter service (in ₹).",
    )
    baggage_loading_included = forms.ChoiceField(choices=YES_NO_OPTIONAL_CHOICES, required=False)
    baggage_loading_charge = forms.IntegerField(
        required=False, min_value=0,
        help_text="Extra charge for baggage loading/unloading (in ₹).",
    )
    max_baggage_kg = forms.IntegerField(
        required=False, min_value=0,
        help_text="Maximum baggage allowed per person (in kg).",
    )

    # -------------------------
    # Guided description helpers
    # -------------------------
    INCLUDED_OPTIONS = [
        "Food", "Guide", "Stay", "Equipment", "Entry tickets",
        "Local transport", "Pickup/drop", "Insurance", "Other",
    ]
    NOT_INCLUDED_OPTIONS = [
        "Personal expenses", "Meals", "Transport", "Entry tickets",
        "Accommodation", "Insurance", "Other",
    ]

    what_is_included = forms.MultipleChoiceField(
        choices=[(x, x) for x in INCLUDED_OPTIONS],
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="What is included",
        help_text="Select all that apply.",
    )
    what_is_not_included = forms.MultipleChoiceField(
        choices=[(x, x) for x in NOT_INCLUDED_OPTIONS],
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="What is NOT included",
        help_text="Select all that apply.",
    )
    experience_highlights = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "e.g.\n• Stunning sunrise views\n• Expert local guides\n• Authentic home-cooked meals"}),
        label="Experience Highlights",
        help_text="List key selling points, one per line.",
    )

    # -------------------------
    # Declaration checkboxes
    # -------------------------
    cancellation_policy_accepted = forms.BooleanField(
        required=False,
        label=(
            "I understand that cancellations, refunds, rescheduling, disputes, "
            "and no-show cases will be handled according to the Routeless "
            "platform cancellation policy."
        ),
    )
    listing_declaration_accepted = forms.BooleanField(
        required=False,
        label=(
            "I confirm that this experience information is correct and I am "
            "responsible for complying with all local rules, safety requirements, "
            "and guest protection standards."
        ),
    )

    class Meta:
        model = Experience
        fields = [
            "title",
            "category",
            "location",
            "price_per_person",
            "max_guests",
            "duration",
            "short_description",
            "description",
            "what_is_included",
            "what_is_not_included",
            "experience_highlights",
            "cancellation_policy_accepted",
            "listing_declaration_accepted",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "short_description": forms.TextInput(attrs={"placeholder": "A one-line summary for search results"}),
            "duration": forms.TextInput(attrs={"placeholder": "e.g. 2 days / 4 hours"}),
            "price_per_person": forms.NumberInput(attrs={
                "min": "0", "step": "1",
                "placeholder": "e.g. 2499",
            }),
        }

    # ---------------------------------------------------------
    # Init / styling / preload category_details
    # ---------------------------------------------------------
    def __init__(self, *args, submit_for_review=False, **kwargs):
        super().__init__(*args, **kwargs)
        self._submit_for_review = submit_for_review

        # Apply human-readable labels
        for fname, label in FIELD_LABELS.items():
            if fname in self.fields:
                self.fields[fname].label = label

        # Nice defaults / CSS classes
        for name, field in self.fields.items():
            existing = field.widget.attrs.get("class", "")
            if isinstance(field.widget, (forms.CheckboxInput,)):
                field.widget.attrs["class"] = (existing + " form-check-input").strip()
            elif isinstance(field.widget, (forms.CheckboxSelectMultiple, forms.RadioSelect)):
                # Don't add form-control to multi-checkbox / radio groups
                pass
            elif isinstance(field.widget, (forms.Select,)):
                field.widget.attrs["class"] = (existing + " form-select").strip()
            else:
                field.widget.attrs["class"] = (existing + " form-control").strip()

        # Better placeholders for some common fields
        if "title" in self.fields:
            self.fields["title"].widget.attrs.setdefault("placeholder", "e.g. Sunrise Trek to Nag Tibba")
        if "location" in self.fields:
            self.fields["location"].widget.attrs.setdefault("placeholder", "Start typing a location...")
            self.fields["location"].widget.attrs["autocomplete"] = "off"
            self.fields["location"].widget.attrs["id"] = "id_location"
        if "max_guests" in self.fields:
            self.fields["max_guests"].widget.attrs.setdefault("placeholder", "e.g. 10")
            self.fields["max_guests"].label = "Maximum number of guests"

        # Price field: enforce whole numbers
        if "price_per_person" in self.fields:
            self.fields["price_per_person"].label = "Price per person (₹)"
            self.fields["price_per_person"].decimal_places = 0

        # If editing existing object, preload category_details JSON into form fields
        if self.instance and self.instance.pk and getattr(self.instance, "category_details", None):
            details = self.instance.category_details or {}
            all_loadable = list(ALL_DETAIL_FIELDS) + COMMON_DETAIL_FIELDS
            for fname in all_loadable:
                if fname not in self.fields:
                    continue
                if fname not in details:
                    continue

                value = details.get(fname)

                # If time stored as "HH:MM", Django TimeField can accept string
                self.initial[fname] = value

    # ---------------------------------------------------------
    # Validation helpers
    # ---------------------------------------------------------
    def _validate_min_max(self, cleaned, min_field, max_field, label):
        min_val = cleaned.get(min_field)
        max_val = cleaned.get(max_field)
        if min_val is not None and max_val is not None and min_val > max_val:
            self.add_error(max_field, f"{label}: maximum must be greater than or equal to minimum.")

    def _validate_required_for_category(self, cleaned, category):
        cfg = CATEGORY_FIELD_SETS.get(category, {})
        for fname in cfg.get("required", []):
            val = cleaned.get(fname)
            if val in [None, "", [], {}]:
                self.add_error(fname, f"This field is required for {category} experiences.")

    # ---------------------------------------------------------
    # Clean
    # ---------------------------------------------------------
    def clean(self):
        cleaned = super().clean()

        category = cleaned.get("category")
        if not category:
            return cleaned

        # Price must be >= 0 and whole number
        price = cleaned.get("price_per_person")
        if price is not None:
            if price < 0:
                self.add_error("price_per_person", "Price must be zero or positive.")
            elif price != int(price):
                self.add_error("price_per_person", "Price must be a whole number (no decimals).")

        # max_guests > 0
        max_g = cleaned.get("max_guests")
        if max_g is not None and max_g <= 0:
            self.add_error("max_guests", "Max guests must be greater than zero.")

        # Category-specific required fields (only if submitting for review)
        if self._submit_for_review:
            self._validate_required_for_category(cleaned, category)

            # Declarations required for submit
            if not cleaned.get("cancellation_policy_accepted"):
                self.add_error(
                    "cancellation_policy_accepted",
                    "You must accept the cancellation policy to submit for review.",
                )
            if not cleaned.get("listing_declaration_accepted"):
                self.add_error(
                    "listing_declaration_accepted",
                    "You must accept the listing declaration to submit for review.",
                )

        # Cross-field validations (always run)
        self._validate_min_max(cleaned, "trek_group_size_min", "trek_group_size_max", "Trek group size")
        self._validate_min_max(cleaned, "adv_group_size_min", "adv_group_size_max", "Adventure group size")
        self._validate_min_max(cleaned, "wild_group_size_min", "wild_group_size_max", "Wildlife group size")
        self._validate_min_max(cleaned, "cul_group_size_min", "cul_group_size_max", "Cultural group size")

        self._validate_min_max(cleaned, "adv_min_age", "adv_max_age", "Adventure age")
        self._validate_min_max(cleaned, "adv_min_weight_kg", "adv_max_weight_kg", "Adventure weight")
        self._validate_min_max(cleaned, "adv_min_height_cm", "adv_max_height_cm", "Adventure height")

        # Logical validations
        if category == "Homestay":
            checkin = cleaned.get("home_checkin_time")
            checkout = cleaned.get("home_checkout_time")
            if checkin and checkout and checkin == checkout:
                self.add_error("home_checkout_time", "Check-out time should be different from check-in time.")

        if category == "Adventure":
            activity = cleaned.get("adv_activity_type")
            custom_name = (cleaned.get("adv_activity_custom_name") or "").strip()
            if activity == "Other" and not custom_name:
                self.add_error("adv_activity_custom_name", "Please specify the activity name when selecting 'Other'.")

        # Permit consistency (generic examples)
        if category == "Trek":
            if cleaned.get("trek_permit_included") == "Yes" and cleaned.get("trek_permit_required") == "No":
                self.add_error("trek_permit_included", "Permit cannot be included if permit is not required.")
        if category == "Adventure":
            if cleaned.get("adv_permit_included") == "Yes" and cleaned.get("adv_permit_required") == "No":
                self.add_error("adv_permit_included", "Permit cannot be included if permit is not required.")
        if category == "Wildlife":
            if cleaned.get("wild_permit_included") == "Yes" and cleaned.get("wild_permit_required") == "No":
                self.add_error("wild_permit_included", "Permit cannot be included if permit is not required.")

        return cleaned

    # ---------------------------------------------------------
    # JSON serialization helper
    # ---------------------------------------------------------
    def _json_safe(self, value):
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, time):
            return value.strftime("%H:%M")
        return value

    # ---------------------------------------------------------
    # Save
    # ---------------------------------------------------------
    def save(self, commit=True):
        obj = super().save(commit=False)

        category = self.cleaned_data.get("category")
        details = {}

        # Category-specific fields
        if category in CATEGORY_FIELD_SETS:
            for fname in CATEGORY_FIELD_SETS[category]["fields"]:
                value = self.cleaned_data.get(fname)
                if value in [None, "", [], {}]:
                    continue
                details[fname] = self._json_safe(value)

        # Common detail fields (schedule, pickup, porter)
        for fname in COMMON_DETAIL_FIELDS:
            value = self.cleaned_data.get(fname)
            if value in [None, "", [], {}]:
                continue
            details[fname] = self._json_safe(value)

        # Store category marker inside JSON
        if details:
            details["_category"] = category

        obj.category_details = details

        # Set listing_status based on submit action
        if self._submit_for_review:
            obj.listing_status = Experience.ListingStatus.PENDING_REVIEW
            if not obj.submitted_at:
                from django.utils import timezone
                obj.submitted_at = timezone.now()
        else:
            # Save as Draft (keep draft if new, or keep current status)
            if not obj.pk:
                obj.listing_status = Experience.ListingStatus.DRAFT

        if commit:
            obj.save()
            self.save_m2m()

        return obj

        
class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = [
            'check_in_date', 'check_out_date', 'guests_count',
            'traveler_name', 'traveler_email', 'traveler_phone', 'message'
        ]
        widgets = {
            'check_in_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'check_out_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'message': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }


class SafarUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        help_text="Required. Tell us where to send your booking confirmations."
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['phone_number', 'bio', 'profile_picture']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }


# ---------------------------------------------------------
# Host Application Multi-Step Forms
# ---------------------------------------------------------
from datetime import date as _date
from .models import HostApplication, INDIAN_STATES


class HostDetailsForm(forms.ModelForm):
    """Step 1: Host Details — basic identity and contact."""

    class Meta:
        model = HostApplication
        fields = [
            "host_type",
            "full_name_or_company_name",
            "mobile_number",
            "email",
            "city",
            "state",
            "host_bio",
            "profile_photo_or_logo",
        ]
        widgets = {
            "host_type": forms.RadioSelect(
                attrs={"class": "form-check-input"},
            ),
            "host_bio": forms.Textarea(attrs={"rows": 3}),
            "state": forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mark required fields
        for fname in [
            "host_type",
            "full_name_or_company_name",
            "mobile_number",
            "email",
            "city",
            "state",
        ]:
            self.fields[fname].required = True
        # Optional fields
        self.fields["host_bio"].required = False
        self.fields["profile_photo_or_logo"].required = False

        # Apply Bootstrap classes
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.RadioSelect):
                continue  # styled separately in template
            existing = field.widget.attrs.get("class", "")
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = (existing + " form-select").strip()
            elif isinstance(field.widget, forms.FileInput):
                field.widget.attrs["class"] = (existing + " form-control").strip()
            else:
                field.widget.attrs["class"] = (existing + " form-control").strip()

        # Placeholders
        self.fields["full_name_or_company_name"].widget.attrs["placeholder"] = (
            "e.g. Ravi Kumar or Himalaya Adventures Pvt Ltd"
        )
        self.fields["mobile_number"].widget.attrs["placeholder"] = "e.g. +91 98765 43210"
        self.fields["email"].widget.attrs["placeholder"] = "e.g. host@example.com"
        self.fields["city"].widget.attrs["placeholder"] = "e.g. Manali"


class HostVerificationForm(forms.ModelForm):
    """Step 2: Verification — documents and banking details."""

    class Meta:
        model = HostApplication
        fields = [
            "pan_number",
            "government_id_proof",
            "police_verification_certificate",
            "police_verification_issue_date",
            "bank_account_holder_name",
            "bank_name",
            "account_number",
            "ifsc_code",
        ]
        widgets = {
            "police_verification_issue_date": forms.DateInput(
                attrs={"type": "date"},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # All fields required
        for name in self.fields:
            self.fields[name].required = True

        # Bootstrap classes
        for name, field in self.fields.items():
            existing = field.widget.attrs.get("class", "")
            if isinstance(field.widget, (forms.FileInput, forms.ClearableFileInput)):
                field.widget.attrs["class"] = (existing + " form-control").strip()
            else:
                field.widget.attrs["class"] = (existing + " form-control").strip()

        # Placeholders
        self.fields["pan_number"].widget.attrs["placeholder"] = "e.g. ABCDE1234F"
        self.fields["bank_account_holder_name"].widget.attrs["placeholder"] = "Account holder name"
        self.fields["bank_name"].widget.attrs["placeholder"] = "e.g. State Bank of India"
        self.fields["account_number"].widget.attrs["placeholder"] = "Account number"
        self.fields["ifsc_code"].widget.attrs["placeholder"] = "e.g. SBIN0001234"

    def clean_pan_number(self):
        import re
        pan = self.cleaned_data.get("pan_number", "").strip().upper()
        if pan and not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", pan):
            raise forms.ValidationError("Enter a valid PAN number (e.g. ABCDE1234F).")
        return pan

    def clean_ifsc_code(self):
        import re
        ifsc = self.cleaned_data.get("ifsc_code", "").strip().upper()
        if ifsc and not re.match(r"^[A-Z]{4}0[A-Z0-9]{6}$", ifsc):
            raise forms.ValidationError("Enter a valid IFSC code (e.g. SBIN0001234).")
        return ifsc

    def clean_police_verification_issue_date(self):
        issue_date = self.cleaned_data.get("police_verification_issue_date")
        if issue_date:
            delta = _date.today() - issue_date
            if delta.days > 90:
                raise forms.ValidationError(
                    "Police verification certificate must not be older than "
                    "3 months from the date of submission."
                )
            if issue_date > _date.today():
                raise forms.ValidationError(
                    "Issue date cannot be in the future."
                )
        return issue_date


class HostBusinessForm(forms.ModelForm):
    """Step 3: Business Details — shown only for Company hosts."""

    class Meta:
        model = HostApplication
        fields = [
            "gst_number",
            "msme_udyam_number",
            "authorized_person_name",
            "business_address",
        ]
        widgets = {
            "business_address": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Required for Company hosts
        self.fields["authorized_person_name"].required = True
        self.fields["business_address"].required = True
        # Optional
        self.fields["gst_number"].required = False
        self.fields["msme_udyam_number"].required = False

        # Bootstrap classes
        for name, field in self.fields.items():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (existing + " form-control").strip()

        # Placeholders
        self.fields["gst_number"].widget.attrs["placeholder"] = "e.g. 22AAAAA0000A1Z5 (optional)"
        self.fields["msme_udyam_number"].widget.attrs["placeholder"] = "e.g. UDYAM-XX-00-0000000 (optional)"
        self.fields["authorized_person_name"].widget.attrs["placeholder"] = "Name of authorized signatory"
        self.fields["business_address"].widget.attrs["placeholder"] = "Registered business address"

    def clean_gst_number(self):
        import re
        gst = self.cleaned_data.get("gst_number", "").strip().upper()
        if gst and not re.match(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$", gst):
            raise forms.ValidationError("Enter a valid GST number.")
        return gst


class HostDeclarationForm(forms.Form):
    """Step 4: Declaration checkbox before final submission."""

    declaration_accepted = forms.BooleanField(
        required=True,
        label=(
            "I confirm that the information provided is correct and I agree "
            "to follow Routeless host, safety, tax, and legal compliance rules."
        ),
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        error_messages={
            "required": "You must accept the declaration to submit your application.",
        },
    )
