from django.urls import path
from . import views

urlpatterns = [
    path('', views.student_list, name='student_list'),
    path('create/', views.create_student, name='create_student'),
    path('statistics/', views.student_statistics, name='student_statistics'),
    path('export/', views.export_students, name='export_students'),
    path('<int:student_id>/', views.student_detail, name='student_detail'),
    path('<int:student_id>/edit/', views.edit_student, name='edit_student'),
]
