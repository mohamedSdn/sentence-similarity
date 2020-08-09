from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from maintenance.models import Equipment, Telemetry, Maintenance, Failure, Error
import pandas as pd
import numpy as np

@csrf_exempt
def predict(request):
	if request.method == 'GET':
		createFeatures()
		temp = 5
		return JsonResponse(temp, safe = False)
	else:
		return HttpResponse(status = 405)
		
def createFeatures():
	
	#getting data from database
	telemetry = pd.DataFrame(list(Telemetry.objects.values()))
	maintenances = pd.DataFrame(list(Maintenance.objects.values()))
	failures = pd.DataFrame(list(Failure.objects.values()))
	equipments = pd.DataFrame(list(Equipment.objects.values()))
	errors = pd.DataFrame(list(Error.objects.values()))
	if not equipments.empty:
		equipments['model'] = equipments['model'].astype('category')
	if not telemetry.empty:
		telemetry['dateTime'] = pd.to_datetime(telemetry['dateTime'], format="%Y-%m-%d %H:%M:%S")
	if not maintenances.empty:
		maintenances['dateTime'] = pd.to_datetime(maintenances['dateTime'], format="%Y-%m-%d %H:%M:%S")
		maintenances['comp'] = maintenances['comp'].astype('category')
	if not failures.empty:
		failures['dateTime'] = pd.to_datetime(failures['dateTime'], format="%Y-%m-%d %H:%M:%S")
		failures['comp'] = failures['comp'].astype('category')
	if not errors.empty:
		errors['dateTime'] = pd.to_datetime(errors['dateTime'], format="%Y-%m-%d %H:%M:%S")
		errors['error_code'] = errors['error_code'].astype('category')
	
	print("-----")
	print(equipments)
	print("-----")
	print(telemetry)
	print("-----")
	print(maintenances)
	print("-----")
	print(failures)
	print("-----")
	print(errors)
	
	#calculating features
	
	#1.telemetry features
	
	#1.1.mean every 3h
	fields = ['volt', 'rotate', 'pressure', 'vibration']
	temp = []
	for col in fields:
		temp.append(pd.pivot_table(telemetry,
									index='dateTime',
									columns='equipment_id',
									values=col).resample('3H', closed='left', label='right').agg(np.mean).unstack())
	telemetry_mean_3h = pd.concat(temp, axis=1)
	telemetry_mean_3h.columns = [i + 'mean_3h' for i in fields]
	telemetry_mean_3h.reset_index(inplace=True)
	
	#1.2.std every 3h
	temp = []
	for col in fields:
		temp.append(pd.pivot_table(telemetry,
								index='dateTime',
								columns='equipment_id',
								values=col).resample('3H', closed='left', label='right').agg(np.std, ddof=0).unstack())
	telemetry_sd_3h = pd.concat(temp, axis=1)
	telemetry_sd_3h.columns = [i + 'sd_3h' for i in fields]
	telemetry_sd_3h.reset_index(inplace=True)
	
	#1.3.mean every 24h
	temp = []
	for col in fields:
		temp.append(pd.pivot_table(telemetry,
									index='dateTime',
									columns='equipment_id',
									values=col).rolling(24, min_periods=1).mean().resample('3H',
																			closed='left',
																			label='right').interpolate().unstack())
	
	
	telemetry_mean_24h = pd.concat(temp, axis=1)
	telemetry_mean_24h.columns = [i + 'mean_24h' for i in fields]
	telemetry_mean_24h.reset_index(inplace=True)
	
	#1.4.std every 24h
	temp = []
	for col in fields:
		temp.append(pd.pivot_table(telemetry,
									index='dateTime',
									columns='equipment_id',
									values=col).rolling(24, min_periods=1).std(ddof=0).resample('3H',
																			closed='left',
																			label='right').interpolate().unstack())
	
	
	telemetry_sd_24h = pd.concat(temp, axis=1)
	telemetry_sd_24h.columns = [i + 'std_24h' for i in fields]
	telemetry_sd_24h.reset_index(inplace=True)
	
	telemetry_feat = pd.concat([telemetry_mean_3h,
								telemetry_sd_3h.iloc[:, 2:7],
								telemetry_mean_24h.iloc[:, 2:7],
								telemetry_sd_24h.iloc[:, 2:7]],
								axis=1).dropna()
	
	print("**********")
	print(telemetry_feat)