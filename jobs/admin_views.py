"""Custom admin-only analytics dashboard.

Shows the numbers WorkBase21's admin wants to see day-to-day:
- How many people are visiting the site (total + unique visitors)
- Which jobs are getting the most attention

Deliberately implemented as a plain staff-only view (not a ModelAdmin)
so it can show hand-picked stats instead of a raw table, while still
living under /admin/ and using the admin's own look and feel.
"""
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.admin.sites import site as admin_site
from django.db.models import Count
from django.shortcuts import render
from django.utils import timezone

from .models import Job, PageVisit


@staff_member_required
def analytics_dashboard(request):
    now = timezone.localtime()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=6)   # last 7 days, inclusive of today
    month_start = today_start - timedelta(days=29)  # last 30 days, inclusive of today

    all_visits = PageVisit.objects.all()

    total_visits = all_visits.count()
    total_unique_visitors = all_visits.values('session_key').exclude(
        session_key=''
    ).distinct().count()

    visits_today = all_visits.filter(created_at__gte=today_start).count()
    visitors_today = all_visits.filter(created_at__gte=today_start).values(
        'session_key'
    ).exclude(session_key='').distinct().count()

    visits_week = all_visits.filter(created_at__gte=week_start).count()
    visitors_week = all_visits.filter(created_at__gte=week_start).values(
        'session_key'
    ).exclude(session_key='').distinct().count()

    visits_month = all_visits.filter(created_at__gte=month_start).count()
    visitors_month = all_visits.filter(created_at__gte=month_start).values(
        'session_key'
    ).exclude(session_key='').distinct().count()

    # Daily breakdown for the last 14 days, for a simple bar chart.
    daily_breakdown = []
    max_day_count = 1
    for i in range(13, -1, -1):
        day_start = today_start - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        count = all_visits.filter(
            created_at__gte=day_start, created_at__lt=day_end
        ).count()
        max_day_count = max(max_day_count, count)
        daily_breakdown.append({
            'label': day_start.strftime('%d %b'),
            'count': count,
        })
    for row in daily_breakdown:
        row['pct'] = round((row['count'] / max_day_count) * 100) if max_day_count else 0

    # Most-viewed jobs — unique visitors per job, active listings first.
    top_jobs = list(
        Job.objects.filter(page_visits__isnull=False)
        .annotate(
            visitor_count=Count('page_visits__session_key', distinct=True),
            hit_count=Count('page_visits'),
        )
        .filter(visitor_count__gt=0)
        .select_related('company')
        .order_by('-visitor_count')[:10]
    )

    top_pages = list(
        all_visits.exclude(path__startswith='/job/')
        .values('path')
        .annotate(hit_count=Count('id'), visitor_count=Count('session_key', distinct=True))
        .order_by('-hit_count')[:10]
    )

    recent_visits = all_visits.select_related('job', 'job__company')[:25]

    context = {
        **admin_site.each_context(request),
        'title': 'Site Analytics',
        'total_visits': total_visits,
        'total_unique_visitors': total_unique_visitors,
        'visits_today': visits_today,
        'visitors_today': visitors_today,
        'visits_week': visits_week,
        'visitors_week': visitors_week,
        'visits_month': visits_month,
        'visitors_month': visitors_month,
        'daily_breakdown': daily_breakdown,
        'top_jobs': top_jobs,
        'top_pages': top_pages,
        'recent_visits': recent_visits,
    }
    return render(request, 'admin/analytics_dashboard.html', context)
