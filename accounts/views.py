import json

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth import views as auth_views
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from jobs import matching
from . import graph
from jobs.models import Job

from .forms import (
    DeleteAccountForm, ProfileForm, RegisterForm, StyledPasswordChangeForm,
    StyledPasswordResetForm, StyledSetPasswordForm, TrackedJobForm,
)
from .models import CareerPath, SavedSearch, TrackedJob, UserProfile
from .context_processors import ALERT_COUNT_SESSION_KEY
from jobs.throttle import client_ip, over_limit



def register(request):
    """Free job-seeker registration — no email verification step for
    now, kept deliberately simple. Logs the person straight in and
    sends them to set up their profile."""
    if request.user.is_authenticated:
        return redirect('profile')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        UserProfile.objects.create(user=user)
        auth_login(request, user)
        messages.success(
            request,
            "Welcome to WorkBase21! Let's set up your profile so we can "
            "personalize things for you."
        )
        return redirect('profile_edit')

    return render(request, 'accounts/register.html', {
        'form': form,
        'page_title': 'Create Your Account',
        'meta_description': 'Create a free WorkBase21 job seeker account.',
    })


@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'accounts/profile.html', {
        'profile': profile,
        'page_title': 'My Profile',
        'skill_suggestions': graph.suggest_skills(profile),
        'career_suggestions': graph.suggest_careers(profile),
    })


@login_required
@require_POST
def profile_add_skill(request, pk):
    """One-tap '+ Add' for a suggested skill."""
    from jobs.models import Skill
    skill = get_object_or_404(Skill, pk=pk)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile.skills.add(skill)
    messages.success(request, f"Added {skill.name} to your skills.")
    return redirect(_safe_next(request, 'profile'))


@login_required
def profile_edit(request):
    from django.db.models import Count, Q
    from jobs.models import Skill
    from .models import Qualification

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, instance=profile)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect('profile')

    skill_suggestions = Skill.objects.annotate(
        n=Count('jobs', filter=Q(jobs__is_active=True), distinct=True)
    ).filter(n__gt=0).order_by('-n', 'name')[:15]
    qualification_suggestions = Qualification.objects.annotate(
        n=Count('profiles', distinct=True)
    ).order_by('-n', 'name')[:10]

    return render(request, 'accounts/profile_edit.html', {
        'form': form,
        'page_title': 'Edit My Profile',
        'skill_suggestions': skill_suggestions,
        'qualification_suggestions': qualification_suggestions,
    })


def career_list(request):
    """Career Explorer — a public, browsable list of career paths.
    No login needed to look around; the skills-gap comparison on each
    career's detail page is the part that needs a profile."""
    career_paths = CareerPath.objects.filter(is_active=True).prefetch_related(
        'skills', 'qualifications'
    )
    career_suggestions = []
    if request.user.is_authenticated:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        career_suggestions = graph.suggest_careers(profile)
    return render(request, 'accounts/career_list.html', {
        'career_paths': career_paths,
        'career_suggestions': career_suggestions,
        'page_title': 'Career Explorer',
        'meta_description': 'Explore career paths, the skills and qualifications they ask for, and related WorkBase21 jobs.',
    })


def career_detail(request, slug):
    career = get_object_or_404(
        CareerPath.objects.prefetch_related('skills', 'qualifications'),
        slug=slug, is_active=True,
    )
    related_jobs = graph.related_jobs_for_career(career)
    previous_paths = career.previous_paths.filter(is_active=True)
    next_paths = career.next_paths.filter(is_active=True)

    gap = None
    if request.user.is_authenticated:
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        gap = matching.skill_gap(profile, career)

    return render(request, 'accounts/career_detail.html', {
        'career': career,
        'related_jobs': related_jobs,
        'previous_paths': previous_paths,
        'next_paths': next_paths,
        'gap': gap,
        'page_title': career.title,
        'meta_description': career.description[:160] if career.description else f'{career.title} career path on WorkBase21.',
    })


def _safe_next(request, fallback):
    nxt = request.POST.get('next') or request.GET.get('next')
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return nxt
    return fallback


@login_required
@require_POST
def toggle_saved_job(request, pk):
    """Save / unsave a job from the job detail page. A job that has
    moved past 'Saved' (i.e. the person has applied) is never deleted
    by this button — that would silently lose their tracking notes."""
    job = get_object_or_404(Job, pk=pk)
    tracked = TrackedJob.objects.filter(user=request.user, job=job).first()
    if tracked is None:
        TrackedJob.objects.create(user=request.user, job=job)
        messages.success(request, "Job saved. Track it from My Applications.")
    elif tracked.status == TrackedJob.SAVED:
        tracked.delete()
        messages.info(request, "Removed from your saved jobs.")
    else:
        messages.info(request, "You're already tracking this application — update it from My Applications.")
    return redirect(_safe_next(request, job.get_absolute_url()))


