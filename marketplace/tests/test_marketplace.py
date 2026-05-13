from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from marketplace.models import Location, Experience, Booking, UserProfile
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
        self.assertContains(response, 'The Routeless')
        
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


class HostApplicationTests(TestCase):
    """Tests for the multi-step host application flow."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='hostapplicant',
            email='applicant@test.com',
            password='password123',
        )

    def _login(self):
        self.client.login(username='hostapplicant', password='password123')

    def _create_step1(self, **overrides):
        from marketplace.models import HostApplication
        defaults = {
            'user': self.user,
            'host_type': HostApplication.HostType.INDIVIDUAL,
            'full_name_or_company_name': 'Test Host',
            'mobile_number': '+919876543210',
            'email': 'host@test.com',
            'city': 'Manali',
            'state': 'Himachal Pradesh',
        }
        defaults.update(overrides)
        return HostApplication.objects.create(**defaults)

    # ---- Model validation tests ----

    def test_police_cert_older_than_3_months_fails(self):
        from django.core.exceptions import ValidationError
        from marketplace.models import HostApplication
        app = self._create_step1()
        app.police_verification_issue_date = date.today() - timedelta(days=91)
        with self.assertRaises(ValidationError) as ctx:
            app.full_clean()
        self.assertIn('police_verification_issue_date', ctx.exception.message_dict)

    def test_police_cert_within_3_months_passes(self):
        from marketplace.models import HostApplication
        app = self._create_step1()
        app.police_verification_issue_date = date.today() - timedelta(days=30)
        # Should not raise
        try:
            app.clean()
        except Exception:
            self.fail("Police cert within 3 months should not raise validation error")

    def test_company_requires_authorized_person(self):
        from django.core.exceptions import ValidationError
        from marketplace.models import HostApplication
        app = self._create_step1(host_type=HostApplication.HostType.COMPANY)
        app.verification_status = HostApplication.VerificationStatus.SUBMITTED
        app.declaration_accepted = True
        app.authorized_person_name = ''
        app.business_address = ''
        with self.assertRaises(ValidationError) as ctx:
            app.full_clean()
        self.assertIn('authorized_person_name', ctx.exception.message_dict)
        self.assertIn('business_address', ctx.exception.message_dict)

    def test_declaration_required_before_submission(self):
        from django.core.exceptions import ValidationError
        from marketplace.models import HostApplication
        app = self._create_step1()
        app.verification_status = HostApplication.VerificationStatus.SUBMITTED
        app.declaration_accepted = False
        with self.assertRaises(ValidationError) as ctx:
            app.full_clean()
        self.assertIn('declaration_accepted', ctx.exception.message_dict)

    # ---- Step completion property tests ----

    def test_step1_complete(self):
        app = self._create_step1()
        self.assertTrue(app.step1_complete)

    def test_step2_incomplete_by_default(self):
        app = self._create_step1()
        self.assertFalse(app.step2_complete)

    def test_step3_complete_for_individual(self):
        from marketplace.models import HostApplication
        app = self._create_step1(host_type=HostApplication.HostType.INDIVIDUAL)
        self.assertTrue(app.step3_complete)

    def test_step3_incomplete_for_company_without_details(self):
        from marketplace.models import HostApplication
        app = self._create_step1(host_type=HostApplication.HostType.COMPANY)
        self.assertFalse(app.step3_complete)

    # ---- View access tests ----

    def test_step1_requires_login(self):
        response = self.client.get(reverse('host_apply_details'))
        self.assertEqual(response.status_code, 302)

    def test_step1_loads_for_authenticated_user(self):
        self._login()
        response = self.client.get(reverse('host_apply_details'))
        self.assertEqual(response.status_code, 200)

    def test_step2_redirects_without_step1(self):
        self._login()
        response = self.client.get(reverse('host_apply_verification'))
        self.assertRedirects(response, reverse('host_apply_details'))

    def test_individual_skips_business_step(self):
        from marketplace.models import HostApplication
        self._login()
        app = self._create_step1()
        # Fill step 2
        app.pan_number = 'ABCDE1234F'
        app.government_id_proof = 'test.pdf'
        app.police_verification_certificate = 'test2.pdf'
        app.police_verification_issue_date = date.today() - timedelta(days=10)
        app.bank_account_holder_name = 'Test'
        app.bank_name = 'SBI'
        app.account_number = '123456789'
        app.ifsc_code = 'SBIN0001234'
        app.save()

        response = self.client.get(reverse('host_apply_business'))
        self.assertRedirects(response, reverse('host_apply_declaration'))

    def test_become_host_redirects_existing_host(self):
        self._login()
        profile = self.user.userprofile
        profile.is_host = True
        profile.save()
        response = self.client.get(reverse('become_host'))
        self.assertRedirects(response, reverse('host_dashboard'))

    # ---- Form validation tests ----

    def test_pan_validation(self):
        from marketplace.forms import HostVerificationForm
        data = {
            'pan_number': 'INVALID',
            'government_id_proof': '',
            'police_verification_certificate': '',
            'police_verification_issue_date': date.today().isoformat(),
            'bank_account_holder_name': 'Test',
            'bank_name': 'SBI',
            'account_number': '123456',
            'ifsc_code': 'SBIN0001234',
        }
        form = HostVerificationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('pan_number', form.errors)

    def test_ifsc_validation(self):
        from marketplace.forms import HostVerificationForm
        data = {
            'pan_number': 'ABCDE1234F',
            'police_verification_issue_date': date.today().isoformat(),
            'bank_account_holder_name': 'Test',
            'bank_name': 'SBI',
            'account_number': '123456',
            'ifsc_code': 'INVALID',
        }
        form = HostVerificationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('ifsc_code', form.errors)

    def test_declaration_form_requires_checkbox(self):
        from marketplace.forms import HostDeclarationForm
        form = HostDeclarationForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('declaration_accepted', form.errors)

    def test_declaration_form_valid(self):
        from marketplace.forms import HostDeclarationForm
        form = HostDeclarationForm(data={'declaration_accepted': True})
        self.assertTrue(form.is_valid())

