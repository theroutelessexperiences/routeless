from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from marketplace.models import Location, Experience, ExperienceImage, UserProfile, CATEGORY_CHOICES
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Seeds the database with Locations, Users, and Experiences'

    def handle(self, *args, **kwargs):
        self.stdout.write('Clearing old data...')
        Experience.objects.all().delete()
        Location.objects.all().delete()
        User.objects.exclude(is_superuser=True).delete()

        self.stdout.write('Creating Locations...')
        locations_data = [
            {'name': 'Manali', 'state': 'Himachal Pradesh'},
            {'name': 'Rishikesh', 'state': 'Uttarakhand'},
            {'name': 'Kasol', 'state': 'Himachal Pradesh'},
            {'name': 'Shimla', 'state': 'Himachal Pradesh'}
        ]
        locations = {}
        for l_data in locations_data:
            loc, _ = Location.objects.get_or_create(
                name=l_data['name'], 
                defaults={'state': l_data['state']}
            )
            locations[l_data['name']] = loc

        self.stdout.write('Creating Users/Hosts...')
        hosts_data = ['rahul_host', 'anita_host', 'vikram_host', 'sushma_host']
        hosts = []
        for h_name in hosts_data:
            user, created = User.objects.get_or_create(username=h_name)
            if created:
                user.set_password('safar123')
                user.save()
            # userprofile is auto-created, just update it
            user.userprofile.is_host = True
            user.userprofile.bio = f"Hi, I am {h_name}, a passionate local host."
            user.userprofile.save()
            hosts.append(user)

        self.stdout.write('Creating Experiences & Images...')
        experiences_data = [
            # Manali
            ('Riverside Camping', 'Manali', 'Adventure', 0, 1500, 4, '3 Days'),
            ('Wooden Cottage', 'Manali', 'Homestay', 1, 4500, 6, '2 Days'),
            ('Rohtang Pass Tour', 'Manali', 'Cultural', 2, 3000, 2, '1 Day'),
            # Rishikesh
            ('Ganga Rafting', 'Rishikesh', 'Adventure', 0, 2000, 8, '1 Day'),
            ('Ashram Retreat', 'Rishikesh', 'Spiritual', 1, 2500, 2, '5 Days'),
            ('Neelkanth Trek', 'Rishikesh', 'Trek', 3, 1200, 10, '2 Days'),
            # Kasol
            ('Kheerganga Trek', 'Kasol', 'Trek', 3, 3500, 12, '3 Days'),
            ('Parvati Homestay', 'Kasol', 'Homestay', 1, 1800, 3, '2 Days'),
            ('Tosh Village Run', 'Kasol', 'Adventure', 2, 1000, 4, '1 Day'),
            # Shimla
            ('Jakhoo Hike', 'Shimla', 'Trek', 0, 800, 15, '1 Day'),
            ('Heritage Mall Road', 'Shimla', 'Homestay', 1, 5500, 2, '3 Days'),
            ('Kufri Snow Trip', 'Shimla', 'Adventure', 2, 2200, 4, '2 Days')
        ]

        count = 0
        img_urls = [
            'https://images.unsplash.com/photo-1605649487212-4d4ce3837242?auto=format&fit=crop&w=400&q=80',
            'https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?auto=format&fit=crop&w=400&q=80',
            'https://images.unsplash.com/photo-1510798831971-661eb04b3739?auto=format&fit=crop&w=400&q=80'
        ]

        for title, loc_name, cat_name, host_idx, price, guests, duration in experiences_data:
            slug = slugify(title)
            experience, created = Experience.objects.get_or_create(
                slug=slug,
                defaults={
                    'title': title,
                    'location': loc_name + ", " + locations[loc_name].state,
                    'category': cat_name,
                    'host': hosts[host_idx],
                    'description': f"Experience the best of {loc_name} with {title}. A premium {cat_name.lower()} offering.",
                    'short_description': f"A beautiful {cat_name} experience in {loc_name}.",
                    'price_per_person': price,
                    'max_guests': guests,
                    'duration': duration,
                    'is_active': True
                }
            )
            if created:
                count += 1
                # Add images
                ExperienceImage.objects.create(experience=experience, image='experiences/placeholder1.jpg', is_primary=True)
                ExperienceImage.objects.create(experience=experience, image='experiences/placeholder2.jpg')

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {count} new experiences across 4 locations and categories.'))
