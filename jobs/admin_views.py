"""Custom admin-only analytics dashboard.

Shows the numbers WorkBase21's admin wants to see day-to-day:
- How many people are visiting the site (total + unique visitors)
- Which jobs are getting the most attention

Deliberately implemented as a plain staff-only view (not a ModelAdmin)
so it can show hand-picked stats instead of a raw table, while still
living under /admin/ and using the admin's own look and feel.
"""
from datetime import timedelta

from django.conf import settings
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


# ---------------------------------------------------------------------------
# Listing Insights — how job seekers engage with each listing, what needs
# the admin's attention, and what job seekers are looking for.
# Aggregate numbers only: no individual job seeker is named anywhere here.
# ---------------------------------------------------------------------------

def _count_subquery(queryset, count_field='pk', distinct=False):
    """A per-job count as a correlated subquery. Used instead of
    joining several related tables at once, which on SQLite would
    multiply rows (e.g. every page visit x every save) and get slow as
    the Site Visits table grows."""
    from django.db.models import IntegerField, OuterRef, Subquery
    from django.db.models.functions import Coalesce
    sq = (
        queryset.filter(job=OuterRef('pk'))
        .values('job')
        .annotate(c=Count(count_field, distinct=distinct))
        .values('c')
    )
    return Coalesce(Subquery(sq, output_field=IntegerField()), 0)


def annotate_engagement(job_qs):
    from accounts.models import TrackedJob
    return job_qs.annotate(
        n_views=_count_subquery(PageVisit.objects.exclude(session_key=''), 'session_key', distinct=True),
        n_saves=_count_subquery(TrackedJob.objects.all()),
        n_applied=_count_subquery(TrackedJob.objects.filter(status__in=TrackedJob.APPLIED_STATUSES)),
    )


FILTER_FIELD_LABELS = (
    ('qualification_level', 'Qualification'),
    ('experience_level', 'Experience'),
    ('work_mode', 'Work mode'),
    ('industry', 'Industry'),
)


def missing_filter_fields(job):
    missing = [label for field, label in FILTER_FIELD_LABELS if not getattr(job, field)]
    if not job.skills.all():
        missing.append('Skills')
    return missing


@staff_member_required
def listing_insights(request):
    from collections import Counter
    from django.db.models import Q
    from accounts.models import SavedSearch, TrackedJob, UserProfile

    today = timezone.localdate()
    soon = today + timedelta(days=7)

    active = Job.objects.filter(is_active=True)
    open_active = active.filter(Q(deadline__isnull=True) | Q(deadline__gte=today))

    summary = {
        'active': active.count(),
        'open': open_active.count(),
        'closing_soon': active.filter(deadline__gte=today, deadline__lte=soon).count(),
        'expired_visible': active.filter(deadline__lt=today).count(),
        'saves': TrackedJob.objects.count(),
        'applied': TrackedJob.objects.filter(status__in=TrackedJob.APPLIED_STATUSES).count(),
        'job_seekers': UserProfile.objects.filter(user__is_staff=False).count(),
        'saved_searches': SavedSearch.objects.count(),
    }

    # --- Listing performance -------------------------------------------
    top_listings = list(
        annotate_engagement(open_active.select_related('company'))
        .order_by('-n_saves', '-n_applied', '-n_views')[:15]
    )
    for job in top_listings:
        job.save_rate = round(job.n_saves / job.n_views * 100) if job.n_views else None

    closing_soon = list(
        annotate_engagement(
            active.filter(deadline__gte=today, deadline__lte=soon).select_related('company')
        ).order_by('deadline')
    )

    # --- Data quality: listings the filters/alerts/matching can't see ---
    needs_attention = []
    for job in open_active.select_related('company').prefetch_related('skills').order_by('-created_at'):
        missing = missing_filter_fields(job)
        if missing:
            needs_attention.append({'job': job, 'missing': missing})
    missing_total = len(needs_attention)

    # --- Demand: what job seekers want vs what's listed ---------------
    from .models import Skill
    from django.db.models import IntegerField, OuterRef, Subquery
    from django.db.models.functions import Coalesce

    def _skill_count(rel_qs):
        sq = rel_qs.filter(skill=OuterRef('pk')).values('skill').annotate(c=Count('pk')).values('c')
        return Coalesce(Subquery(sq, output_field=IntegerField()), 0)

    ProfileSkill = UserProfile.skills.through
    JobSkill = Job.skills.through
    skill_demand = list(
        Skill.objects.annotate(
            seekers=_skill_count(ProfileSkill.objects.all()),
            open_jobs=_skill_count(JobSkill.objects.filter(
                Q(job__is_active=True) & (Q(job__deadline__isnull=True) | Q(job__deadline__gte=today))
            )),
        ).filter(seekers__gt=0).order_by('-seekers', 'open_jobs', 'name')[:12]
    )

    search_counter = Counter(s.describe() for s in SavedSearch.objects.all()[:2000])
    top_saved_searches = search_counter.most_common(10)

    location_counter = Counter()
    display_name = {}
    for loc in UserProfile.objects.exclude(location='').values_list('location', flat=True):
        key = ' '.join(loc.split()).lower()
        location_counter[key] += 1
        display_name.setdefault(key, ' '.join(loc.split()))
    seeker_locations = []
    for key, n in location_counter.most_common(8):
        town = key.split(',')[0].strip()
        seeker_locations.append({
            'location': display_name[key],
            'seekers': n,
            'open_jobs': open_active.filter(location__icontains=town).count() if town else 0,
        })

    exp_labels = dict(Job.EXPERIENCE_CHOICES)
    seekers_by_exp = dict(
        UserProfile.objects.exclude(experience_level='')
        .values_list('experience_level').annotate(n=Count('pk'))
    )
    jobs_by_exp = dict(
        open_active.exclude(experience_level='')
        .values_list('experience_level').annotate(n=Count('pk'))
    )
    experience_rows = [
        {'label': label, 'seekers': seekers_by_exp.get(key, 0), 'open_jobs': jobs_by_exp.get(key, 0)}
        for key, label in Job.EXPERIENCE_CHOICES
    ]

    context = {
        **admin_site.each_context(request),
        'title': 'Listing Insights',
        'summary': summary,
        'top_listings': top_listings,
        'closing_soon': closing_soon,
        'needs_attention': needs_attention[:25],
        'missing_total': missing_total,
        'skill_demand': skill_demand,
        'top_saved_searches': top_saved_searches,
        'seeker_locations': seeker_locations,
        'experience_rows': experience_rows,
        'has_experience_data': any(r['seekers'] or r['open_jobs'] for r in experience_rows),
    }
    return render(request, 'admin/listing_insights.html', context)


