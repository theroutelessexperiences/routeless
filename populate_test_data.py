import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "safar_hq.settings")
django.setup()

from django.contrib.auth.models import User
from marketplace.models import Location, Experience, CATEGORY_CHOICES, UserProfile

def run():
    print("Populating test data...")
    # Create test host
    host, created = User.objects.get_or_create(username="test_host", email="host@therouteless.com")
    if created:
        host.set_password("testpassword123")
        host.save()
        profile, _ = UserProfile.objects.get_or_create(user=host)
        profile.is_host = True
        profile.save()
        print("Created test host.")

    # Create locations
    loc1, _ = Location.objects.get_or_create(name="Manali", state="Himachal Pradesh")
    loc2, _ = Location.objects.get_or_create(name="Rishikesh", state="Uttarakhand")
    loc3, _ = Location.objects.get_or_create(name="Goa", state="Goa")

    print("Created locations.")

    # Create experiences
    experiences_data = [
        {
            "title": "Riverside Camping & Rafting",
            "category": "Adventure",
            "location_fk": loc2,
            "host": host,
            "short_description": "Experience the thrill of white water rafting followed by a serene night camping alongside the Ganges.",
            "description": "An unforgettable 2-day adventure in Rishikesh featuring 16km river rafting, cliff jumping, body surfing, and overnight stay in luxury Swiss tents. Includes all meals, bonfire, and live music.",
            "price_per_person": 2500.00,
            "max_guests": 20,
            "duration": "2 Days, 1 Night",
            "status": "approved",
            "is_featured": True,
        },
        {
            "title": "Himalayan Apple Orchard Homestay",
            "category": "Homestay",
            "location_fk": loc1,
            "host": host,
            "short_description": "Wake up to stunning snow-capped peaks and the sweet aroma of apple orchards.",
            "description": "Stay with a local Himachali family in their traditional wood-and-stone house surrounded by lush apple orchards. Enjoy authentic home-cooked meals, village walks, and pure mountain air.",
            "price_per_person": 1800.00,
            "max_guests": 6,
            "duration": "Flexible",
            "status": "approved",
            "is_featured": True,
        },
        {
            "title": "Old Goa Heritage Walk & Feni Tasting",
            "category": "Cultural",
            "location_fk": loc3,
            "host": host,
            "short_description": "Discover the Portuguese influence in Goa through its architecture and local spirits.",
            "description": "A guided walking tour through the majestic churches and cathedrals of Old Goa (a UNESCO World Heritage site), followed by a visit to a local tavern for an authentic Feni tasting session.",
            "price_per_person": 1200.00,
            "max_guests": 15,
            "duration": "4 Hours",
            "status": "approved",
            "is_featured": True,
        }
    ]

    for data in experiences_data:
        exp, created = Experience.objects.get_or_create(
            title=data["title"],
            defaults=data
        )
        if created:
            print(f"Created experience: {exp.title}")
        else:
            # Update just to be sure
            for k, v in data.items():
                setattr(exp, k, v)
            exp.save()
            print(f"Updated experience: {exp.title}")

    print("Done populating test data.")

if __name__ == "__main__":
    run()
