from django.urls import path
from . import views

urlpatterns = [
    path('', views.welcome, name='welcome'),

    path('jobs/', views.jobs_sector_choice, name='jobs'),
    path('jobs/public/', views.job_list_by_sector, {'sector': 'public'}, name='jobs_public'),
    path('jobs/private/', views.job_list_by_sector, {'sector': 'private'}, name='jobs_private'),
    path('internships/', views.job_list_by_type, {'job_type': 'internships'}, name='internships'),
    path('learnerships/', views.job_list_by_type, {'job_type': 'learnerships'}, name='learnerships'),
    path('in-service-trainee/', views.job_list_by_type, {'job_type': 'inservice'}, name='inservice'),
    path('bursaries/', views.job_list_by_type, {'job_type': 'bursaries'}, name='bursaries'),

    path('job/<int:pk>/', views.job_detail, name='job_detail'),
    path('search/', views.search_results, name='search'),

    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('privacy-policy/', views.privacy, name='privacy'),
    path('terms-and-conditions/', views.terms, name='terms'),
]