# ---------------------------------------------------------------------------
# Backups (see jobs/backup.py)
# ---------------------------------------------------------------------------

@staff_member_required
def backups_page(request):
    import datetime
    from django.utils import timezone as tz
    from . import backup

    db_file = backup.db_path()
    m_size, m_count = backup.media_size()
    last = backup.last_emailed()
    last_dt = tz.localtime(datetime.datetime.fromtimestamp(last, tz=datetime.timezone.utc)) if last else None
    next_dt = last_dt + datetime.timedelta(days=7) if last_dt else None
    context = {
        **admin_site.each_context(request),
        'title': 'Backups',
        'db_size': backup.human_size(db_file.stat().st_size) if db_file.exists() else '—',
        'media_size': backup.human_size(m_size),
        'media_count': m_count,
        'email_configured': backup.email_is_configured(),
        'site_email': settings.SITE_EMAIL,
        'last_emailed': last_dt,
        'next_email': next_dt,
        'is_superuser': request.user.is_superuser,
    }
    return render(request, 'admin/backups.html', context)


@staff_member_required
def backup_download_db(request):
    from django.http import HttpResponse
    from . import backup
    data, _ = backup.gzipped_database()
    response = HttpResponse(data, content_type='application/gzip')
    response['Content-Disposition'] = f'attachment; filename="workbase21-database-{backup.stamp()}.sqlite3.gz"'
    return response


@staff_member_required
def backup_download_full(request):
    import tempfile
    from django.http import FileResponse
    from . import backup
    # Built in a temporary file (deleted automatically once the download
    # finishes), so a big zip never sits in memory.
    tmp = tempfile.NamedTemporaryFile(suffix='.zip')
    backup.write_full_backup_zip(tmp)
    tmp.seek(0)
    return FileResponse(tmp, as_attachment=True, filename=f"workbase21-full-backup-{backup.stamp()}.zip",
                        content_type='application/zip')


@staff_member_required
def backup_email_now(request):
    import smtplib
    from django.contrib import messages
    from django.shortcuts import redirect
    from . import backup
    if request.method != 'POST':
        return redirect('admin_backups')
    if not backup.email_is_configured():
        messages.error(request, "Email isn't set up on this server (EMAIL_HOST_USER / EMAIL_HOST_PASSWORD), so the backup can't be emailed.")
        return redirect('admin_backups')
    try:
        size = backup.email_database_backup('manual')
    except (smtplib.SMTPException, OSError, RuntimeError) as e:
        messages.error(request, f"The backup couldn't be emailed: {e}. Try again, or use Download instead.")
    else:
        messages.success(request, f"Backup emailed to {settings.SITE_EMAIL} ({backup.human_size(size)}). The weekly timer restarts from now.")
    return redirect('admin_backups')


@staff_member_required
def backup_restore(request):
    from django.contrib import messages
    from django.http import HttpResponseForbidden
    from django.shortcuts import redirect
    from . import backup
    if not request.user.is_superuser:
        return HttpResponseForbidden("Only superusers can restore backups.")
    if request.method != 'POST':
        return redirect('admin_backups')
    uploaded = request.FILES.get('backup_file')
    if not uploaded:
        messages.error(request, "Choose a backup file first.")
        return redirect('admin_backups')
    if request.POST.get('confirm', '').strip() != 'RESTORE':
        messages.error(request, "Nothing was changed: type RESTORE (in capitals) in the box to confirm.")
        return redirect('admin_backups')
    try:
        safety, counts = backup.restore_database(uploaded)
    except backup.RestoreError as e:
        messages.error(request, f"Nothing was changed: {e}")
        return redirect('admin_backups')
    messages.success(
        request,
        f"Database restored ({counts['jobs']} listings, {counts['users']} user accounts in the backup). "
        f"The previous database was saved on the server as {safety.name}. "
        "If you were logged out, just log in again.",
    )
    return redirect('admin_backups')
