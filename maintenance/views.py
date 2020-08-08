from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from maintenance.models import Equipment, Component, Telemetry, Maintenance, Failure
import pandas as pd

@csrf_exempt
def predict(request):
	if request.method == 'GET':
		createFeatures()
		temp = 5
		return JsonResponse(temp, safe = False)
	else:
		return HttpResponse(status = 405)
		
def createFeatures():
	telemetry = pd.DataFrame(list(Telemetry.objects.values()))
	maintenances = pd.DataFrame(list(Maintenance.objects.values()))
	failures = pd.DataFrame(list(Failure.objects.values()))
	equipments = pd.DataFrame(list(Equipment.objects.values()))
	if not equipments.empty:
		equipments['model'] = equipments['model'].astype('category')
		equipments['mark'] = equipments['mark'].astype('category')
		equipments['type'] = equipments['type'].astype('category')
	if not telemetry.empty:
		telemetry['dateTime'] = pd.to_datetime(telemetry['dateTime'], format="%Y-%m-%d %H:%M:%S")
	if not maintenances.empty:
		maintenances['dateTime'] = pd.to_datetime(maintenances['dateTime'], format="%Y-%m-%d %H:%M:%S")
		maintenances['comp'] = maintenances['comp'].astype('category')
	if not failures.empty:
		failures['dateTime'] = pd.to_datetime(failures['dateTime'], format="%Y-%m-%d %H:%M:%S")
		failures['comp'] = failures['comp'].astype('category')
	
	print("-----")
	print(equipments)
	print("-----")
	print(telemetry)
	print("-----")
	print(maintenances)
	print("-----")
	print(failures)
	
	
	