def _application_stats(items):
    """The job seeker's OWN history only — plain counts, no
    benchmarking against other people and no predictions."""
    applied = [t for t in items if t.applied_at]
    total_applied = len(applied)
    responded = sum(1 for t in items if t.status in TrackedJob.RESPONDED_STATUSES)
    by_category = {}
    for t in applied:
        label = t.job.type_label
        by_category[label] = by_category.get(label, 0) + 1
    return {
        'saved': sum(1 for t in items if t.status == TrackedJob.SAVED),
        'applied': total_applied,
        'interviews': sum(1 for t in items if t.reached_interview),
        'offers': sum(1 for t in items if t.status == TrackedJob.OFFER),
        'response_rate': round(responded / total_applied * 100) if total_applied else None,
        'by_category': sorted(by_category.items(), key=lambda kv: -kv[1]),
    }


@login_required
def application_tracker(request):
    items = list(
        TrackedJob.objects.filter(user=request.user).select_related('job', 'job__company')
    )
    status_counts = {key: 0 for key, _ in TrackedJob.STATUS_CHOICES}
    for t in items:
        status_counts[t.status] += 1

    active_status = request.GET.get('status', '')
    shown = [t for t in items if t.status == active_status] if active_status in status_counts else items

    today = timezone.localdate()
    soon = today + timezone.timedelta(days=7)
    reminders = sorted(
        [t for t in items if t.reminder_date and t.reminder_date <= soon],
        key=lambda t: t.reminder_date,
    )

    status_tabs = [
        {'key': key, 'label': label, 'count': status_counts[key]}
        for key, label in TrackedJob.STATUS_CHOICES
    ]

    return render(request, 'accounts/application_tracker.html', {
        'items': shown,
        'total': len(items),
        'status_tabs': status_tabs,
        'active_status': active_status,
        'stats': _application_stats(items),
        'reminders': reminders,
        'today': today,
        'page_title': 'My Applications',
    })


@login_required
def application_edit(request, pk):
    tracked = get_object_or_404(
        TrackedJob.objects.select_related('job', 'job__company'), pk=pk, user=request.user
    )
    form = TrackedJobForm(request.POST or None, instance=tracked)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Application updated.")
        return redirect('application_tracker')
    return render(request, 'accounts/application_edit.html', {
        'form': form,
        'tracked': tracked,
        'page_title': f'Update — {tracked.job.title}',
    })


@login_required
@require_POST
def application_delete(request, pk):
    tracked = get_object_or_404(TrackedJob, pk=pk, user=request.user)
    tracked.delete()
    messages.info(request, "Removed from your tracker.")
    return redirect('application_tracker')


# --- Saved searches & in-app job alerts --------------------------------

SAVABLE_RESULT_PAGES = {
    'jobs_public', 'jobs_private', 'internships', 'learnerships', 'bursaries', 'search',
}


def _clear_alert_count_cache(request):
    request.session.pop(ALERT_COUNT_SESSION_KEY, None)


@login_required
@require_POST
def saved_search_create(request):
    from django.urls import Resolver404, resolve
    from jobs.search import FILTER_PARAMS

    results_path = request.POST.get('results_path', '')
    try:
        match = resolve(results_path)
    except Resolver404:
        match = None
    if not match or match.url_name not in SAVABLE_RESULT_PAGES:
        messages.error(request, "That search can't be saved.")
        return redirect('welcome')

    job_type = request.POST.get('job_type', '')
    job_type = job_type if job_type in dict(Job.TYPE_CHOICES) else ''
    sector = request.POST.get('sector', '')
    sector = sector if sector in dict(Job.SECTOR_CHOICES) else ''
    query = request.POST.get('q', '').strip()[:200]
    filters = {}
    for key in FILTER_PARAMS:
        value = request.POST.get(f'f_{key}', '').strip()[:100]
        if value:
            filters[key] = value

    back = _safe_next(request, results_path)

    if match.url_name == 'search' and not query:
        messages.error(request, "Enter a search term before saving a search.")
        return redirect(back)

    existing = SavedSearch.objects.filter(user=request.user)
    for s in existing:
        if (s.job_type, s.sector, s.query.lower(), s.filters or {}) == (job_type, sector, query.lower(), filters):
            messages.info(request, "You've already saved this search — see it under Job Alerts.")
            return redirect(back)
    if existing.count() >= SavedSearch.MAX_PER_USER:
        messages.error(request, f"You can save up to {SavedSearch.MAX_PER_USER} searches. Remove one under Job Alerts first.")
        return redirect(back)

    SavedSearch.objects.create(
        user=request.user, job_type=job_type, sector=sector, query=query,
        filters=filters, results_path=results_path,
        last_seen_job_id=SavedSearch.current_max_job_id(),
    )
    _clear_alert_count_cache(request)
    messages.success(request, "Search saved. New matching listings will show up under Job Alerts.")
    return redirect(back)


@login_required
def job_alerts(request):
    rows = []
    for search in SavedSearch.objects.filter(user=request.user):
        new = search.new_jobs()
        rows.append({
            'search': search,
            'new_count': new.count(),
            'new_jobs': list(new[:5]),
        })
    total_new = sum(r['new_count'] for r in rows)
    # Refresh the header badge with the exact number just calculated.
    import time
    request.session[ALERT_COUNT_SESSION_KEY] = {'t': time.time(), 'n': total_new}
    return render(request, 'accounts/job_alerts.html', {
        'rows': rows,
        'total_new': total_new,
        'max_searches': SavedSearch.MAX_PER_USER,
        'page_title': 'Job Alerts',
    })


