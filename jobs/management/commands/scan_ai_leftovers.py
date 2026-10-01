"""Scans every listing and article for signs of unedited AI-assistant
output that got pasted straight onto the live site by mistake — phrases
like "Would you like me to..." or a ChatGPT/Claude tracking link left in
an "Apply Now" URL.

    python manage.py scan_ai_leftovers

Read-only: it only looks, it changes nothing. Run it in the Render Shell
and paste the output into the chat.
"""
import re
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.urls import NoReverseMatch, reverse

from jobs.models import Job, TrendingTopic

# Phrases an AI assistant uses when talking TO THE PERSON IT'S CHATTING
# WITH, not to a job seeker reading a published page. Finding any of
# these on a live listing or article is a strong sign it was pasted
# straight from an AI chat without being read first.
LEFTOVER_PHRASES = [
    r"would you like (?:me to|assistance|help)",
    r"need help (?:expanding|polishing|preparing|drafting|tailoring)",
    r"\blet me know\b",
    r"i can help (?:you )?with",
    r"i'd be happy to",
    r"feel free to (?:ask|let me know|reach out)",
    r"is there anything else",
    r"as an ai(?: language model)?\b",
    r"i hope this helps",
    r"here'?s a draft",
    r"here is a draft",
    r"please note that i",
    r"i don'?t have (?:access to|the ability to) real[- ]?time",
    r"as of my (?:last update|knowledge cutoff|training)",
    r"\b(?:sure|certainly|of course)[,!]",
    r"i apologi[sz]e,? but",
]
LEFTOVER_RE = re.compile('(' + '|'.join(LEFTOVER_PHRASES) + ')', re.I | re.M)

# A link containing one of these shows it was copied from an AI chat
# session rather than the employer's own posting.
TRACKING_RE = re.compile(r'utm_source=(chatgpt|openai|claude|anthropic|gemini|bard|copilot)', re.I)
CHAT_DOMAIN_RE = re.compile(r'(chat\.openai\.com|chatgpt\.com|claude\.ai|gemini\.google\.com)', re.I)

TAGS = re.compile(r'<[^>]+>')


def plain(markup):
    import html
    return html.unescape(TAGS.sub(' ', markup or ''))


def snippet(text, match, width=70):
    start = max(0, match.start() - width)
    end = min(len(text), match.end() + width)
    s = ' '.join(text[start:end].split())
    return ('…' if start > 0 else '') + s + ('…' if end < len(text) else '')


class Command(BaseCommand):
    help = "Find leftover AI-assistant text or chat-tool tracking links in live listings/articles (read-only)."

    def handle(self, *args, **options):
        w = self.stdout.write
        w("WORKBASE21 — SCAN FOR LEFTOVER AI-ASSISTANT TEXT")
        w("=" * 60)

        found_any = False
        found_any |= self.scan_jobs(w)
        found_any |= self.scan_articles(w)

        w("")
        w("=" * 60)
        if found_any:
            w(self.style.WARNING("Review every item above in the admin, remove the leftover "
                                 "text/link, and re-run this scan until it comes back clean."))
        else:
            w(self.style.SUCCESS("Nothing matched. (This checks a fixed list of common phrases — "
                                 "it can miss wording outside that list, so it's not a guarantee.)"))

    def admin_link(self, name, pk):
        try:
            return reverse(name, args=[pk])
        except NoReverseMatch:
            return ''

    def check_item(self, w, label, admin_url, blocks_with_names):
        """blocks_with_names: list of (field_name, html). Returns True if
        anything was flagged for this item."""
        hits = defaultdict(list)
        for field_name, markup in blocks_with_names:
            if not markup:
                continue
            text = plain(markup)
            for m in LEFTOVER_RE.finditer(text):
                hits[field_name].append(('phrase', snippet(text, m)))
            for m in TRACKING_RE.finditer(markup):
                hits[field_name].append(('tracking link', f"...utm_source={m.group(1)}..."))
            for m in CHAT_DOMAIN_RE.finditer(markup):
                hits[field_name].append(('chat-tool link', snippet(markup, m)))

        if not hits:
            return False

        w("")
        w(f"⚠ {label}")
        if admin_url:
            w(f"  Edit: {admin_url}")
        for field_name, items in hits.items():
            for kind, text in items:
                w(f"  [{field_name}] {kind}: {text}")
        return True

    def scan_jobs(self, w):
        w("")
        w("LISTINGS")
        w("-" * 60)
        any_hit = False
        jobs = Job.objects.all().select_related('company').order_by('-created_at')
        for j in jobs:
            blocks = [
                ('description', j.description), ('description2', j.description2),
                ('description3', j.description3), ('description4', j.description4),
                ('description5', j.description5),
            ]
            # The Apply Now link itself isn't stored on the Job model as HTML,
            # but application links are — check those too.
            for link in j.application_links.all():
                blocks.append((f'application link "{link.title}"', f'<a href="{link.url}">'))
            label = f'{"HIDDEN " if not j.is_active else ""}Job: {j.title} ({j.company.name})'
            any_hit |= self.check_item(w, label, self.admin_link('admin:jobs_job_change', j.pk), blocks)
        if not any_hit:
            w("Nothing found in any listing.")
        return any_hit

    def scan_articles(self, w):
        w("")
        w("ARTICLES")
        w("-" * 60)
        any_hit = False
        articles = TrendingTopic.objects.all().order_by('-created_at')
        for a in articles:
            blocks = [(f'body{n or ""}', getattr(a, f'body{n}' if n else 'body'))
                     for n in ('', 2, 3, 4, 5)]
            label = f'{"HIDDEN " if not a.is_active else ""}Article: {a.title}'
            any_hit |= self.check_item(w, label, self.admin_link('admin:jobs_trendingtopic_change', a.pk), blocks)
        if not any_hit:
            w("Nothing found in any article.")
        return any_hit
