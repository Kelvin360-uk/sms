from django.urls import path
from . import views

urlpatterns = [
    path('', views.class_list, name='class_list'),
    path('create/', views.create_class, name='create_class'),
    path('<int:class_id>/', views.class_detail, name='class_detail'),
    path('subjects/', views.subject_list, name='subject_list'),
    path('subjects/create/', views.create_subject, name='create_subject'),
]
