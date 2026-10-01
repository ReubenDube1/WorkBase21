"""The AI-leftover scanner: catches leftover assistant phrases and
chat-tool tracking links in listings and articles, names the exact field
and item, stays quiet on clean content, and never changes anything."""
import io

from django.core.management import call_command

from jobs.models import Job, TrendingTopic
from .helpers import WBTestCase, make_company, make_job


def scan():
    out = io.StringIO()
    call_command('scan_ai_leftovers', stdout=out)
    return out.getvalue()


class CleanSiteTest(WBTestCase):
    def test_clean_content_is_not_flagged(self):
        make_job('Clerk', description='<p>We need a reliable clerk with good Excel skills.</p>')
        TrendingTopic.objects.create(title='A real guide', body='<p>Some genuinely useful advice for job seekers.</p>')
        r = scan()
        self.assertIn('Nothing found in any listing.', r)
        self.assertIn('Nothing found in any article.', r)
        self.assertNotIn('⚠', r)

    def test_runs_on_an_empty_site(self):
        r = scan()
        self.assertIn('Nothing found in any listing.', r)
        self.assertIn('Nothing found in any article.', r)


class RealCasesTest(WBTestCase):
    """The two actual listings this was built to catch."""

    def test_catches_the_siemens_style_leftover(self):
        make_job('SAICA Trainee', company=make_company('Siemens'),
                 description2='<p>Next Steps.</p><p>If you need help expanding or polishing '
                              'an application response, let me know!</p>')
        r = scan()
        self.assertIn('⚠', r)
        self.assertIn('Siemens', r)
        self.assertIn('[description2] phrase', r)
        self.assertIn('let me know', r.lower())

    def test_catches_the_microsoft_style_leftover_and_tracking_link(self):
        from jobs.models import JobApplicationLink
        job = make_job(
            'Account Executive', company=make_company('Microsoft'),
            description3='<p>Would you like assistance with any of the following? '
                         '1. Resume Tailoring 2. Cover Letter Generation</p>',
        )
        JobApplicationLink.objects.create(
            job=job, title='Apply Now',
            url='https://apply.careers.microsoft.com/careers?utm_source=chatgpt.com&pid=123', order=1,
        )
        r = scan()
        self.assertIn('Microsoft', r)
        self.assertIn('[description3] phrase', r)
        self.assertIn('tracking link', r)
        self.assertIn('chatgpt', r.lower())


class DetectionCoverageTest(WBTestCase):
    def test_a_range_of_leftover_phrases_are_each_caught(self):
        phrases = [
            "As an AI language model, I cannot browse the internet.",
            "I hope this helps! Let me know if you need anything else.",
            "Here's a draft job description for your review.",
            "Certainly! Here is the listing you asked for.",
            "I apologize, but I don't have access to real-time job boards.",
        ]
        for i, phrase in enumerate(phrases):
            make_job(f'Job {i}', description=f'<p>Real intro text.</p><p>{phrase}</p>')
        r = scan()
        self.assertEqual(r.count('⚠'), len(phrases), "every listing with a leftover phrase should be flagged once")

    def test_ordinary_sentences_dont_trigger_false_positives(self):
        make_job('Support Agent', description=(
            '<p>You will help customers with their accounts and answer queries. '
            'Please note that applicants must have a valid ID. '
            'We offer training and a supportive team environment.</p>'
        ))
        r = scan()
        self.assertIn('Nothing found in any listing.', r)

    def test_chat_tool_domain_in_a_link_is_flagged(self):
        TrendingTopic.objects.create(
            title='Copied article', body='<p>Source: <a href="https://chatgpt.com/share/abc123">chat</a></p>',
        )
        r = scan()
        self.assertIn('chat-tool link', r)


class ReportDetailTest(WBTestCase):
    def test_names_the_exact_field_and_includes_an_edit_link(self):
        job = make_job('Clerk', description5='<p>Would you like me to tailor this further?</p>')
        r = scan()
        self.assertIn('[description5]', r)
        self.assertIn(f'/admin/jobs/job/{job.pk}/change/', r)

    def test_hidden_items_are_included_and_labelled(self):
        make_job('Draft Listing', is_active=False, description='<p>Let me know if this works for you.</p>')
        r = scan()
        self.assertIn('HIDDEN Job: Draft Listing', r)

    def test_application_link_itself_is_checked(self):
        from jobs.models import JobApplicationLink
        job = make_job('Clerk')
        JobApplicationLink.objects.create(job=job, title='Apply', url='https://x.com/?utm_source=claude', order=1)
        r = scan()
        self.assertIn('application link "Apply"', r)


class ReadOnlyTest(WBTestCase):
    def test_changes_nothing(self):
        make_job('Clerk', description='<p>Would you like me to help with this listing?</p>')
        TrendingTopic.objects.create(title='Draft', body='<p>Here is a draft article for you.</p>')
        jobs_before = list(Job.objects.values_list('pk', 'description'))
        articles_before = list(TrendingTopic.objects.values_list('pk', 'body'))
        scan()
        self.assertEqual(jobs_before, list(Job.objects.values_list('pk', 'description')))
        self.assertEqual(articles_before, list(TrendingTopic.objects.values_list('pk', 'body')))
