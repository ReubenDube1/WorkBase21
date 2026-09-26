import logging
import smtplib

from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
from django.core.mail import EmailMessage
from django.core.paginator import Paginator
from django.db.models import Q, Case, When, Value, BooleanField, Count
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.conf import settings

from . import matching
from .throttle import client_ip, over_limit
from .search import FILTER_PARAMS, apply_filter_params, keyword_filter
from .models import Job, Review, TrendingTopic, Skill
from .forms import ContactForm

logger = logging.getLogger(__name__)

JOBS_PER_PAGE = 9
HOMEPAGE_JOBS_LIMIT = 16
HOMEPAGE_ARTICLES_LIMIT = 16



def _with_expired_flag(queryset):
    """Annotates a Job queryset with `_expired` and orders live listings
    first, newest first within each group.

    Listings are kept visible after their deadline passes instead of
    disappearing — this keeps the site's page count and content depth
    up (helpful for search engines and ad review) while still making
    it obvious to job seekers, via the 'Expired' styling already in
    the templates, which listings are still open."""
    return queryset.annotate(
        _expired=Case(
            When(deadline__lt=timezone.localdate(), then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    ).order_by('_expired', '-created_at')


def _not_expired_q():
    """Used only for the 'X open listings' counts on the sector-choice
    page — those should reflect what's still open, even though the
    listing pages themselves now also show expired jobs."""
    return Q(deadline__gte=timezone.localdate()) | Q(deadline__isnull=True)

# Maps a URL-friendly slug to the value stored in Job.type,
# plus the heading shown on that page. ('jobs' is handled separately
# below since it now has its own Public/Private sector split.)
TYPE_MAP = {
    'internships': {'value': Job.INTERNSHIP, 'title': 'Internships', 'blurb': 'Kick-start your career with hands-on experience.'},
    'learnerships': {'value': Job.LEARNERSHIP, 'title': 'Learnerships', 'blurb': 'Structured learning combined with real workplace experience.'},
    'bursaries': {'value': Job.BURSARY, 'title': 'Bursaries', 'blurb': 'Funding opportunities to help you study further.'},
}

SECTOR_INFO = {
    Job.PUBLIC: {
        'title': 'Public Sector Jobs',
        'blurb': 'Government departments, state-owned entities and municipalities.',
    },
    Job.PRIVATE: {
        'title': 'Private Sector Jobs',
        'blurb': 'Roles at companies and organisations across every industry.',
    },
}


def _paginate(request, queryset, per_page=JOBS_PER_PAGE):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def _apply_filters(request, queryset):
    return apply_filter_params(request.GET, queryset)


def _querystring_without_page(request):
    """The current querystring minus 'page' — used so pagination links
    (and the 'clear filters' link) carry every active filter/search
    term forward instead of resetting them."""
    params = request.GET.copy()
    params.pop('page', None)
    return params.urlencode()


def _active_jobs():
    """Every published listing, expired or not — is_active is the
    admin's manual publish/unpublish toggle and is respected; a job's
    deadline having passed no longer hides it from the site."""
    return _with_expired_flag(
        Job.objects.filter(is_active=True).select_related('company')
    )


def welcome(request):
    """Home page: hero search bar, latest listings, trending topics and
    reviews from job seekers / partner organisations."""
    context = {
        'home_jobs': _active_jobs()[:HOMEPAGE_JOBS_LIMIT],
        'page_title': 'Find Your Next Opportunity',
        'meta_description': (
            "Browse jobs, internships, learnerships and bursaries "
            "across South Africa on WorkBase21."
        ),
        'trending_topics': TrendingTopic.objects.filter(is_active=True)[:HOMEPAGE_ARTICLES_LIMIT],
        'reviews': Review.objects.filter(is_published=True)[:6],
    }
    return render(request, 'welcome.html', context)


def jobs_sector_choice(request):
    """The 'Jobs' nav link now leads here first, so job seekers can pick
    Public Sector or Private Sector before seeing listings."""
    today = timezone.localdate()
    public_count = Job.objects.filter(
        _not_expired_q(), type=Job.JOB, sector=Job.PUBLIC, is_active=True
    ).count()
    private_count = Job.objects.filter(
        _not_expired_q(), type=Job.JOB, sector=Job.PRIVATE, is_active=True
    ).count()
    context = {
        'page_title': 'Jobs',
        'meta_description': 'Choose between Public Sector and Private Sector jobs on WorkBase21.',
        'public_count': public_count,
        'private_count': private_count,
    }
    return render(request, 'jobs_sector_choice.html', context)


def job_list_by_sector(request, sector):
    """Listing page for Jobs filtered to Public Sector or Private Sector."""
    info = SECTOR_INFO[sector]
    jobs_qs = _with_expired_flag(
        Job.objects.filter(
            type=Job.JOB, sector=sector, is_active=True,
        ).select_related('company')
    )
    jobs_qs, active_filters = _apply_filters(request, jobs_qs)
    page_obj = _paginate(request, jobs_qs)
    context = {
        'page_obj': page_obj,
        'page_title': info['title'],
        'page_blurb': info['blurb'],
        'active_type': 'jobs',
        'active_sector': sector,
        'meta_description': f"{info['blurb']} Apply today on WorkBase21.",
        'active_filters': active_filters,
        'search_scope': {'job_type': Job.JOB, 'sector': sector},
        'can_save_search': True,
        'extra_qs': _querystring_without_page(request),
    }
    return render(request, 'job_sector_list.html', context)


def job_list_by_type(request, job_type):
    """Shared view for Internships / Learnerships / Bursaries — each just filters on a different `type` value."""
    info = TYPE_MAP[job_type]
    jobs_qs = _with_expired_flag(
        Job.objects.filter(
            type=info['value'], is_active=True,
        ).select_related('company')
    )
    jobs_qs, active_filters = _apply_filters(request, jobs_qs)
    page_obj = _paginate(request, jobs_qs)
    context = {
        'page_obj': page_obj,
        'page_title': info['title'],
        'page_blurb': info['blurb'],
        'active_type': job_type,
        'meta_description': f"{info['blurb']} Apply today on WorkBase21.",
        'active_filters': active_filters,
        'search_scope': {'job_type': info['value'], 'sector': ''},
        'can_save_search': True,
        'extra_qs': _querystring_without_page(request),
    }
    template_map = {
        'internships': 'internships.html',
        'learnerships': 'learnerships.html',
        'bursaries': 'bursary.html',
    }
    return render(request, template_map[job_type], context)


@login_required
def recommended_jobs(request):
    """'Recommended for you' — a personalized feed built entirely from
    the same rules-based matching engine as the eligibility checker.
    Explains why each job appears rather than just listing them."""
    from accounts.models import UserProfile

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile_has_data = bool(
        profile.qualification_level or profile.experience_level
        or profile.location or profile.skills.exists()
    )

    recommendations = []
    if profile_has_data:
        active_jobs = Job.objects.filter(is_active=True).select_related(
            'company'
        ).prefetch_related('skills')
        recommendations = matching.recommend_jobs(profile, active_jobs, limit=12)

    return render(request, 'recommended_jobs.html', {
        'recommendations': recommendations,
        'profile_has_data': profile_has_data,
        'page_title': 'Recommended For You',
        'meta_description': 'Jobs matched to your WorkBase21 profile.',
    })


@login_required
def job_eligibility(request, pk):
    """Rules-based, transparent comparison of the logged-in job
    seeker's profile against this listing's stated requirements. Never
    predicts whether the employer will accept or reject anyone —
    just reports what matches, what doesn't, and what couldn't be
    checked because a field is blank on either side."""
    from accounts.models import UserProfile

    job = get_object_or_404(
        Job.objects.select_related('company').prefetch_related('skills'), pk=pk
    )
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    result = matching.check_eligibility(profile, job)

    return render(request, 'eligibility_result.html', {
        'job': job,
        'profile': profile,
        'result': result,
        'page_title': f'Eligibility Check — {job.title}',
    })


def job_detail(request, pk, slug):
    job = get_object_or_404(Job.objects.select_related('company'), pk=pk)

    # Hidden (inactive) listings are 404 for the public — including
    # drafts made with the admin's Duplicate action. Staff can still
    # open them as a preview (the template shows a 'hidden' banner).
    if not job.is_active and not request.user.is_staff:
        raise Http404("Listing not found")

    # Keep URLs canonical for SEO/sharing — if someone hits an outdated
    # or hand-edited slug (e.g. the job title or company name changed
    # since the link was shared), redirect permanently to the current
    # correct URL rather than silently serving it under a stale slug.
    if slug != job.slug:
        return redirect(job.get_absolute_url(), permanent=True)

    related_jobs = _with_expired_flag(
        Job.objects.filter(type=job.type, is_active=True)
        .exclude(pk=job.pk).select_related('company')
    )[:4]

    tracked = None
    if request.user.is_authenticated:
        from accounts.models import TrackedJob
        tracked = TrackedJob.objects.filter(user=request.user, job=job).first()

    context = {
        'job': job,
        'related_jobs': related_jobs,
        'tracked': tracked,
        'page_title': f"{job.title} at {job.company.name}",
        'meta_description': (
            f"{job.title} at {job.company.name} in {job.location}. "
            f"Apply before {job.deadline_display} on WorkBase21."
        ),
    }
    return render(request, 'job_detail.html', context)


def job_detail_legacy_redirect(request, pk):
    """Old links used /job/<pk>/ with no slug. Keep those working by
    redirecting permanently to the current canonical URL, instead of
    breaking any links already shared or indexed."""
    job = get_object_or_404(Job, pk=pk)
    if not job.is_active and not request.user.is_staff:
        raise Http404("Listing not found")
    return redirect(job.get_absolute_url(), permanent=True)


def search_results(request):
    query = request.GET.get('q', '').strip()
    jobs_qs = Job.objects.none()
    active_filters = {}

    if query:
        jobs_qs = _with_expired_flag(
            keyword_filter(
                Job.objects.filter(is_active=True).select_related('company'), query
            )
        )
        jobs_qs, active_filters = _apply_filters(request, jobs_qs)

    page_obj = _paginate(request, jobs_qs)
    context = {
        'page_obj': page_obj,
        'query': query,
        'result_count': jobs_qs.count() if query else 0,
        'page_title': f'Search results for "{query}"' if query else 'Search',
        'meta_description': f'Search results for {query} on WorkBase21.',
        'active_filters': active_filters,
        'search_scope': {'job_type': '', 'sector': ''},
        'can_save_search': bool(query),
        'extra_qs': _querystring_without_page(request),
    }
    return render(request, 'search.html', context)


def market_insights(request):
    """Job-Market Analytics: aggregated trends computed from Workbase21's
    own active listings — no external data source. Every breakdown
    shows a sample size so numbers aren't mistaken for a national
    survey; this only reflects what's currently posted on the site."""
    active_jobs = Job.objects.filter(is_active=True)
    total = active_jobs.count()

    def _breakdown(qs, field, label_map=None, limit=10):
        rows = list(
            qs.exclude(**{field: ''}).values(field)
            .annotate(count=Count('id')).order_by('-count')[:limit]
        )
        for row in rows:
            raw = row[field]
            row['label'] = label_map.get(raw, raw) if label_map else raw
            row['pct'] = round((row['count'] / total) * 100) if total else 0
        return rows

    top_skills = list(
        Skill.objects.annotate(
            count=Count('jobs', filter=Q(jobs__is_active=True), distinct=True)
        ).filter(count__gt=0).order_by('-count')[:10]
    )
    for s in top_skills:
        s.pct = round((s.count / total) * 100) if total else 0

    top_locations = list(
        active_jobs.values('location').annotate(count=Count('id'))
        .order_by('-count')[:10]
    )
    for row in top_locations:
        row['pct'] = round((row['count'] / total) * 100) if total else 0

    by_category = _breakdown(active_jobs, 'type', dict(Job.TYPE_CHOICES))
    by_sector = _breakdown(
        active_jobs.filter(type=Job.JOB), 'sector', dict(Job.SECTOR_CHOICES)
    )
    by_experience = _breakdown(
        active_jobs, 'experience_level', dict(Job.EXPERIENCE_CHOICES)
    )
    by_qualification = _breakdown(
        active_jobs, 'qualification_level', dict(Job.QUALIFICATION_CHOICES)
    )
    by_industry = _breakdown(active_jobs, 'industry', dict(Job.INDUSTRY_CHOICES))
    by_work_mode = _breakdown(active_jobs, 'work_mode', dict(Job.WORK_MODE_CHOICES))

    date_bounds = active_jobs.order_by('created_at').first(), active_jobs.order_by('-created_at').first()

    context = {
        'page_title': 'Job Market Insights',
        'meta_description': (
            "See what's trending in the South African job market right "
            "now — most requested skills, top locations, and demand by "
            "industry, experience level and qualification, based on "
            "live WorkBase21 listings."
        ),
        'total': total,
        'earliest': date_bounds[0].created_at if date_bounds[0] else None,
        'latest': date_bounds[1].created_at if date_bounds[1] else None,
        'top_skills': top_skills,
        'top_locations': top_locations,
        'by_category': by_category,
        'by_sector': by_sector,
        'by_experience': by_experience,
        'by_qualification': by_qualification,
        'by_industry': by_industry,
        'by_work_mode': by_work_mode,
    }
    return render(request, 'market_insights.html', context)


def about(request):
    return render(request, 'about.html', {
        'page_title': 'About Us',
        'meta_description': 'Learn more about WorkBase21 and our mission to connect South African talent with opportunity.',
    })


def trending_list(request):
    """Resources / career advice hub — lists every TrendingTopic that
    has a full article body, newest first."""
    articles = TrendingTopic.objects.filter(
        is_active=True
    ).exclude(body='').order_by('-created_at')
    page_obj = _paginate(request, articles, per_page=9)
    return render(request, 'trending_list.html', {
        'page_obj': page_obj,
        'page_title': 'Blog',
        'active_type': 'trending_list',
        'meta_description': (
            'Career advice, CV tips, and guides to help South African '
            'job seekers navigate jobs, internships, learnerships and '
            'bursaries on WorkBase21.'
        ),
    })


def trending_detail(request, slug):
    """Full article page for a TrendingTopic that has a body. 404s for
    stat-only cards that were never meant to have their own page."""
    article = get_object_or_404(
        TrendingTopic, slug=slug, is_active=True
    )
    if not article.is_article:
        from django.http import Http404
        raise Http404("This entry doesn't have a published article.")

    related_articles = TrendingTopic.objects.filter(
        is_active=True
    ).exclude(pk=article.pk).exclude(body='').order_by('-created_at')[:3]

    return render(request, 'trending_detail.html', {
        'article': article,
        'related_articles': related_articles,
        'page_title': article.title,
        'active_type': 'trending_list',
        'meta_description': article.description or article.title,
    })


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        if over_limit(f'contact:ip:{client_ip(request)}', 5):
            messages.error(
                request,
                "You've sent several messages in a short time, so this one wasn't sent. "
                "Please wait a while and try again.",
                extra_tags='modal',
            )
        else:
            data = form.cleaned_data
            # Sent FROM the site's Gmail (Gmail won't send as someone
            # else) with Reply-To set to the visitor, so hitting Reply
            # in Gmail answers them directly.
            email = EmailMessage(
                subject=f"[WorkBase21 Contact] {data['subject']}",
                body=(
                    f"Name: {data['name']}\n"
                    f"Email: {data['email']}\n\n"
                    f"{data['message']}\n"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[settings.SITE_EMAIL],
                reply_to=[data['email']],
            )
            try:
                email.send()
            except (smtplib.SMTPException, OSError):
                logger.exception("Contact form email failed to send")
                messages.error(
                    request,
                    "Something went wrong on our side and your message couldn't be sent. "
                    "What you typed is still in the form, so you can try again in a few minutes.",
                    extra_tags='modal',
                )
            else:
                messages.success(
                    request,
                    f"Thanks, {data['name']}! Your message has been sent. "
                    f"We'll reply to {data['email']} as soon as we can.",
                    extra_tags='modal',
                )
                return redirect('contact')

    return render(request, 'contact.html', {
        'form': form,
        'page_title': 'Contact Us',
        'meta_description': 'Get in touch with the WorkBase21 team.',
    })


def privacy(request):
    return render(request, 'privacy.html', {
        'page_title': 'Privacy Policy',
        'meta_description': 'Read the WorkBase21 privacy policy.',
    })


def terms(request):
    return render(request, 'terms.html', {
        'page_title': 'Terms & Conditions',
        'meta_description': 'Read the WorkBase21 terms and conditions.',
    })


def custom_404(request, exception=None):
    return render(request, '404.html', {
        'page_title': 'Page Not Found',
    }, status=404)


def ads_txt(request):
    """
    Serve /ads.txt for Google AdSense verification.

    Served via a Django view (instead of relying on the static files
    pipeline) so it's guaranteed to be reachable at the site root
    regardless of STATIC_URL, whitenoise config, or collectstatic
    timing on Render.
    """
    from django.http import HttpResponse

    content = "google.com, pub-1588690618371844, DIRECT, f08c47fec0942fa0\n"
    return HttpResponse(content, content_type="text/plain")


def robots_txt(request):
    """
    Serve /robots.txt — allows crawling everywhere except the admin
    and CKEditor upload endpoints, and points crawlers at the sitemap
    so new/updated jobs and articles get discovered and indexed.
    """
    from django.http import HttpResponse

    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /ckeditor/",
        "Allow: /",
        "",
        f"Sitemap: https://{settings.SITE_DOMAIN}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
