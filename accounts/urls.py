from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import LoginForm

urlpatterns = [
    path('register/', views.register, name='register'),
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='accounts/login.html', authentication_form=LoginForm
        ),
        name='login',
    ),
    path(
        'logout/',
        auth_views.LogoutView.as_view(next_page='welcome'),
        name='logout',
    ),
    path('profile/', views.profile_view, name='profile'),
    path('settings/', views.account_settings, name='account_settings'),
    path('settings/download/', views.account_download, name='account_download'),
    path('settings/delete/', views.account_delete, name='account_delete'),
    path('password-change/', views.PasswordChangeView.as_view(), name='password_change'),
    path('password-reset/', views.PasswordResetView.as_view(), name='password_reset'),
    path('password-reset/sent/', views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/add-skill/<int:pk>/', views.profile_add_skill, name='profile_add_skill'),
    path('applications/', views.application_tracker, name='application_tracker'),
    path('applications/<int:pk>/', views.application_edit, name='application_edit'),
    path('applications/<int:pk>/delete/', views.application_delete, name='application_delete'),
    path('alerts/', views.job_alerts, name='job_alerts'),
    path('alerts/save-search/', views.saved_search_create, name='saved_search_create'),
    path('alerts/seen/', views.job_alerts_mark_seen, name='job_alerts_mark_all_seen'),
    path('alerts/<int:pk>/seen/', views.job_alerts_mark_seen, name='job_alerts_mark_seen'),
    path('alerts/<int:pk>/delete/', views.saved_search_delete, name='saved_search_delete'),
]
