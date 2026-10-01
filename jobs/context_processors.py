from django.conf import settings


def job_types(request):
    """Makes the navbar links and site-wide info available in every
    template without passing it from each view."""
    return {
        'nav_job_types': [
            {'slug': 'jobs', 'label': 'Jobs'},
            {'slug': 'internships', 'label': 'Internships'},
            {'slug': 'learnerships', 'label': 'Learnerships'},
            {'slug': 'careers', 'label': 'Careers'},
            {'slug': 'trending_list', 'label': 'Blog'},
            {'slug': 'bursaries', 'label': 'Bursaries'},
        ],
        'SITE_NAME': settings.SITE_NAME,
        'SITE_DOMAIN': settings.SITE_DOMAIN,
        'SITE_EMAIL': settings.SITE_EMAIL,
        'SITE_DESCRIPTION': settings.SITE_DESCRIPTION,
    }


def filter_choices(request):
    """The advanced-search filter dropdown options, available on every
    template so the filter bar partial can be included on any listing
    page without each view having to pass it in."""
    from .models import Job, Skill
    return {
        'qualification_choices': Job.QUALIFICATION_CHOICES,
        'experience_choices': Job.EXPERIENCE_CHOICES,
        'work_mode_choices': Job.WORK_MODE_CHOICES,
        'industry_choices': Job.INDUSTRY_CHOICES,
        'all_skills': Skill.objects.filter(jobs__is_active=True).distinct(),
    }


# --- SEO + advertising rules, decided per page ------------------------------
# Google asks publishers not to show ads on pages without real content
# (login/sign-up forms, search results, account pages, contact forms), and
# search engines shouldn't index those pages either. Deciding it here, in one
# place, means every current and future page follows the same rules.
import re as _re

NOINDEX_PREFIXES = ('/accounts/', '/search/', '/recommended/')
NO_ADS_PREFIXES = NOINDEX_PREFIXES + ('/contact/', '/admin/')
_NO_ADS_PATTERNS = (_re.compile(r'^/job/\d+/(eligibility|save)/'),)


def seo_flags(request):
    path = request.path
    noindex = path.startswith(NOINDEX_PREFIXES)
    no_ads = path.startswith(NO_ADS_PREFIXES) or any(p.match(path) for p in _NO_ADS_PATTERNS)
    return {'seo_noindex': noindex, 'show_ads': not no_ads}
