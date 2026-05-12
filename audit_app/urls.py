from django.urls import path
from . import views

urlpatterns = [
    path('', views.results_list, name='results'),
    path('run_audit/', views.run_audit, name='run_audit'),
]