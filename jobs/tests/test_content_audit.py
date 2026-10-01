"""The content audit finds thin pages, duplicates and placeholder text, never
changes anything, and copes with an empty site."""
import io

from django.core.management import call_command

from jobs.models import Job, TrendingTopic
from .helpers import WBTestCase, make_company, make_job


def audit():
    out = io.StringIO()
    call_command('content_audit', stdout=out)
    return out.getvalue()


class AuditTestCase(WBTestCase):
    """Starts with no articles: the project's own migrations create one
    ("How to Verify a Remote Job...") in every new database."""

    def setUp(self):
        super().setUp()
        TrendingTopic.objects.all().delete()


def long_text(n, seed='word'):
    return '<p>' + ' '.join(f'{seed}{i}' for i in range(n)) + '</p>'


class EmptySiteTest(AuditTestCase):
    def test_runs_on_an_empty_site(self):
        report = audit()
        self.assertIn('No published articles.', report)
        self.assertIn('No active listings.', report)


class ArticleAuditTest(AuditTestCase):
    def setUp(self):
        super().setUp()
        TrendingTopic.objects.create(title='A thorough guide', body='<h2>One</h2>' + long_text(900, 'a'))
        TrendingTopic.objects.create(title='A tiny note', body='<p>Just a few words here.</p>')
        TrendingTopic.objects.create(title='Sample with placeholder', body=long_text(600, 'b') + '<p>This is placeholder text.</p>')
        TrendingTopic.objects.create(title='Pictures guide', body=long_text(520, 'c') +
                                    '<img src="/media/x.jpg"><img src="/media/y.jpg" alt="A described picture">')
        TrendingTopic.objects.create(title='Draft not live', body=long_text(700, 'd'), is_active=False)
        TrendingTopic.objects.create(title='Stat card only', body='')

    def test_counts_and_flags(self):
        r = audit()
        self.assertIn('4 published, 1 hidden drafts, 1 homepage stat cards', r)
        self.assertRegex(r, r'\d+ \| +\d+ \| +\d+ \| A tiny note +<- THIN')
        self.assertIn('PLACEHOLDER TEXT', r)
        self.assertIn('1 image(s) without alt text', r)
        self.assertIn('Duplicate titles: none.', r)

    def test_drafts_and_stat_cards_are_not_listed_as_published(self):
        r = audit()
        self.assertNotIn('Draft not live  ', r)
        self.assertNotIn('Stat card only  ', r)

    def test_duplicate_titles_and_identical_text_found(self):
        body = '<h2>Same</h2>' + long_text(700, 'same')
        TrendingTopic.objects.create(title='How to Verify a Remote Job Before You Apply', body=body)
        TrendingTopic.objects.create(title='how to verify a remote job, before you apply!', body=body)
        r = audit()
        self.assertIn('DUPLICATE TITLES', r)
        self.assertIn('x2', r)
        self.assertIn('IDENTICAL TEXT on different articles', r)

    def test_read_only(self):
        before = list(TrendingTopic.objects.values_list('pk', 'title', 'body', 'is_active'))
        audit()
        self.assertEqual(before, list(TrendingTopic.objects.values_list('pk', 'title', 'body', 'is_active')))


class ListingAuditTest(WBTestCase):
    def test_lengths_duplicates_and_placeholders(self):
        co = make_company('Acme')
        make_job('Short ad', company=co, description='<p>Apply now.</p>')
        make_job('Solid ad', company=co, description=long_text(300, 'x'))
        make_job('Empty ad', company=co, description='')
        make_job('Clerk', company=co, description=long_text(200, 'same'))
        make_job('Clerk', company=co, description=long_text(200, 'same'))
        make_job('Has placeholder', company=co, description='<p>placeholder text</p>' + long_text(150, 'p'))
        make_job('Hidden one', company=co, is_active=False, description='')
        r = audit()
        self.assertIn('LISTINGS  (6 active, 1 hidden)', r)
        self.assertIn('no description: 1', r)
        self.assertIn('under 120 words: 1', r)
        self.assertIn('SAME TITLE + COMPANY listed more than once: 1 group', r)
        self.assertIn('IDENTICAL DESCRIPTION TEXT shared by several listings: 1 group', r)
        self.assertIn('Listings containing placeholder text: 1', r)
        self.assertIn('Short ad', r.split('Shortest 10 listings')[1])
        self.assertNotIn('Hidden one', r)

    def test_read_only(self):
        make_job('One', description='<p>text</p>')
        before = list(Job.objects.values_list('pk', 'title', 'description', 'is_active'))
        audit()
        self.assertEqual(before, list(Job.objects.values_list('pk', 'title', 'description', 'is_active')))


class MigrationArticleTest(WBTestCase):
    def test_the_built_in_article_is_included_and_measured(self):
        """The data migration's article exists in every database (including
        your live one). The audit should see it, and flag it as thin."""
        r = audit()
        self.assertIn('How to Verify a Remote Job Before You Apply', r)
        self.assertRegex(r, r'How to Verify a Remote Job Before You Apply +<- THIN')
