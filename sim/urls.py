from django.urls import path
from sim import views

urlpatterns = [
    path('forums/<int:pk>/', views.simForums),
    path('forums/<int:pk>/embeddings/', views.insertEmbs),
]