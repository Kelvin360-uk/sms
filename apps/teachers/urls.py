from django.urls import path
from . import views

urlpatterns = [
    path('', views.teacher_list, name='teacher_list'),
    path('create/', views.create_teacher, name='create_teacher'),
    path('export/', views.export_teachers, name='export_teachers'),
    path('<int:teacher_id>/', views.teacher_detail, name='teacher_detail'),
    path('<int:teacher_id>/edit/', views.edit_teacher, name='edit_teacher'),
]
