"""Accounts: sign-up and login (with clearly highlighted errors), password
reset and change, download my data, delete my account."""
import json
import re

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.urls import reverse

from accounts.models import SavedSearch, TrackedJob, UserProfile
from jobs.tests.helpers import PASSWORD, WBTestCase, make_admin, make_job, make_seeker


class SignUpTest(WBTestCase):
    url = reverse('register')

    def form(self, **overrides):
        data = {'username': 'thandi', 'email': 'thandi@example.com',
                'password1': 'GoodPass!987', 'password2': 'GoodPass!987'}
        data.update(overrides)
        return data

    def test_sign_up_creates_account_and_profile_and_logs_in(self):
        r = self.client.post(self.url, self.form())
        self.assertRedirects(r, reverse('profile_edit'))
        user = User.objects.get(username='thandi')
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        self.assertEqual(self.client.get(reverse('profile')).status_code, 200)

    def test_errors_are_highlighted_next_to_the_right_boxes(self):
        make_seeker('taken')
        r = self.client.post(self.url, self.form(username='taken', password2='Different!1'))
        html = r.content.decode()
        self.assertIn('form-error-summary', html)
        self.assertEqual(html.count('has-error'), 2, "username and password confirmation should both be flagged")
        self.assertIn('A user with that username already exists', html)
        self.assertIn('password boxes are emptied', html)
        self.assertFalse(User.objects.filter(email='thandi@example.com').exists())

    def test_duplicate_email_refused(self):
        make_seeker('first', email='same@example.com')
        r = self.client.post(self.url, self.form(email='SAME@example.com'))
        self.assertPageHas(r, 'An account with this email already exists')

    def test_password_rules_shown_as_hints_not_raw_code(self):
        r = self.client.get(self.url)
        self.assertPageLacks(r, '&lt;ul&gt;')


class LoginLogoutTest(WBTestCase):
    def setUp(self):
        super().setUp()
        self.user = make_seeker('lerato')

    def test_login_and_logout(self):
        r = self.client.post(reverse('login'), {'username': 'lerato', 'password': PASSWORD})
        self.assertRedirects(r, reverse('profile'))
        self.client.post(reverse('logout'))
        self.assertEqual(self.client.get(reverse('profile')).status_code, 302)

    def test_wrong_password_shows_error_summary(self):
        r = self.client.post(reverse('login'), {'username': 'lerato', 'password': 'nope'})
        self.assertPageHas(r, 'form-error-summary')
        self.assertPageHas(r, 'correct username and password')

    def test_login_page_has_forgot_password_link(self):
        self.assertPageHas(self.client.get(reverse('login')), reverse('password_reset'))


class PasswordResetTest(WBTestCase):
    def setUp(self):
        super().setUp()
        self.user = make_seeker('sipho', email='Sipho@Example.com')

    def request_reset(self, email, **extra):
        return self.client.post(reverse('password_reset'), {'email': email}, **extra)

    def test_full_reset_flow(self):
        r = self.request_reset('sipho@example.COM', HTTP_X_FORWARDED_PROTO='https', HTTP_HOST='workbase21.co.za')
        self.assertRedirects(r, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        m = mail.outbox[0]
        self.assertEqual(m.to, [self.user.email])   # Django lower-cases the domain part on sign-up
        self.assertEqual(m.from_email, settings.DEFAULT_FROM_EMAIL)
        link = re.search(r'https://workbase21\.co\.za(/accounts/reset/\S+/)', m.body)
        self.assertIsNotNone(link, "reset link should be https on the real domain")
        r = self.client.get(link.group(1))
        set_url = r['Location']
        r = self.client.post(set_url, {'new_password1': 'BrandNew!555', 'new_password2': 'BrandNew!555'})
        self.assertRedirects(r, reverse('password_reset_complete'))
        self.assertTrue(self.client.login(username='sipho', password='BrandNew!555'))
        self.client.logout()
        r = self.client.get(link.group(1), follow=True)
        self.assertPageHas(r, 'invalid or has expired')

    def test_unknown_email_same_response_no_email_and_logged(self):
        with self.assertLogs('accounts.views', 'INFO') as logs:
            r = self.request_reset('nobody@example.com')
        self.assertRedirects(r, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(any('no active account' in line for line in logs.output))
        self.assertFalse(any('nobody@example.com' in line for line in logs.output), "full address must not be logged")

    def test_rate_limits(self):
        for _ in range(5):
            self.request_reset('sipho@example.com')
        self.assertEqual(len(mail.outbox), 3, "max 3 reset emails per address per hour")


class PasswordChangeTest(WBTestCase):
    def test_change_password(self):
        self.login(make_seeker('ann'))
        r = self.client.post(reverse('password_change'),
                             {'old_password': 'wrong', 'new_password1': 'Another!555x', 'new_password2': 'Another!555x'})
        self.assertPageHas(r, 'has-error')
        r = self.client.post(reverse('password_change'),
                             {'old_password': PASSWORD, 'new_password1': 'Another!555x', 'new_password2': 'Another!555x'})
        self.assertRedirects(r, reverse('account_settings'))
        self.assertEqual(self.client.get(reverse('profile')).status_code, 200, "still logged in")


class MyDataTest(WBTestCase):
    def setUp(self):
        super().setUp()
        self.user = make_seeker('thabo', location='Thohoyandou')
        job = make_job('Clerk')
        TrackedJob.objects.create(user=self.user, job=job, status='applied', notes='Sent CV')
        SavedSearch.objects.create(user=self.user, job_type='internship')
        other = make_seeker('nosy')
        TrackedJob.objects.create(user=other, job=job, notes='OTHER PERSON NOTE')
        self.login(self.user)

    def test_download_my_data(self):
        r = self.client.get(reverse('account_download'))
        self.assertIn('attachment', r['Content-Disposition'])
        data = json.loads(r.content)
        self.assertEqual(data['account']['username'], 'thabo')
        self.assertEqual(data['profile']['location'], 'Thohoyandou')
        self.assertEqual(data['saved_and_tracked_jobs'][0]['notes'], 'Sent CV')
        self.assertEqual(data['saved_searches'][0]['search'], 'Internships')
        self.assertNotIn(b'OTHER PERSON NOTE', r.content)

    def test_delete_account(self):
        r = self.client.post(reverse('account_delete'), {'password': 'wrong'})
        self.assertTrue(User.objects.filter(username='thabo').exists())
        r = self.client.post(reverse('account_delete'), {'password': PASSWORD})
        self.assertRedirects(r, reverse('welcome'))
        self.assertFalse(User.objects.filter(username='thabo').exists())
        self.assertFalse(TrackedJob.objects.filter(notes='Sent CV').exists())
        self.assertFalse(SavedSearch.objects.filter(user__username='thabo').exists())
        self.assertTrue(TrackedJob.objects.filter(notes='OTHER PERSON NOTE').exists())
        self.assertEqual(self.client.get(reverse('profile')).status_code, 302, "logged out")

    def test_admin_cannot_delete_own_account_here(self):
        self.login(make_admin())
        self.client.post(reverse('account_delete'), {'password': PASSWORD})
        self.assertTrue(User.objects.filter(username='boss').exists())
