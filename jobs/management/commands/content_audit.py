"""Content audit: how substantial and original is the published content?

    python manage.py content_audit

Prints a plain-text report you can paste into a chat or save. It looks for
the usual causes of Google AdSense's "low-value content" verdict:

  * articles and listings that are very short ("thin")
  * duplicate titles, and different pages with identical text
  * leftover placeholder text
  * images without alt text, articles with no headings or links

It only READS the database and contains no personal information about
job seekers. Run it on the live site from the Render Shell.
"""
import hashlib
import html
import re
import statistics
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.utils import timezone

from jobs.models import Job, TrendingTopic

THIN_ARTICLE, SHORT_ARTICLE = 500, 800
THIN_LISTING, SHORT_LISTING = 120, 250

TAGS = re.compile(r'<[^>]+>')
PLACEHOLDER = re.compile(
    r'\b(lorem ipsum|placeholder|seed_demo_data|replace (?:it|this) with|coming soon|under construction)\b', re.I)
IMG = re.compile(r'<img\b[^>]*>', re.I)
IMG_WITH_ALT = re.compile(r'\balt\s*=\s*"[^"\s][^"]*"', re.I)
HREF = re.compile(r'<a\b[^>]*\bhref\s*=\s*"([^"]*)"', re.I)
HEADING = re.compile(r'<h[2-4]\b', re.I)


def text_of(markup):
    return ' '.join(html.unescape(TAGS.sub(' ', markup or '')).split())


def word_count(markup):
    return len(text_of(markup).split())


def normalise(s):
    return ' '.join(re.sub(r'[^a-z0-9 ]+', ' ', (s or '').lower()).split())


def fingerprint(markup):
    t = normalise(text_of(markup))
    return hashlib.md5(t.encode()).hexdigest() if len(t) > 40 else None


def short(s, n=62):
    s = ' '.join((s or '').split())
    return s if len(s) <= n else s[:n - 1] + '…'


def bucket(n, thin, short_):
    return 'thin' if n < thin else ('short' if n < short_ else 'ok')


