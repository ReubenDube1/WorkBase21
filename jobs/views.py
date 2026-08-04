from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.utils import timezone

from .models import Job, Review, TrendingTopic
from .forms import ContactForm

JOBS_PER_PAGE = 9

# Maps a URL-friendly slug to the value stored in Job.type,
# plus the heading shown on that page. ('jobs' is handled separately
# below since it now has its own Public/Private sector split.)
TYPE_MAP = {
    'internships': {'value': Job.INTERNSHIP, 'title': 'Internships', 'blurb': 'Kick-start your career with hands-on experience.'},
    'learnerships': {'value': Job.LEARNERSHIP, 'title': 'Learnerships', 'blurb': 'Structured learning combined with real workplace experience.'},
    'inservice': {'value': Job.INSERVICE, 'title': 'In-Service Trainee', 'blurb': 'Complete your practical training requirements.'},
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


def _active_jobs():
    return Job.objects.filter(
        is_active=True, deadline__gte=timezone.localdate()
    ).select_related('company')


def welcome(request):
    """Home page: hero search bar, latest listings, trending topics and
    reviews from job seekers / partner organisations."""
    page_obj = _paginate(request, _active_jobs())
    context = {
        'page_obj': page_obj,
        'page_title': 'Find Your Next Opportunity',
        'meta_description': (
            "Browse jobs, internships, learnerships, in-service trainee "
            "positions and bursaries across South Africa on WorkBase21."
        ),
        'trending_topics': TrendingTopic.objects.filter(is_active=True),
        'reviews': Review.objects.filter(is_published=True)[:6],
    }
    return render(request, 'welcome.html', context)


def jobs_sector_choice(request):
    """The 'Jobs' nav link now leads here first, so job seekers can pick
    Public Sector or Private Sector before seeing listings."""
    today = timezone.localdate()
    public_count = Job.objects.filter(
        type=Job.JOB, sector=Job.PUBLIC, is_active=True, deadline__gte=today
    ).count()
    private_count = Job.objects.filter(
        type=Job.JOB, sector=Job.PRIVATE, is_active=True, deadline__gte=today
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
    jobs_qs = Job.objects.filter(
        type=Job.JOB,
        sector=sector,
        is_active=True,
        deadline__gte=timezone.localdate(),
    ).select_related('company')
    page_obj = _paginate(request, jobs_qs)
    context = {
        'page_obj': page_obj,
        'page_title': info['title'],
        'page_blurb': info['blurb'],
        'active_type': 'jobs',
        'active_sector': sector,
        'meta_description': f"{info['blurb']} Apply today on WorkBase21.",
    }
    return render(request, 'job_sector_list.html', context)


def job_list_by_type(request, job_type):
    """Shared view for Internships / Learnerships / In-Service / Bursaries
    — each just filters on a different `type` value."""
    info = TYPE_MAP[job_type]
    jobs_qs = Job.objects.filter(
        type=info['value'],
        is_active=True,
        deadline__gte=timezone.localdate(),
    ).select_related('company')
    page_obj = _paginate(request, jobs_qs)
    context = {
        'page_obj': page_obj,
        'page_title': info['title'],
        'page_blurb': info['blurb'],
        'active_type': job_type,
        'meta_description': f"{info['blurb']} Apply today on WorkBase21.",
    }
    template_map = {
        'internships': 'internships.html',
        'learnerships': 'learnerships.html',
        'inservice': 'inservice.html',
        'bursaries': 'bursary.html',
    }
    return render(request, template_map[job_type], context)


def job_detail(request, pk):
    job = get_object_or_404(Job.objects.select_related('company'), pk=pk)

    related_jobs = Job.objects.filter(
        type=job.type, is_active=True, deadline__gte=timezone.localdate()
    ).exclude(pk=job.pk).select_related('company')[:4]

    context = {
        'job': job,
        'related_jobs': related_jobs,
        'page_title': f"{job.title} at {job.company.name}",
        'meta_description': (
            f"{job.title} at {job.company.name} in {job.location}. "
            f"Apply before {job.deadline:%d %b %Y} on WorkBase21."
        ),
    }
    return render(request, 'job_detail.html', context)


def search_results(request):
    query = request.GET.get('q', '').strip()
    jobs_qs = Job.objects.none()

    if query:
        jobs_qs = Job.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(company__name__icontains=query) |
            Q(location__icontains=query) |
            Q(type__icontains=query),
            is_active=True,
        ).select_related('company').distinct()

    page_obj = _paginate(request, jobs_qs)
    context = {
        'page_obj': page_obj,
        'query': query,
        'result_count': jobs_qs.count() if query else 0,
        'page_title': f'Search results for "{query}"' if query else 'Search',
        'meta_description': f'Search results for {query} on WorkBase21.',
    }
    return render(request, 'search.html', context)


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
    ).exclude(body='').order_by('-updated_at')
    page_obj = _paginate(request, articles, per_page=9)
    return render(request, 'trending_list.html', {
        'page_obj': page_obj,
        'page_title': 'Career Resources',
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
    ).exclude(pk=article.pk).exclude(body='').order_by('-updated_at')[:3]

    return render(request, 'trending_detail.html', {
        'article': article,
        'related_articles': related_articles,
        'page_title': article.title,
        'meta_description': article.description or article.title,
    })


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        # In production, hook this up to an email backend or a database
        # model to store enquiries. Kept simple here as requested.
        messages.success(
            request,
            "Thanks for reaching out! We'll get back to you soon."
        )
        form = ContactForm()

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
