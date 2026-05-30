"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from xml.etree.ElementInclude import include

from django.contrib import admin
from django.urls import path, include
from audit_app import views as audit_views, exports

from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
    path('', include('messages_app.urls')),
    path('results/', include('audit_app.urls')),
    path('review/', audit_views.review_queue, name='review_queue'),
    path('review/<int:result_id>/action/', audit_views.review_action, name='review_action'),
    path('review/<int:session_id>/close/', audit_views.close_session, name='close_session'),
    path('evaluation/', audit_views.evaluation_view, name='evaluation'),
    path('results/export/<int:session_id>/', exports.export_session_pdf, name='export_session_pdf'),
]
