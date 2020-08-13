from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from maintenance.models import Equipment, Telemetry, Maintenance, Failure, Error
import pandas as pd
import numpy as np
from datetime import datetime
import pickle

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
	maintenances = pd.DataFrame(list(Maintenance.objects.values('dateTime', 'equipment_id', 'comp')))
	failures = pd.DataFrame(list(Failure.objects.values('dateTime', 'equipment_id', 'comp')))
	equipments = pd.DataFrame(list(Equipment.objects.extra(
		select={
			'equipment_id': 'id',
			'model': 'model',
			'commissioned_on': 'commissioned_on'
		}
	).values('equipment_id', 'model', 'commissioned_on')))
	errors = pd.DataFrame(list(Error.objects.values('dateTime', 'equipment_id', 'error_code')))
	if not equipments.empty:
		equipments['model'] = equipments['model'].astype('category')
		equipments['commissioned_on'] = pd.to_datetime(equipments['commissioned_on'], format="%Y-%m-%d %H:%M:%S")
		equipments['commissioned_on'] = pd.DatetimeIndex(equipments['commissioned_on']).tz_localize(None)
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
	print(equipments.head())
	print("-----")
	print(telemetry.head())
	print("-----")
	print(maintenances.head())
	print("-----")
	print(failures.head())
	print("-----")
	print(errors.head())
	
	#calculating features
	
	#1.telemetry features
	
	#1.1.mean every 3h
	fields = ['volt', 'rotate', 'pressure', 'vibration']
	temp = []
	for col in fields:
		temp.append(pd.pivot_table(telemetry,
									index='dateTime',
									columns='equipment_id',
									values=col).resample('3H', closed='left', label='right').mean().unstack())
	telemetry_mean_3h = pd.concat(temp, axis=1)
	telemetry_mean_3h.columns = [i + 'mean_3h' for i in fields]
	telemetry_mean_3h.reset_index(inplace=True)
	
	#1.2.std every 3h
	temp = []
	for col in fields:
		temp.append(pd.pivot_table(telemetry,
								index='dateTime',
								columns='equipment_id',
								values=col).resample('3H', closed='left', label='right').std().unstack())
	telemetry_sd_3h = pd.concat(temp, axis=1)
	telemetry_sd_3h.columns = [i + 'sd_3h' for i in fields]
	telemetry_sd_3h.reset_index(inplace=True)
	
	#1.3.mean every 24h
	
	telemetry_mean_24h = telemetry_mean_3h
	
	# temp = []
	# for col in fields:
		# temp.append(pd.pivot_table(telemetry,
									# index='dateTime',
									# columns='equipment_id',
									# values=col).rolling(window=24,center=False).mean().resample('3H',
																			# closed='left',
																			# label='right').first().unstack())
	# telemetry_mean_24h = pd.concat(temp, axis=1)
	# telemetry_mean_24h.columns = [i + 'mean_24h' for i in fields]
	# telemetry_mean_24h.reset_index(inplace=True)
	# telemetry_mean_24h = telemetry_mean_24h.loc[-telemetry_mean_24h['voltmean_24h'].isnull()]
	
	#1.4.std every 24h
	
	telemetry_sd_24h = telemetry_sd_3h
	
	# temp = []
	# for col in fields:
		# temp.append(pd.pivot_table(telemetry,
									# index='dateTime',
									# columns='equipment_id',
									# values=col).rolling(window=24,center=False).std().resample('3H',
																			# closed='left',
																			# label='right').first().unstack())
	# telemetry_sd_24h = pd.concat(temp, axis=1)
	# telemetry_sd_24h.columns = [i + 'sd_24h' for i in fields]
	# telemetry_sd_24h = telemetry_sd_24h.loc[-telemetry_sd_24h['voltsd_24h'].isnull()]
	# telemetry_sd_24h.reset_index(inplace=True)
	
	#1.5.combine the last four features
	
	print("//////////")
	print(telemetry_mean_3h)
	print(telemetry_sd_3h)
	print(telemetry_mean_24h)
	print(telemetry_sd_24h)
	print("//////////")
	
	telemetry_feat = pd.concat([telemetry_mean_3h,
								telemetry_sd_3h.iloc[:, 2:7],
								telemetry_mean_24h.iloc[:, 2:7],
								telemetry_sd_24h.iloc[:, 2:7]],
								axis=1).dropna()
	
	print("**********")
	print(telemetry_feat.head())
	
	#2.errors features
	error_count = pd.get_dummies(errors.set_index('dateTime')).reset_index()
	error_count.columns = [em[11:] if em.startswith('error') else em for em in error_count.columns]
	error_count = error_count.groupby(['equipment_id','dateTime']).sum().reset_index()
	error_count = telemetry[['dateTime', 'equipment_id']].merge(error_count, on=['equipment_id', 'dateTime'], how='left').fillna(0.0)
	
	
	temp = []
	fields = ['error%d' % i for i in range(1, len(error_count.columns) - 1)]
	for col in fields:
		temp.append(pd.pivot_table(error_count,
								index='dateTime',
								columns='equipment_id',
								values=col).resample('3H', closed='left', label='right').first().unstack())
	# for col in fields:
		# temp.append(pd.pivot_table(error_count,
									# index='dateTime',
									# columns='equipment_id',
									# values=col).rolling(window=24,center=False).sum().resample('3H',
																								# closed='left',
																								# label='right').first().unstack())
	error_count = pd.concat(temp, axis=1)
	error_count.columns = [i + 'count' for i in fields]
	error_count.reset_index(inplace=True)
	error_count = error_count.dropna()
		
	print("**********")
	print(error_count.head())
	
	#3.maintenance features
	comp_rep = pd.get_dummies(maintenances.set_index('dateTime')).reset_index()
	comp_rep.columns = [em[5:] if em.startswith('comp') else em for em in comp_rep.columns]
	comp_rep = comp_rep.groupby(['equipment_id', 'dateTime']).sum().reset_index()
	comp_rep = telemetry[['dateTime', 'equipment_id']].merge(comp_rep,
														on=['dateTime', 'equipment_id'],
														how='outer').fillna(0).sort_values(by=['equipment_id', 'dateTime'])
	components = [comp for comp in comp_rep.columns[2:]]
	for comp in components:
		comp_rep.loc[comp_rep[comp] < 1, comp] = None
		comp_rep.loc[-comp_rep[comp].isnull(), comp] = comp_rep.loc[-comp_rep[comp].isnull(), 'dateTime']
		comp_rep[comp] = comp_rep[comp].fillna(method='ffill')
	for comp in components:
		comp_rep[comp] = (comp_rep['dateTime'] - comp_rep[comp]) / np.timedelta64(1, 'D')
	
	print("**********")
	print(comp_rep.head())
	
	#4.equipments features
	equipments.columns = ['equipment_id', 'model', 'age']
	now = datetime.now()
	equipments['age'] = (now - equipments['age']) / np.timedelta64(1, 'Y')
	
	print("**********")
	print(equipments.head())
	
	#5.combine all features
	final_feat = telemetry_feat.merge(error_count, on=['dateTime', 'equipment_id'], how='left')
	final_feat = final_feat.merge(comp_rep, on=['dateTime', 'equipment_id'], how='left')
	final_feat = final_feat.merge(equipments, on=['equipment_id'], how='left')
	
	print("+-+-+-+-+-+-+-+-+")
	print(final_feat.head())
	
	#6.label construction
	labeled_features = final_feat.merge(failures, on=['dateTime', 'equipment_id'], how='left')
	labeled_features = labeled_features.bfill(axis=1, limit=7)
	labeled_features = labeled_features.fillna('none')
	
	print("+-+-+-+-+-+-+-+-+")
	print(labeled_features.head())
	
	labeled_features_for_prediction = pd.get_dummies(labeled_features.drop(['dateTime', 'equipment_id', 'comp'], 1))
	
	print("+-+-+-+-+-+-+-+-+")
	print(labeled_features_for_prediction.head())
	
	#7.get model
	# import os
	# module_dir = os.path.dirname(__file__)
	# file_path = os.path.join(module_dir, 'prediction_model.pkl')
	
	# gradientBoostingClassifier = pickle.load(open(file_path, 'rb'))
	
	#8.final results
	# labeled_features['predicted_failure'] = gradientBoostingClassifier.predict(labeled_features_for_prediction)
	
	# labeled_features = labeled_features.loc[labeled_features['predicted_failure'] != 'none']
	# print("@@@@@@@@@@@@ final results")
	# print(labeled_features)
	
	
	
	
	
	
	
	
	
	
	