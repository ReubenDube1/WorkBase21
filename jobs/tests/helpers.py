"""Shared building blocks for the WorkBase21 tests: quick ways to create
realistic companies, listings, job seekers and admins in the temporary
test database (never the real one)."""
from datetime import timedelta
import itertools

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from jobs.models import Company, Job, Skill

PASSWORD = 'TestPass!2345'
_counter = itertools.count(1)


def make_company(name=None):
    return Company.objects.create(name=name or f"Company {next(_counter)}")


def make_job(title=None, company=None, **fields):
    defaults = dict(
        title=title or f"Job {next(_counter)}",
        company=company or make_company(),
        type=Job.JOB,
        sector=Job.PRIVATE,
        location='Johannesburg, Gauteng',
        description='<p>Great opportunity.</p>',
        deadline=timezone.localdate() + timedelta(days=30),
        is_active=True,
    )
    defaults.update(fields)
    skills = defaults.pop('skills', None)
    job = Job.objects.create(**defaults)
    if skills:
        job.skills.set(skills)
    return job


def skill(name):
    return Skill.objects.filter(name__iexact=name).first() or Skill.objects.create(name=name)


def make_seeker(username=None, email=None, **profile_fields):
    from accounts.models import UserProfile
    username = username or f"seeker{next(_counter)}"
    user = User.objects.create_user(username, email or f"{username}@example.com", PASSWORD)
    skills = profile_fields.pop('skills', None)
    profile = UserProfile.objects.create(user=user, **profile_fields)
    if skills:
        profile.skills.set(skills)
    return user


def make_admin(username='boss', superuser=True):
    if superuser:
        return User.objects.create_superuser(username, f"{username}@example.com", PASSWORD)
    return User.objects.create_user(username, f"{username}@example.com", PASSWORD, is_staff=True)


class WBTestCase(TestCase):
    """Base class: clears the rate-limit memory before every test so tests
    never affect each other."""

    def setUp(self):
        cache.clear()

    def login(self, user):
        self.client.force_login(user)
        return self.client

    # Short, readable failure messages (Django's own assertContains prints
    # the whole page's HTML when it fails, which is hard to read).
    def assertPageHas(self, response, text):
        path = response.request.get('PATH_INFO', '')
        self.assertTrue(text in response.content.decode(),
                        f"Expected to see {text!r} on {path}, but it wasn't there.")

    def assertPageLacks(self, response, text):
        path = response.request.get('PATH_INFO', '')
        self.assertFalse(text in response.content.decode(),
                         f"{text!r} should NOT appear on {path}, but it does.")

