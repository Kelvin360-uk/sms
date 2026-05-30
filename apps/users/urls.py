from django.urls import path
from . import views

urlpatterns = [
    path('', views.user_list, name='user_list'),
    path('create/', views.create_user, name='create_user'),
    path('renewal/request/', views.request_session_renewal, name='request_renewal'),
    path('renewal/handle/', views.handle_renewal_requests, name='handle_renewals'),
    path('renewal/<int:req_id>/<str:action>/', views.renewal_action, name='renewal_action'),
    path('downloads/grant/', views.grant_download_permission, name='grant_download'),
]
