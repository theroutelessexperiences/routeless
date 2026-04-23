from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Location, Experience, Booking, UserProfile
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

class MarketplaceE2ETests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Setup test data
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.host = User.objects.create_user(username='testhost', password='password123')
        self.host.userprofile.is_host = True
        self.host.userprofile.save()
        
        self.location = Location.objects.create(name='Manali', slug='manali', state='HP')
        
        self.experience = Experience.objects.create(
            title='Test Trek', 
            slug='test-trek', 
            category='Trek',
            location='Manali, HP',
            host=self.host,
            price_per_person=1000,
            max_guests=4,
            duration='3 Days',
            is_active=True,
            status=Experience.Status.APPROVED
        )

    def test_homepage_loads(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'THEROUTELESS')
        
    def test_listing_list_and_search(self):
        response = self.client.get(reverse('listing_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Trek')
        
        # Test filters
        response = self.client.get(reverse('listing_list') + '?category=trekking')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Trek')
        
        response = self.client.get(reverse('listing_list') + '?category=homestay')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Test Trek')
        
    def test_listing_detail(self):
        response = self.client.get(reverse('listing_detail', kwargs={'slug': self.experience.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Trek')
        self.assertContains(response, '1000')

    def test_booking_requires_auth(self):
        # Post request to book without login
        response = self.client.post(reverse('listing_detail', kwargs={'slug': self.experience.slug}), {
            'start_date': date.today().isoformat(),
            'end_date': (date.today() + timedelta(days=2)).isoformat(),
            'guests': 2,
            'traveler_name': 'Test',
            'traveler_email': 'test@test.com',
            'traveler_phone': '123'
        })
        # Should redirect to login
        self.assertRedirects(response, f"{reverse('login')}?next=/experiences/{self.experience.slug}/", fetch_redirect_response=False)
        # Assuming URL pattern '/login/?next=...' but standard redirect is checked. Actually reverse('login') gives '/login/', so:
    @patch('payments.services.create_razorpay_order')
    def test_booking_flow_authenticated(self, mock_create_order):
        # Setup mock to simulate successful Razorpay order creation
        mock_payment = MagicMock()
        mock_payment.payment_status = "pending"
        mock_create_order.return_value = (True, mock_payment)
        
        self.client.login(username='testuser', password='password123')
        
        response = self.client.post(reverse('listing_detail', kwargs={'slug': self.experience.slug}), {
            'start_date': date.today().isoformat(),
            'end_date': (date.today() + timedelta(days=2)).isoformat(),
            'guests': 2,
            'traveler_name': 'Test',
            'traveler_email': 'test@test.com',
            'traveler_phone': '123'
        })
        
        booking = Booking.objects.first()
        if not booking:
            print("Booking is None!")
            print(f"Response status: {response.status_code}")
            if response.status_code in [301, 302]:
                print(f"Redirected to: {response.url}")
            else:
                print(f"Content: {response.content}")
                
        self.assertRedirects(response, reverse('checkout', kwargs={'pk': booking.id}))
        self.assertEqual(booking.user, self.user)
        self.assertEqual(booking.booking_status, 'Payment Created')
        
    def test_host_dashboard_access(self):
        # Normal user shouldn't access
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('host_dashboard'))
        self.assertRedirects(response, reverse('home'))
        
        # Host should access
        self.client.logout()
        self.client.login(username='testhost', password='password123')
        response = self.client.get(reverse('host_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Host Dashboard')
        
    def test_my_bookings(self):
        self.client.login(username='testuser', password='password123')
        Booking.objects.create(
            experience=self.experience, user=self.user,
            traveler_name='t', traveler_email='e@e.com', traveler_phone='123',
            check_in_date=date.today(), check_out_date=date.today() + timedelta(days=1), guests_count=1
        )
        response = self.client.get(reverse('my_bookings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Trek')
