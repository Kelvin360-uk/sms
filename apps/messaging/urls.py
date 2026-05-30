from django.urls import path
from . import views

urlpatterns = [
    path('', views.inbox, name='inbox'),
    path('sent/', views.sent, name='sent_messages'),
    path('compose/', views.compose, name='compose_message'),
    path('<int:message_id>/', views.message_detail, name='message_detail'),
    path('<int:message_id>/reply/', views.reply_message, name='reply_message'),
    path('<int:message_id>/resolve/', views.resolve_message, name='resolve_message'),
]
