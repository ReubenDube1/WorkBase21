"""Skills & career relationship graph — suggestions built from the
admin-managed links between skills, qualifications and career paths.

Rules-based and explainable like the rest of the matching: every
suggestion carries the reason it was made ("goes with Python",
"covered by your BSc Statistics", "matches your career goal").
"""
from django.db.models import Count, Q
from django.utils import timezone

from jobs.models import Job, Skill

from .models import CareerPath


def open_jobs_q(prefix=''):
    today = timezone.localdate()
    return (
        Q(**{f'{prefix}is_active': True})
        & (Q(**{f'{prefix}deadline__isnull': True}) | Q(**{f'{prefix}deadline__gte': today}))
    )


def suggest_skills(profile, limit=8):
    """Skills the job seeker doesn't list yet, suggested because they
    go with skills they have, or their qualifications usually cover
    them. Ranked by how many open listings ask for the skill."""
    have = set(profile.skills.values_list('pk', flat=True))
    reasons = {}

    for skill in profile.skills.prefetch_related('related_skills'):
        for rel in skill.related_skills.all():
            if rel.pk not in have:
                reasons.setdefault(rel.pk, []).append(f"goes with {skill.name}")

    for qual in profile.qualifications.prefetch_related('skills'):
        for rel in qual.skills.all():
            if rel.pk not in have:
                reasons.setdefault(rel.pk, []).append(f"covered by your {qual.name}")

    if not reasons:
        return []

    skills = Skill.objects.filter(pk__in=reasons).annotate(
        open_jobs=Count('jobs', filter=open_jobs_q('jobs__'), distinct=True)
    )
    rows = [{'skill': s, 'reasons': reasons[s.pk], 'open_jobs': s.open_jobs} for s in skills]
    rows.sort(key=lambda r: (-r['open_jobs'], -len(r['reasons']), r['skill'].name.lower()))
    return rows[:limit]


def suggest_careers(profile, limit=3):
    """Career paths ranked by how much of their skill list the profile
    already covers, with a matching career goal ranked first. Coverage
    is a coverage measure only — never a chance of getting hired."""
    have = set(profile.skills.values_list('pk', flat=True))
    goal = ' '.join(profile.career_goal.lower().split())
    rows = []
    for career in CareerPath.objects.filter(is_active=True).prefetch_related('skills'):
        ids = {s.pk for s in career.skills.all()}
        matched = len(ids & have)
        title = career.title.lower()
        goal_match = bool(goal) and (goal in title or title in goal)
        if not matched and not goal_match:
            continue
        rows.append({
            'career': career,
            'matched': matched,
            'total': len(ids),
            'coverage': round(matched / len(ids) * 100) if ids else None,
            'goal_match': goal_match,
        })
    rows.sort(key=lambda r: (not r['goal_match'], -(r['coverage'] or 0), -r['matched'], r['career'].title))
    return rows[:limit]


def related_jobs_for_career(career, limit=6):
    """Open listings that share a skill with the career OR whose title
    contains one of the career's related job titles."""
    q = Q()
    skill_ids = list(career.skills.values_list('pk', flat=True))
    if skill_ids:
        q |= Q(skills__in=skill_ids)
    for title in career.job_title_list:
        q |= Q(title__icontains=title)
    if not q:
        return Job.objects.none()
    return (
        Job.objects.filter(q).filter(open_jobs_q())
        .distinct().select_related('company').order_by('-created_at')[:limit]
    )
