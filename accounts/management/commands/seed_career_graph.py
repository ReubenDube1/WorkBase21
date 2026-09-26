"""Optional starter data for the skills & career graph.

    python manage.py seed_career_graph

Creates a small set of career paths, skills, qualifications and the
links between them, so Career Explorer and profile suggestions have
something to work with. Safe to run more than once, and it never
overwrites anything you've already set up:
  - an existing career path (same title) is left completely untouched
  - existing skills/qualifications are reused (matched ignoring case)
  - links are only ever ADDED, never removed
Everything it creates can be edited or deleted in the admin.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import CareerPath, Qualification
from jobs.models import Skill

RELATED_SKILLS = [
    ('Statistics', 'Data Analysis'), ('Statistics', 'R'), ('Statistics', 'Machine Learning'),
    ('Data Analysis', 'Excel'), ('Data Analysis', 'SQL'), ('Data Analysis', 'Data Visualisation'),
    ('Data Analysis', 'Python'), ('Data Visualisation', 'Power BI'),
    ('Python', 'Machine Learning'), ('Python', 'Django'), ('Python', 'Git'),
    ('Machine Learning', 'Deep Learning'), ('Machine Learning', 'Cloud Computing'),
    ('JavaScript', 'HTML/CSS'), ('JavaScript', 'React'), ('JavaScript', 'Git'),
    ('Networking', 'Linux'), ('Networking', 'Cybersecurity'), ('Linux', 'Cybersecurity'),
    ('Cloud Computing', 'Linux'), ('Communication', 'Problem Solving'),
]

QUALIFICATIONS = {
    # name: (level, [skills it usually covers])
    'BSc Statistics': ('degree', ['Statistics', 'R', 'Data Analysis']),
    'BSc Mathematical Sciences': ('degree', ['Statistics', 'Python', 'Problem Solving']),
    'BSc Computer Science': ('degree', ['Python', 'SQL', 'Git', 'JavaScript', 'Problem Solving']),
    'National Diploma: Information Technology': ('diploma', ['Networking', 'HTML/CSS', 'SQL']),
    'Matric': ('matric', []),
}

CAREERS = [
    {
        'title': 'IT Support Technician', 'icon': '🖥️', 'order': 1,
        'description': 'Keeps computers, networks and users running — an entry point into IT that doesn\'t always require a degree.',
        'skills': ['Networking', 'Linux', 'Communication', 'Problem Solving'],
        'qualifications': ['National Diploma: Information Technology', 'Matric'],
        'job_titles': ['IT Support', 'IT Technician', 'Help Desk', 'Desktop Support'],
        'milestones': ['Learn computer hardware and operating system basics',
                       'Learn networking fundamentals', 'Get comfortable with Linux',
                       'Practise troubleshooting and explaining fixes to users'],
        'next': ['Cybersecurity Analyst', 'Software Developer'],
    },
    {
        'title': 'Data Analyst', 'icon': '📊', 'order': 2,
        'description': 'Turns data into answers that help organisations make decisions — reports, dashboards and analysis.',
        'skills': ['Excel', 'SQL', 'Statistics', 'Data Analysis', 'Data Visualisation', 'Power BI', 'Python', 'Communication'],
        'qualifications': ['BSc Statistics', 'BSc Mathematical Sciences', 'BSc Computer Science'],
        'job_titles': ['Data Analyst', 'Business Analyst', 'BI Analyst', 'Reporting Analyst'],
        'milestones': ['Get comfortable with Excel (formulas, pivot tables)', 'Learn SQL to query databases',
                       'Learn the basics of statistics', 'Build dashboards in Power BI or a similar tool',
                       'Complete 2–3 portfolio projects using real public data'],
        'next': ['Data Scientist'],
    },
    {
        'title': 'Data Scientist', 'icon': '🔬', 'order': 3,
        'description': 'Uses statistics, programming and machine learning to find patterns and build predictive models.',
        'skills': ['Python', 'Statistics', 'Machine Learning', 'SQL', 'Data Analysis', 'R', 'Data Visualisation'],
        'qualifications': ['BSc Statistics', 'BSc Mathematical Sciences', 'BSc Computer Science'],
        'job_titles': ['Data Scientist'],
        'milestones': ['Build strong Python and SQL skills', 'Deepen statistics and probability',
                       'Learn core machine learning methods', 'Complete end-to-end projects from raw data to results'],
        'next': ['Machine Learning Engineer'],
    },
    {
        'title': 'Machine Learning Engineer', 'icon': '🤖', 'order': 4,
        'description': 'Builds, deploys and maintains machine learning systems in production.',
        'skills': ['Python', 'Machine Learning', 'Deep Learning', 'Cloud Computing', 'Git', 'SQL'],
        'qualifications': ['BSc Computer Science', 'BSc Mathematical Sciences'],
        'job_titles': ['Machine Learning Engineer', 'ML Engineer', 'AI Engineer'],
        'milestones': ['Get solid at Python and software engineering practices', 'Learn machine learning and deep learning',
                       'Learn to deploy models on cloud platforms', 'Build and ship a model others can use'],
        'next': [],
    },
    {
        'title': 'Software Developer', 'icon': '💻', 'order': 5,
        'description': 'Designs, builds and maintains software — web apps, mobile apps and systems.',
        'skills': ['Python', 'JavaScript', 'HTML/CSS', 'Git', 'SQL', 'Django', 'React', 'Problem Solving'],
        'qualifications': ['BSc Computer Science', 'National Diploma: Information Technology'],
        'job_titles': ['Software Developer', 'Software Engineer', 'Web Developer', 'Junior Developer', 'Programmer'],
        'milestones': ['Learn one programming language well', 'Learn Git and version control',
                       'Build and deploy a web app', 'Contribute to a team or open-source project'],
        'next': ['Machine Learning Engineer'],
    },
    {
        'title': 'Cybersecurity Analyst', 'icon': '🛡️', 'order': 6,
        'description': 'Protects an organisation\'s systems and data by monitoring, detecting and responding to threats.',
        'skills': ['Networking', 'Linux', 'Cybersecurity', 'Cloud Computing', 'Problem Solving', 'Communication'],
        'qualifications': ['National Diploma: Information Technology', 'BSc Computer Science'],
        'job_titles': ['Cybersecurity Analyst', 'Security Analyst', 'SOC Analyst', 'Information Security'],
        'milestones': ['Learn networking and Linux fundamentals', 'Learn core security concepts and common attacks',
                       'Practise with security tools in a home lab', 'Work towards an entry-level security certification'],
        'next': [],
    },
]


def get_skill(name):
    return Skill.objects.filter(name__iexact=name).first() or Skill.objects.create(name=name)


def get_qualification(name, level):
    q = Qualification.objects.filter(name__iexact=name).first()
    if q is None:
        return Qualification.objects.create(name=name, level=level), True
    if not q.level and level:
        q.level = level
        q.save(update_fields=['level'])
    return q, False


class Command(BaseCommand):
    help = "Add optional starter career paths, skills, qualifications and the links between them."

    @transaction.atomic
    def handle(self, *args, **options):
        skills_before = Skill.objects.count()

        for a, b in RELATED_SKILLS:
            get_skill(a).related_skills.add(get_skill(b))

        quals_created = 0
        for name, (level, skill_names) in QUALIFICATIONS.items():
            q, created = get_qualification(name, level)
            quals_created += created
            q.skills.add(*[get_skill(n) for n in skill_names])

        created_careers, skipped = {}, []
        for data in CAREERS:
            if CareerPath.objects.filter(title__iexact=data['title']).exists():
                skipped.append(data['title'])
                continue
            career = CareerPath.objects.create(
                title=data['title'], icon=data['icon'], order=data['order'],
                description=data['description'],
                milestones='\n'.join(data['milestones']),
                job_titles='\n'.join(data['job_titles']),
            )
            career.skills.add(*[get_skill(n) for n in data['skills']])
            career.qualifications.add(*[
                get_qualification(n, QUALIFICATIONS.get(n, ('', []))[0])[0]
                for n in data['qualifications']
            ])
            created_careers[data['title']] = career

        # Link "next steps" only FROM careers created in this run, so an
        # admin's existing career paths are never modified.
        for data in CAREERS:
            career = created_careers.get(data['title'])
            if not career:
                continue
            for next_title in data['next']:
                target = CareerPath.objects.filter(title__iexact=next_title).first()
                if target and target.pk != career.pk:
                    career.next_paths.add(target)

        self.stdout.write(self.style.SUCCESS(
            f"Career graph ready: {len(created_careers)} career path(s) created, "
            f"{len(skipped)} already existed and were left untouched, "
            f"{Skill.objects.count() - skills_before} new skill(s), "
            f"{quals_created} new qualification(s)."
        ))
        if skipped:
            self.stdout.write("Left untouched: " + ", ".join(skipped))
