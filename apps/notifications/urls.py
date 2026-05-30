from django.urls import path
from . import views

urlpatterns = [
    path('', views.notification_list, name='notification_list'),
    path('<int:notif_id>/read/', views.mark_read, name='mark_notification_read'),
    path('read-all/', views.mark_all_read, name='mark_all_notifications_read'),
]
