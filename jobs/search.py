"""Shared job search/filter logic.

Used by the listing pages (Jobs, Internships, Learnerships, Bursaries,
Search) AND by saved-search job alerts, so a saved search always finds
exactly what the same search on the site would find.
"""
from django.db.models import Q

FILTER_PARAMS = (
    'qualification', 'experience', 'work_mode', 'industry', 'skill',
    'salary_min',
)


def keyword_filter(queryset, query):
    return queryset.filter(
        Q(title__icontains=query) |
        Q(description__icontains=query) |
        Q(company__name__icontains=query) |
        Q(location__icontains=query) |
        Q(type__icontains=query)
    ).distinct()


def apply_filter_params(params, queryset):
    """Applies whichever advanced-search filters are present in
    `params` (request.GET or a plain dict). Every filter is optional
    and additive — an unfilled filter simply doesn't narrow results.
    Returns (queryset, active_filters_dict)."""
    active = {}

    qualification = params.get('qualification', '')
    if qualification:
        queryset = queryset.filter(qualification_level=qualification)
        active['qualification'] = qualification

    experience = params.get('experience', '')
    if experience:
        queryset = queryset.filter(experience_level=experience)
        active['experience'] = experience

    work_mode = params.get('work_mode', '')
    if work_mode:
        queryset = queryset.filter(work_mode=work_mode)
        active['work_mode'] = work_mode

    industry = params.get('industry', '')
    if industry:
        queryset = queryset.filter(industry=industry)
        active['industry'] = industry

    skill = params.get('skill', '')
    if skill:
        queryset = queryset.filter(skills__slug=skill)
        active['skill'] = skill

    salary_min = str(params.get('salary_min', ''))
    if salary_min.isdigit():
        queryset = queryset.filter(salary_min__gte=int(salary_min))
        active['salary_min'] = salary_min

    return queryset.distinct(), active
