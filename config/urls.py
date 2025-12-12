from django.contrib import admin
from django.urls import path
from keno import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('inicio/', views.inicio, name='inicio'),
    path('sala/', views.sala, name='sala'),
    path('ranking/', views.ranking, name='ranking'),
]