class Command(BaseCommand):
    help = "Report on thin, duplicate and placeholder content (read-only)."

    def handle(self, *args, **options):
        w = self.stdout.write
        today = timezone.localdate()
        w(f"WORKBASE21 CONTENT AUDIT — {today:%d %b %Y}")
        w("=" * 60)
        self.audit_articles(w)
        self.audit_listings(w, today)
        w("")
        w("Paste everything above into the chat for specific advice.")

    # ------------------------------------------------------------------
    def audit_articles(self, w):
        published = list(TrendingTopic.objects.filter(is_active=True).exclude(body='').order_by('created_at'))
        drafts = TrendingTopic.objects.filter(is_active=False).exclude(body='').count()
        cards = TrendingTopic.objects.filter(is_active=True, body='').count()
        w("")
        w(f"ARTICLES  ({len(published)} published, {drafts} hidden drafts, {cards} homepage stat cards with no article)")
        w("-" * 60)
        if not published:
            w("No published articles.")
            return

        rows = []
        titles = defaultdict(list)
        prints = defaultdict(list)
        for a in published:
            blocks = a.body_blocks
            markup = ' '.join(blocks)
            n_words = word_count(markup)
            imgs = IMG.findall(markup)
            no_alt = sum(1 for i in imgs if not IMG_WITH_ALT.search(i))
            hrefs = HREF.findall(markup)
            internal = sum(1 for h in hrefs if h.startswith('/') or 'workbase21' in h)
            flags = []
            if bucket(n_words, THIN_ARTICLE, SHORT_ARTICLE) == 'thin':
                flags.append(f'THIN (<{THIN_ARTICLE} words)')
            elif bucket(n_words, THIN_ARTICLE, SHORT_ARTICLE) == 'short':
                flags.append('short')
            if PLACEHOLDER.search(text_of(markup)):
                flags.append('PLACEHOLDER TEXT')
            if not HEADING.search(markup) and n_words > 300:
                flags.append('no headings')
            if no_alt:
                flags.append(f'{no_alt} image(s) without alt text')
            rows.append((a, n_words, len(imgs) + (1 if a.image else 0), len(hrefs), internal, flags))
            titles[normalise(a.title)].append(a)
            fp = fingerprint(markup)
            if fp:
                prints[fp].append(a)

        counts = [r[1] for r in rows]
        w(f"Words per article: median {int(statistics.median(counts))}, shortest {min(counts)}, longest {max(counts)}, "
          f"total {sum(counts):,}")
        thin = [r for r in rows if r[1] < THIN_ARTICLE]
        short_ = [r for r in rows if THIN_ARTICLE <= r[1] < SHORT_ARTICLE]
        w(f"Under {THIN_ARTICLE} words: {len(thin)}   |   {THIN_ARTICLE}-{SHORT_ARTICLE - 1} words: {len(short_)}   |   "
          f"{SHORT_ARTICLE}+ words: {len(rows) - len(thin) - len(short_)}")
        w(f"With at least one picture: {sum(1 for r in rows if r[2])} of {len(rows)}   |   "
          f"with an internal link: {sum(1 for r in rows if r[4])} of {len(rows)}")
        w("")
        w("Shortest first:   words | pics | links | title")
        for a, n_words, pics, links, internal, flags in sorted(rows, key=lambda r: r[1]):
            note = f"   <- {'; '.join(flags)}" if flags else ''
            w(f"  {n_words:5} | {pics:4} | {links:5} | {short(a.title)}{note}")

        dup_titles = [v for v in titles.values() if len(v) > 1]
        dup_text = [v for v in prints.values() if len(v) > 1]
        w("")
        if dup_titles:
            w("DUPLICATE TITLES (same title on more than one article — remove or rename one):")
            for group in dup_titles:
                w(f"  - {short(group[0].title, 70)}  x{len(group)}  (created: "
                  + ', '.join(f'{g.created_at:%d %b %Y}' for g in group) + ")")
        else:
            w("Duplicate titles: none.")
        if dup_text:
            w("IDENTICAL TEXT on different articles:")
            for group in dup_text:
                w("  - " + ' / '.join(short(g.title, 40) for g in group))
        else:
            w("Identical text on different articles: none.")

    # ------------------------------------------------------------------
    def audit_listings(self, w, today):
        everything = Job.objects.all()
        active = list(Job.objects.filter(is_active=True).select_related('company'))
        w("")
        w(f"LISTINGS  ({len(active)} active, {everything.filter(is_active=False).count()} hidden)")
        w("-" * 60)
        if not active:
            w("No active listings.")
            return

        by_type = defaultdict(int)
        for j in active:
            by_type[j.type_label] += 1
        w("By type: " + ', '.join(f"{k} {v}" for k, v in sorted(by_type.items())))
        expired = sum(1 for j in active if j.deadline and j.deadline < today)
        w(f"Past their deadline but still shown: {expired} of {len(active)}")

        metrics = []
        titles = defaultdict(list)
        prints = defaultdict(list)
        for j in active:
            markup = ' '.join(j.description_blocks)
            n_words = word_count(markup)
            metrics.append((j, n_words))
            titles[(normalise(j.title), normalise(j.company.name))].append(j)
            fp = fingerprint(markup)
            if fp:
                prints[fp].append(j)

        counts = [m[1] for m in metrics]
        none = sum(1 for c in counts if c == 0)
        thin = sum(1 for c in counts if 0 < c < THIN_LISTING)
        short_ = sum(1 for c in counts if THIN_LISTING <= c < SHORT_LISTING)
        good = len(counts) - none - thin - short_
        w(f"Description length: median {int(statistics.median(counts))} words")
        w(f"  no description: {none}   |   under {THIN_LISTING} words: {thin}   |   "
          f"{THIN_LISTING}-{SHORT_LISTING - 1}: {short_}   |   {SHORT_LISTING}+ words: {good}")

        weakest = sorted(metrics, key=lambda m: m[1])[:10]
        w("")
        w("Shortest 10 listings:   words | title (company)")
        for j, n_words in weakest:
            w(f"  {n_words:5} | {short(j.title, 48)} ({short(j.company.name, 24)})")

        dup = [v for v in titles.values() if len(v) > 1]
        same_text = [v for v in prints.values() if len(v) > 1]
        w("")
        if dup:
            w(f"SAME TITLE + COMPANY listed more than once: {len(dup)} group(s)")
            for g in dup[:8]:
                w(f"  - {short(g[0].title, 50)} ({short(g[0].company.name, 24)}) x{len(g)}")
        else:
            w("Same title + company listed twice: none.")
        if same_text:
            w(f"IDENTICAL DESCRIPTION TEXT shared by several listings: {len(same_text)} group(s)")
            for g in same_text[:8]:
                w("  - " + ' / '.join(short(x.title, 30) for x in g[:3]) + (f" … ({len(g)} listings)" if len(g) > 3 else ''))
        else:
            w("Identical description text on different listings: none.")

        placeholder = [j for j, _ in metrics if PLACEHOLDER.search(text_of(' '.join(j.description_blocks)))]
        w(f"Listings containing placeholder text: {len(placeholder)}")
        for j in placeholder[:5]:
            w(f"  - {short(j.title, 60)}")

        missing = sum(1 for j in active if not (j.qualification_level and j.experience_level and j.work_mode and j.industry))
        w(f"Listings missing some search-filter details: {missing} of {len(active)}")
