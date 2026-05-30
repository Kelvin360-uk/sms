from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from apps.users import views as user_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth
    path('', user_views.root_redirect, name='root'),
    path('login/', user_views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Dashboard
    path('dashboard/', user_views.dashboard, name='dashboard'),

    # App URLs
    path('users/', include('apps.users.urls')),
    path('students/', include('apps.students.urls')),
    path('teachers/', include('apps.teachers.urls')),
    path('classes/', include('apps.classes.urls')),
    path('exams/', include('apps.exams.urls')),
    path('payments/', include('apps.payments.urls')),
    path('audit/', include('apps.audit.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('messaging/', include('apps.messaging.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
