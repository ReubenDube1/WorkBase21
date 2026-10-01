"""The ready-made draft articles: created hidden, substantial, free of
placeholder text, with working internal links; the command never overwrites
existing articles and can be re-run safely."""
import io
import re

from django.core.management import call_command
from django.urls import reverse

from jobs.management.commands.seed_article_drafts import DRAFTS
from jobs.models import TrendingTopic
from .helpers import WBTestCase, make_admin


def words(html):
    return len(re.sub(r'<[^>]+>', ' ', html).split())


def run():
    out = io.StringIO()
    call_command('seed_article_drafts', stdout=out)
    return out.getvalue()


class DraftContentTest(WBTestCase):
    def test_every_draft_is_substantial_and_clean(self):
        self.assertGreaterEqual(len(DRAFTS), 3)
        for d in DRAFTS:
            with self.subTest(article=d['title']):
                self.assertGreaterEqual(words(d['body']), 650, "articles should be genuinely in-depth")
                self.assertGreaterEqual(len(re.findall(r'<h2>', d['body'])), 4, "needs clear sections")
                self.assertLessEqual(len(d['description']), 250, "card text limit")
                self.assertLessEqual(len(d['icon']), 10)
                for bad in ('lorem', 'placeholder', 'TODO', 'XXX', 'seed_demo_data'):
                    self.assertNotIn(bad.lower(), d['body'].lower())

    def test_internal_links_all_work(self):
        links = {href for d in DRAFTS for href in re.findall(r'href="(/[^"]*)"', d['body'])}
        self.assertGreater(len(links), 3)
        for href in sorted(links):
            with self.subTest(link=href):
                self.assertEqual(self.client.get(href).status_code, 200)


class DraftCommandTest(WBTestCase):
    def test_creates_hidden_drafts_nothing_public(self):
        out = run()
        self.assertIn(f'{len(DRAFTS)} draft article(s) created', out)
        for d in DRAFTS:
            article = TrendingTopic.objects.get(title=d['title'])
            self.assertFalse(article.is_active, "drafts must start hidden")
            self.assertEqual(article.body, d['body'].strip())
            self.assertEqual(self.client.get(article.get_absolute_url()).status_code, 404,
                             "a hidden draft must not be visible to the public")
        self.assertNotIn(DRAFTS[0]['title'], self.client.get(reverse('trending_list')).content.decode())
        self.assertNotIn(TrendingTopic.objects.get(title=DRAFTS[0]['title']).slug,
                         self.client.get(reverse('sitemap')).content.decode())

    def test_publishing_a_draft_makes_it_live(self):
        run()
        article = TrendingTopic.objects.get(title=DRAFTS[1]['title'])
        TrendingTopic.objects.filter(pk=article.pk).update(is_active=True)
        r = self.client.get(article.get_absolute_url())
        self.assertEqual(r.status_code, 200)
        self.assertIn('<h2>', r.content.decode())
        self.assertIn(article.slug, self.client.get(reverse('sitemap')).content.decode())

    def test_safe_to_rerun_and_never_overwrites(self):
        run()
        TrendingTopic.objects.filter(title=DRAFTS[0]['title']).update(body='<p>MY OWN EDITED VERSION</p>', is_active=True)
        out = run()
        self.assertIn('0 draft article(s) created', out)
        self.assertEqual(TrendingTopic.objects.filter(title=DRAFTS[0]['title']).count(), 1)
        edited = TrendingTopic.objects.get(title=DRAFTS[0]['title'])
        self.assertEqual(edited.body, '<p>MY OWN EDITED VERSION</p>')
        self.assertTrue(edited.is_active, "a published article must stay published")

    def test_skips_an_article_you_already_wrote_with_the_same_title(self):
        mine = TrendingTopic.objects.create(title=DRAFTS[2]['title'].upper(), body='<p>Mine</p>')
        run()
        self.assertEqual(TrendingTopic.objects.filter(title__iexact=DRAFTS[2]['title']).count(), 1)
        mine.refresh_from_db()
        self.assertEqual(mine.body, '<p>Mine</p>')

    def test_drafts_open_in_the_admin_editor(self):
        run()
        self.login(make_admin())
        article = TrendingTopic.objects.get(title=DRAFTS[0]['title'])
        r = self.client.get(reverse('admin:jobs_trendingtopic_change', args=[article.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertIn('vendor/tinymce/tinymce', r.content.decode())
