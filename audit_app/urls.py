from django.urls import path
from .views import results_list, run_audit

urlpatterns = [
    path('', results_list, name='results'),
    path('run_audit/', run_audit, name='run_audit'),
]