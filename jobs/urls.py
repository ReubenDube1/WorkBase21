from django.urls import path
from django.views.generic import RedirectView
from accounts import views as account_views
from . import views

urlpatterns = [
    path('', views.welcome, name='welcome'),

    path('jobs/', views.jobs_sector_choice, name='jobs'),
    path('jobs/public/', views.job_list_by_sector, {'sector': 'public'}, name='jobs_public'),
    path('jobs/private/', views.job_list_by_sector, {'sector': 'private'}, name='jobs_private'),
    path('internships/', views.job_list_by_type, {'job_type': 'internships'}, name='internships'),
    path('learnerships/', views.job_list_by_type, {'job_type': 'learnerships'}, name='learnerships'),
    path('bursaries/', views.job_list_by_type, {'job_type': 'bursaries'}, name='bursaries'),

    path('careers/', account_views.career_list, name='careers'),
    path('careers/<slug:slug>/', account_views.career_detail, name='career_detail'),
    path('recommended/', views.recommended_jobs, name='recommended_jobs'),

    # In-Service Trainee was removed. Anyone with an old bookmarked or
    # shared link is sent to the Blog instead of hitting a 404.
    path('in-service-trainee/', RedirectView.as_view(pattern_name='trending_list', permanent=True)),

    # Must come before the <slug:slug> pattern below — otherwise
    # "eligibility" matches as a (wrong) slug and gets redirected
    # instead of hitting this view.
    path('job/<int:pk>/eligibility/', views.job_eligibility, name='job_eligibility'),
    path('job/<int:pk>/save/', account_views.toggle_saved_job, name='toggle_saved_job'),
    path('job/<int:pk>/<slug:slug>/', views.job_detail, name='job_detail'),
    path('job/<int:pk>/', views.job_detail_legacy_redirect, name='job_detail_legacy'),
    path('search/', views.search_results, name='search'),
    path('market-insights/', views.market_insights, name='market_insights'),

    path('resources/', views.trending_list, name='trending_list'),
    path('resources/<slug:slug>/', views.trending_detail, name='trending_detail'),

    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('privacy-policy/', views.privacy, name='privacy'),
    path('terms-and-conditions/', views.terms, name='terms'),
]
