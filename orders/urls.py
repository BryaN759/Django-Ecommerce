from django.urls import path
from . import views

urlpatterns = [
    path('place_order/', views.place_order, name='place_order'),
    path('payments/<str:order_number>/', views.payments, name='payments'),
    path('order_status/<str:order_number>/', views.order_status, name='order_status'),
    path('order_complete/<str:order_number>/<str:tran_id>/', views.order_complete, name='order_complete'),
    # path('payment-success/', views.payment_success, name='payment_success'),
    # path('payment-failed/', views.payment_failure, name='payment_failed'),
    # path('payment-cancelled/', views.payment_cancelled, name='payment_cancelled'),
]