@login_required
@require_POST
def job_alerts_mark_seen(request, pk=None):
    searches = SavedSearch.objects.filter(user=request.user)
    if pk is not None:
        searches = searches.filter(pk=pk)
        if not searches.exists():
            from django.http import Http404
            raise Http404
    searches.update(
        last_seen_job_id=SavedSearch.current_max_job_id(),
        last_seen_at=timezone.now(),
    )
    _clear_alert_count_cache(request)
    messages.success(request, "Marked as seen.")
    return redirect('job_alerts')


@login_required
@require_POST
def saved_search_delete(request, pk):
    search = get_object_or_404(SavedSearch, pk=pk, user=request.user)
    search.delete()
    _clear_alert_count_cache(request)
    messages.info(request, "Saved search removed.")
    return redirect('job_alerts')


# --- Password reset / change (Gmail, free) --------------------------------



class PasswordResetView(auth_views.PasswordResetView):
    """Django's standard reset flow plus rate limits (3 emails per
    address, 10 requests per device, per hour) so the form can't burn
    the free Gmail quota or be used to spam people.

    The 'check your email' page is ALWAYS shown — for unknown
    addresses, rate-limited requests, and even if Gmail fails (Django
    catches and logs that itself: look for 'Failed to send password
    reset email' in the Render logs). Showing a different page in any
    of those cases would reveal which email addresses have accounts."""
    template_name = 'accounts/password_reset_form.html'
    email_template_name = 'accounts/emails/password_reset_email.txt'
    subject_template_name = 'accounts/emails/password_reset_subject.txt'
    form_class = StyledPasswordResetForm
    success_url = reverse_lazy('password_reset_done')

    def form_valid(self, form):
        email = form.cleaned_data['email'].strip().lower()
        ip_limited = over_limit(f'pwreset:ip:{client_ip(self.request)}', 10)
        email_limited = over_limit(f'pwreset:email:{email}', 3)
        if ip_limited or email_limited:
            return redirect(self.success_url)
        return super().form_valid(form)


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    form_class = StyledSetPasswordForm
    success_url = reverse_lazy('password_reset_complete')


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'


class PasswordChangeView(auth_views.PasswordChangeView):
    template_name = 'accounts/password_change.html'
    form_class = StyledPasswordChangeForm
    success_url = reverse_lazy('account_settings')

    def form_valid(self, form):
        response = super().form_valid(form)  # keeps the user logged in
        messages.success(self.request, "Your password has been changed.")
        return response


# --- Account settings: download & delete (POPIA) ----------------------------

@login_required
def account_settings(request):
    return render(request, 'accounts/account_settings.html', {
        'page_title': 'Account Settings',
    })


@login_required
def account_download(request):
    """Everything WorkBase21 stores about this account, as a JSON file."""
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    def fmt(d):
        return d.isoformat() if d else None

    data = {
        'account': {
            'username': user.username,
            'email': user.email,
            'date_joined': fmt(user.date_joined),
            'last_login': fmt(user.last_login),
        },
        'profile': {
            'location': profile.location,
            'highest_qualification_level': profile.qualification_label,
            'qualifications': list(profile.qualifications.values_list('name', flat=True)),
            'experience_level': profile.experience_label,
            'career_goal': profile.career_goal,
            'skills': list(profile.skills.values_list('name', flat=True)),
            'bio': profile.bio,
        },
        'saved_and_tracked_jobs': [
            {
                'job': t.job.title,
                'company': t.job.company.name,
                'status': t.get_status_display(),
                'date_applied': fmt(t.applied_at),
                'reminder_date': fmt(t.reminder_date),
                'notes': t.notes,
                'saved_on': fmt(t.created_at),
            }
            for t in TrackedJob.objects.filter(user=user).select_related('job', 'job__company')
        ],
        'saved_searches': [
            {'search': s_.describe(), 'saved_on': fmt(s_.created_at)}
            for s_ in SavedSearch.objects.filter(user=user)
        ],
        'exported_on': fmt(timezone.now()),
    }
    response = HttpResponse(
        json.dumps(data, indent=2, ensure_ascii=False),
        content_type='application/json; charset=utf-8',
    )
    response['Content-Disposition'] = 'attachment; filename="workbase21-my-data.json"'
    return response


@login_required
def account_delete(request):
    """Permanently deletes the account and everything attached to it:
    profile, saved/tracked jobs and notes, saved searches. Requires the
    password. Admin (staff) accounts are blocked here so the site owner
    can't lock themselves out by accident."""
    if request.user.is_staff:
        messages.error(request, "Admin accounts can't be deleted from this page — use the Django admin instead.")
        return redirect('account_settings')

    form = DeleteAccountForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, "Your account and all its data have been permanently deleted.")
        return redirect('welcome')

    return render(request, 'accounts/account_delete.html', {
        'form': form,
        'page_title': 'Delete Account',
    })
