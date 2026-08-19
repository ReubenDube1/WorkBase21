from django.conf import settings


def job_types(request):
    """Makes the navbar links and site-wide info available in every
    template without passing it from each view."""
    return {
        'nav_job_types': [
            {'slug': 'jobs', 'label': 'Jobs'},
            {'slug': 'internships', 'label': 'Internships'},
            {'slug': 'learnerships', 'label': 'Learnerships'},
            {'slug': 'trending_list', 'label': 'Blog'},
            {'slug': 'bursaries', 'label': 'Bursaries'},
        ],
        'SITE_NAME': settings.SITE_NAME,
        'SITE_DOMAIN': settings.SITE_DOMAIN,
        'SITE_EMAIL': settings.SITE_EMAIL,
        'SITE_DESCRIPTION': settings.SITE_DESCRIPTION,
    }
