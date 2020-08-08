from django.urls import path
from maintenance import views

urlpatterns = [
    path('equipments/', views.predict),
]