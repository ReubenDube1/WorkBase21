"""Saved jobs + application tracker, saved searches + job alerts, and the
check_email diagnostic. Includes privacy checks: job seekers can never see
or change each other's data."""
import io
import smtplib
from datetime import timedelta
from unittest import mock

from django.core import mail
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import SavedSearch, TrackedJob
from jobs.models import Job
from jobs.tests.helpers import WBTestCase, make_job, make_seeker


class SavedJobsTrackerTest(WBTestCase):
    def setUp(self):
        super().setUp()
        self.user = make_seeker('lindiwe')
        self.jobs = [make_job(f'Job {i}') for i in range(3)]
        self.login(self.user)

    def toggle(self, job, **data):
        return self.client.post(reverse('toggle_saved_job', args=[job.pk]), data)

    def tracked(self, job):
        return TrackedJob.objects.filter(user=self.user, job=job).first()

    def update(self, t, **fields):
        data = {'status': t.status, 'applied_at': '', 'reminder_date': '', 'notes': ''}
        data.update(fields)
        return self.client.post(reverse('application_edit', args=[t.pk]), data)

    def test_save_and_unsave(self):
        j = self.jobs[0]
        self.assertRedirects(self.toggle(j, next=j.get_absolute_url()), j.get_absolute_url(), fetch_redirect_response=False)
        self.assertEqual(self.tracked(j).status, 'saved')
        self.toggle(j)
        self.assertIsNone(self.tracked(j))

    def test_save_button_never_deletes_an_application(self):
        j = self.jobs[0]
        self.toggle(j)
        self.update(self.tracked(j), status='applied', notes='Sent CV')
        self.toggle(j)
        self.assertIsNotNone(self.tracked(j))
        self.assertEqual(self.tracked(j).applied_at, timezone.localdate(), "applied date fills itself in")

    def test_stats(self):
        for j in self.jobs:
            self.toggle(j)
        a, b, c = (self.tracked(j) for j in self.jobs)
        self.update(a, status='applied')
        self.update(b, status='interview')
        self.update(b, status='rejected')
        r = self.client.get(reverse('application_tracker'))
        s = r.context['stats']
        self.assertEqual((s['saved'], s['applied'], s['interviews'], s['offers'], s['response_rate']), (1, 2, 1, 0, 50))

    def test_reminders_shown(self):
        self.toggle(self.jobs[0])
        self.update(self.tracked(self.jobs[0]), reminder_date=str(timezone.localdate() - timedelta(days=1)))
        r = self.client.get(reverse('application_tracker'))
        self.assertPageHas(r, 'Coming up')
        self.assertPageHas(r, 'overdue')

    def test_invalid_date_flagged(self):
        self.toggle(self.jobs[0])
        r = self.update(self.tracked(self.jobs[0]), applied_at='not-a-date')
        self.assertPageHas(r, 'has-error')

    def test_hidden_job_shows_no_longer_listed(self):
        self.toggle(self.jobs[0])
        Job.objects.filter(pk=self.jobs[0].pk).update(is_active=False)
        self.assertPageHas(self.client.get(reverse('application_tracker')), 'No longer listed')

    def test_other_people_cannot_see_or_change_my_entries(self):
        self.toggle(self.jobs[0])
        mine = self.tracked(self.jobs[0])
        self.login(make_seeker('nosy'))
        self.assertEqual(self.client.get(reverse('application_edit', args=[mine.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('application_delete', args=[mine.pk])).status_code, 404)
        self.assertTrue(TrackedJob.objects.filter(pk=mine.pk).exists())

    def test_save_cannot_redirect_to_other_websites(self):
        r = self.toggle(self.jobs[0], next='https://evil.example.com/')
        self.assertEqual(r['Location'], self.jobs[0].get_absolute_url())


class JobAlertsTest(WBTestCase):
    def setUp(self):
        super().setUp()
        self.user = make_seeker('alertuser')
        self.login(self.user)
        make_job('Existing Remote Intern', type=Job.INTERNSHIP, work_mode='remote')

    def save_search(self, **data):
        base = {'results_path': reverse('internships'), 'job_type': 'internship', 'sector': ''}
        base.update(data)
        return self.client.post(reverse('saved_search_create'), base)

    def test_only_new_matching_listings_count_including_backdated(self):
        self.save_search(f_work_mode='remote')
        s = SavedSearch.objects.get(user=self.user)
        self.assertEqual(s.describe(), 'Internships · Remote')
        self.assertEqual(s.new_jobs().count(), 0, "existing listings are not 'new'")
        new = make_job('New Remote Intern', type=Job.INTERNSHIP, work_mode='remote')
        make_job('New Onsite Intern', type=Job.INTERNSHIP, work_mode='onsite')
        back = make_job('Backdated Remote Intern', type=Job.INTERNSHIP, work_mode='remote',
                        created_at=timezone.now() - timedelta(days=60))
        self.assertEqual(set(s.new_jobs()), {new, back})

    def test_alerts_page_badge_and_mark_seen(self):
        self.save_search(f_work_mode='remote')
        make_job('New Remote Intern', type=Job.INTERNSHIP, work_mode='remote')
        self.client.session.pop('job_alert_count_cache', None)
        r = self.client.get(reverse('job_alerts'))
        self.assertEqual(r.context['total_new'], 1)
        self.assertPageHas(self.client.get(reverse('welcome')), 'hamburger-badge')
        self.client.post(reverse('job_alerts_mark_all_seen'))
        self.assertEqual(self.client.get(reverse('job_alerts')).context['total_new'], 0)

    def test_duplicates_tampering_and_limit(self):
        self.save_search(f_work_mode='remote')
        self.save_search(f_work_mode='remote')
        self.assertEqual(SavedSearch.objects.filter(user=self.user).count(), 1, "no duplicates")
        self.save_search(results_path='/admin/')
        self.save_search(results_path='https://evil.example.com/')
        self.assertEqual(SavedSearch.objects.filter(user=self.user).count(), 1, "tampered paths refused")
        for i in range(12):
            self.client.post(reverse('saved_search_create'), {'results_path': reverse('search'), 'q': f'term{i}'})
        self.assertEqual(SavedSearch.objects.filter(user=self.user).count(), 10, "max 10 saved searches")

    def test_other_people_cannot_change_my_alerts(self):
        self.save_search(f_work_mode='remote')
        s = SavedSearch.objects.get(user=self.user)
        self.login(make_seeker('nosy'))
        self.assertEqual(self.client.post(reverse('saved_search_delete', args=[s.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('job_alerts_mark_seen', args=[s.pk])).status_code, 404)


@override_settings(EMAIL_HOST_USER='contact.workbase21@gmail.com', EMAIL_HOST_PASSWORD='abcdefghijklmnop',
                   EMAIL_HOST='smtp.gmail.com', EMAIL_PORT=587)
class CheckEmailCommandTest(WBTestCase):
    def run_check(self, email='contact.workbase21@gmail.com'):
        out = io.StringIO()
        call_command('check_email', email, stdout=out)
        return out.getvalue()

    @override_settings(EMAIL_HOST_USER='', EMAIL_HOST_PASSWORD='')
    def test_reports_missing_settings(self):
        self.assertIn('Not set on this server', self.run_check())

    @override_settings(EMAIL_HOST_PASSWORD='fifteenchars123')
    def test_reports_wrong_password_length(self):
        self.assertIn('is 15 characters', self.run_check())

    def test_reports_blocked_network(self):
        with mock.patch('socket.create_connection', side_effect=OSError('Network is unreachable')):
            self.assertIn("can't reach", self.run_check())

    def test_reports_rejected_login(self):
        with mock.patch('socket.create_connection'), mock.patch('smtplib.SMTP') as S:
            S.return_value.login.side_effect = smtplib.SMTPAuthenticationError(535, b'no')
            self.assertIn('Gmail rejected the login', self.run_check())

    def test_all_good_sends_test_email(self):
        make_seeker('owner', email='contact.workbase21@gmail.com')
        with mock.patch('socket.create_connection'), mock.patch('smtplib.SMTP'):
            out = self.run_check()
        self.assertIn("Account 'owner' uses", out)
        self.assertIn('Test email sent', out)
        self.assertEqual(mail.outbox[-1].to, ['contact.workbase21@gmail.com'])
