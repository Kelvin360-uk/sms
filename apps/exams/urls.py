from django.urls import path
from . import views

urlpatterns = [
    path('', views.exam_dashboard, name='exam_dashboard'),
    path('submit/', views.submit_result, name='submit_result'),
    path('sessions/create/', views.create_session, name='create_exam_session'),
    path('reminders/create/', views.create_reminder, name='create_reminder'),
    path('class-teacher/pending/', views.class_teacher_pending, name='class_teacher_pending'),
    path('class-teacher/<int:result_id>/review/', views.class_teacher_review, name='class_teacher_review'),
    path('asst-hm/pending/', views.asst_hm_pending, name='asst_hm_pending'),
    path('asst-hm/<int:result_id>/finalize/', views.asst_hm_finalize, name='asst_hm_finalize'),
    path('student/<int:student_id>/results/', views.view_results, name='view_results'),
    path('student/<int:student_id>/download/', views.download_results, name='download_results'),
]
