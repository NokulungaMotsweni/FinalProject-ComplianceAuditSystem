from django.urls import path
from .views import dashboard, upload_dataset

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('upload', upload_dataset, name='upload_dataset'),
]