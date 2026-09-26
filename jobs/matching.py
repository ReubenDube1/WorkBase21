"""Rules-based, transparent matching between a job seeker's profile
and a job listing — no AI, no black box. Every criterion the
eligibility checker reports is a straightforward, explainable
comparison of fields already on the two models.

Deliberately conservative: this never claims to predict whether an
employer will accept or reject anyone. It only reports how a
profile's stated qualification, experience, skills and location
compare with what a listing states, and which criteria couldn't be
compared because either side left a field blank.
"""
from .models import Job

QUALIFICATION_RANK = {key: i for i, (key, _) in enumerate(Job.QUALIFICATION_CHOICES)}
EXPERIENCE_RANK = {key: i for i, (key, _) in enumerate(Job.EXPERIENCE_CHOICES)}


def check_eligibility(profile, job):
    """Returns a dict with 'matched', 'unmet' and 'unclear' lists of
    short, plain-language strings, plus 'checked_count' (criteria that
    could actually be compared) and 'matched_count'."""
    matched, unmet, unclear = [], [], []

    # --- Qualification level ---
    if not job.qualification_level:
        unclear.append("This listing doesn't specify a required qualification level.")
    elif not profile.qualification_level:
        unclear.append("Add your qualification level to your profile to check this.")
    else:
        job_rank = QUALIFICATION_RANK.get(job.qualification_level, -1)
        profile_rank = QUALIFICATION_RANK.get(profile.qualification_level, -1)
        if profile_rank >= job_rank:
            matched.append(
                f"Your qualification level ({profile.qualification_label}) meets what "
                f"this role asks for ({job.qualification_label})."
            )
        else:
            unmet.append(
                f"This role asks for {job.qualification_label}; your profile shows "
                f"{profile.qualification_label}."
            )

    # --- Experience level ---
    if not job.experience_level:
        unclear.append("This listing doesn't specify a required experience level.")
    elif not profile.experience_level:
        unclear.append("Add your experience level to your profile to check this.")
    else:
        job_rank = EXPERIENCE_RANK.get(job.experience_level, -1)
        profile_rank = EXPERIENCE_RANK.get(profile.experience_level, -1)
        if profile_rank >= job_rank:
            matched.append(
                f"Your experience level ({profile.experience_label}) meets what this "
                f"role asks for ({job.experience_label})."
            )
        else:
            unmet.append(
                f"This role asks for {job.experience_label}; your profile shows "
                f"{profile.experience_label}."
            )

    # --- Skills ---
    job_skills = set(job.skills.all())
    if not job_skills:
        unclear.append("This listing doesn't list specific required skills.")
    else:
        profile_skills = set(profile.skills.all())
        overlap = job_skills & profile_skills
        missing = job_skills - profile_skills
        if overlap:
            names = ", ".join(s.name for s in overlap)
            matched.append(
                f"You have {len(overlap)} of {len(job_skills)} skills this role "
                f"lists: {names}."
            )
        if missing:
            names = ", ".join(s.name for s in missing)
            unmet.append(f"Skills listed but not on your profile: {names}.")

    # --- Location ---
    if job.work_mode == 'remote':
        unclear.append("This role is listed as remote, so location may not be a factor.")
    elif not job.location:
        unclear.append("This listing doesn't specify a location.")
    elif not profile.location:
        unclear.append("Add your location to your profile to check this.")
    else:
        job_loc = job.location.lower()
        profile_loc = profile.location.lower()
        profile_parts = [p.strip() for p in profile_loc.split(',') if p.strip()]
        overlaps = (
            profile_loc in job_loc or job_loc in profile_loc
            or any(part in job_loc for part in profile_parts)
        )
        if overlaps:
            matched.append(
                f"Your location ({profile.location}) matches this role's location "
                f"({job.location})."
            )
        else:
            unmet.append(
                f"Your profile location ({profile.location}) differs from this "
                f"role's location ({job.location})."
            )

    return {
        'matched': matched,
        'unmet': unmet,
        'unclear': unclear,
        'checked_count': len(matched) + len(unmet),
        'matched_count': len(matched),
    }


def recommend_jobs(profile, queryset, limit=12):
    """Ranks active jobs by how well they match the profile, reusing
    the exact same transparent rules as the eligibility checker —
    nothing hidden, nothing AI-scored. Only returns jobs with at
    least one matched criterion, so an empty or barely-filled-in
    profile won't get padded out with irrelevant listings. Never a
    hiring-probability claim — just "this matches what you've told us
    about yourself so far."
    """
    scored = []
    for job in queryset:
        result = check_eligibility(profile, job)
        if result['matched_count'] > 0:
            scored.append((job, result))

    def sort_key(pair):
        result = pair[1]
        matched = result['matched_count']
        checked = result['checked_count'] or 1
        return (matched, matched / checked)

    scored.sort(key=sort_key, reverse=True)
    return scored[:limit]


def skill_gap(profile, career_path):
    """Compares the profile's skills against a CareerPath's listed
    skills. 'coverage_pct' is explicitly a coverage measure (how much
    of the career's skill list the profile already has) — never
    presented as a probability of landing a role in that career."""
    target_skills = set(career_path.skills.all())
    if not target_skills:
        return {
            'has_target_skills': False,
            'matched': [], 'missing': [],
            'matched_count': 0, 'total': 0, 'coverage_pct': None,
        }

    profile_skills = set(profile.skills.all())
    matched = sorted(target_skills & profile_skills, key=lambda s: s.name)
    missing = sorted(target_skills - profile_skills, key=lambda s: s.name)

    return {
        'has_target_skills': True,
        'matched': matched,
        'missing': missing,
        'matched_count': len(matched),
        'total': len(target_skills),
        'coverage_pct': round(len(matched) / len(target_skills) * 100),
    }
