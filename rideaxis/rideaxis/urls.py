from django.contrib import admin
from django.urls import path, include 
from myapp import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path("", include("myapp.urls")),
    path('profile/', views.profile, name='profile'),
    path("login/", auth_views.LoginView.as_view(template_name="myapp/login.html"), name="login"),
    path('logout/', views.logout_view, name='logout'),
    path("register/", views.register, name="register"),
]
