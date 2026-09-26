"""Admin tools: Listing Insights numbers are correct (and not inflated by
page visits), job list columns/filters work, and Duplicate/Publish/Hide
actions do exactly what they say."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from accounts.models import TrackedJob
from jobs.models import Job, JobApplicationLink, PageVisit
from .helpers import WBTestCase, make_admin, make_job, make_seeker, skill


class ListingInsightsTest(WBTestCase):
    def setUp(self):
        super().setUp()
        self.login(make_admin())
        self.star = make_job('Star Job', deadline=timezone.localdate() + timedelta(days=3),
                             qualification_level='degree', experience_level='entry',
                             work_mode='onsite', industry='it', skills=[skill('Python')])
        for i in range(12):   # 12 visits from 4 different visitors
            PageVisit.objects.create(path=self.star.get_absolute_url(), session_key=f's{i % 4}', job=self.star)
        a, b = make_seeker(), make_seeker()
        TrackedJob.objects.create(user=a, job=self.star)
        TrackedJob.objects.create(user=b, job=self.star, status='applied')
        make_job('Incomplete Job')
        make_job('Old Job', deadline=timezone.localdate() - timedelta(days=5))

    def test_engagement_numbers_are_correct_not_inflated(self):
        r = self.client.get(reverse('admin_listing_insights'))
        row = next(j for j in r.context['top_listings'] if j.pk == self.star.pk)
        self.assertEqual((row.n_views, row.n_saves, row.n_applied, row.save_rate), (4, 2, 1, 50))

    def test_attention_lists(self):
        r = self.client.get(reverse('admin_listing_insights'))
        self.assertIn(self.star.pk, [j.pk for j in r.context['closing_soon']])
        missing = {row['job'].title for row in r.context['needs_attention']}
        self.assertIn('Incomplete Job', missing)
        self.assertNotIn('Star Job', missing)
        self.assertEqual(r.context['summary']['expired_visible'], 1)

    def test_no_job_seeker_names_on_dashboard(self):
        r = self.client.get(reverse('admin_listing_insights'))
        for user in TrackedJob.objects.values_list('user__username', flat=True):
            self.assertPageLacks(r, user)


class JobChangelistTest(WBTestCase):
    def setUp(self):
        super().setUp()
        self.login(make_admin())
        self.soon = make_job('Soon', deadline=timezone.localdate() + timedelta(days=2),
                             qualification_level='degree', experience_level='entry',
                             work_mode='onsite', industry='it', skills=[skill('Excel')])
        self.expired = make_job('Expired', deadline=timezone.localdate() - timedelta(days=2))
        TrackedJob.objects.create(user=make_seeker(), job=self.soon, status='applied')
        self.url = reverse('admin:jobs_job_changelist')

    def listed(self, **params):
        return {o.title for o in self.client.get(self.url, params).context['cl'].result_list}

    def test_saves_and_applied_columns(self):
        row = next(o for o in self.client.get(self.url).context['cl'].result_list if o.pk == self.soon.pk)
        self.assertEqual((row._save_count, row._applied_count), (1, 1))

    def test_filters(self):
        self.assertEqual(self.listed(deadline_status='soon'), {'Soon'})
        self.assertEqual(self.listed(deadline_status='expired'), {'Expired'})
        self.assertEqual(self.listed(filter_fields='complete'), {'Soon'})
        self.assertEqual(self.listed(filter_fields='missing'), {'Expired'})


class BulkActionsTest(WBTestCase):
    def setUp(self):
        super().setUp()
        self.login(make_admin())
        self.job = make_job('Original', industry='it', skills=[skill('SQL')])
        JobApplicationLink.objects.create(job=self.job, title='Stream A', url='https://example.com/a', order=1)

    def act(self, action, jobs):
        return self.client.post(reverse('admin:jobs_job_changelist'),
                                {'action': action, '_selected_action': [j.pk for j in jobs]})

    def test_duplicate_makes_hidden_full_copy(self):
        self.act('duplicate_listings', [self.job])
        copy = Job.objects.get(title='Original (copy)')
        self.assertFalse(copy.is_active, "copies start hidden")
        self.assertEqual(copy.industry, 'it')
        self.assertEqual(list(copy.skills.values_list('name', flat=True)), ['SQL'])
        self.assertEqual(list(copy.application_links.values_list('title', flat=True)), ['Stream A'])
        self.assertTrue(Job.objects.get(pk=self.job.pk).is_active, "original untouched")

    def test_publish_and_hide(self):
        self.act('hide_listings', [self.job])
        self.assertFalse(Job.objects.get(pk=self.job.pk).is_active)
        self.act('publish_listings', [self.job])
        self.assertTrue(Job.objects.get(pk=self.job.pk).is_active)
