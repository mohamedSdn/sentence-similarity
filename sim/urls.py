from django.urls import path
from sim import views

urlpatterns = [
    path('forums/<int:pk>/', views.simForums),
]