
from django.urls import include, path

urlpatterns = [
	path('sim/', include('sim.urls')),
	path('maintenance/', include('maintenance.urls')),
]
