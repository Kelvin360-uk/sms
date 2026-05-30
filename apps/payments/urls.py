from django.urls import path
from . import views

urlpatterns = [
    path('', views.payment_dashboard, name='payment_dashboard'),
    path('submit/', views.finance_submit_payment, name='finance_submit_payment'),
    path('outstanding/', views.outstanding_balances, name='outstanding_balances'),
    path('class-performance/', views.class_performance, name='class_performance'),
    path('<int:payment_id>/', views.payment_detail, name='payment_detail'),
    path('<int:payment_id>/edit/', views.edit_pending_payment, name='edit_payment'),
    path('<int:payment_id>/approve/', views.it_admin_approve, name='it_admin_approve_payment'),
    path('<int:payment_id>/reverse/', views.reverse_payment, name='reverse_payment'),
]
