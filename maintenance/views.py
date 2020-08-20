from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from maintenance.models import Equipment, Telemetry, Maintenance, Failure, Error
import category_encoders as ce
import pandas as pd
import numpy as np
from datetime import datetime
import pickle
import os

@csrf_exempt
def predict(request):
	if request.method == 'GET':
		temp = createFeatures()
		if(temp == -1):
			return HttpResponse(status = 503)
		elif(temp == -2):
			return HttpResponse(status = 400)
		elif(temp in [0, 1, 2, 3, 4]):
			temp = []
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
			'commissioned_on': 'commissioned_on',
			'code': 'code'
		}
	).values('equipment_id', 'model', 'commissioned_on', 'code')))
	errors = pd.DataFrame(list(Error.objects.values('dateTime', 'equipment_id', 'error_code')))
	print("--------")
	print(equipments.head())
	if not equipments.empty:
		equipments['model'] = equipments['model'].astype('str')
		equipments['code'] = equipments['code'].astype('str')
		equipments['commissioned_on'] = pd.to_datetime(equipments['commissioned_on'], format="%Y-%m-%d %H:%M:%S")
		equipments['commissioned_on'] = pd.DatetimeIndex(equipments['commissioned_on']).tz_localize(None)
	else:
		return 3
	if not telemetry.empty:
		telemetry['dateTime'] = pd.to_datetime(telemetry['dateTime'], format="%Y-%m-%d %H:%M:%S")
		telemetry['dateTime'] = pd.DatetimeIndex(telemetry['dateTime']).tz_localize(None)
	else:
		return 0
	if not maintenances.empty:
		maintenances['dateTime'] = pd.to_datetime(maintenances['dateTime'], format="%Y-%m-%d %H:%M:%S")
		maintenances['dateTime'] = pd.DatetimeIndex(maintenances['dateTime']).tz_localize(None)
		maintenances['comp'] = maintenances['comp'].astype('category')
	else:
		return 2
	if not failures.empty:
		failures['dateTime'] = pd.to_datetime(failures['dateTime'], format="%Y-%m-%d %H:%M:%S")
		failures['dateTime'] = pd.DatetimeIndex(failures['dateTime']).tz_localize(None)
		failures['comp'] = failures['comp'].astype('category')
	if not errors.empty:
		errors['dateTime'] = pd.to_datetime(errors['dateTime'], format="%Y-%m-%d %H:%M:%S")
		errors['dateTime'] = pd.DatetimeIndex(errors['dateTime']).tz_localize(None)
		errors['error_code'] = errors['error_code'].astype('category')
	else:
		return 1
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
	temp = []
	for col in fields:
		temp.append(pd.pivot_table(telemetry,
									index='dateTime',
									columns='equipment_id',
									values=col).rolling(window=24,center=False).mean().resample('3H',
																			closed='left',
																			label='right').first().unstack())
	telemetry_mean_24h = pd.concat(temp, axis=1)
	telemetry_mean_24h.columns = [i + 'mean_24h' for i in fields]
	telemetry_mean_24h.reset_index(inplace=True)
	telemetry_mean_24h = telemetry_mean_24h.loc[-telemetry_mean_24h['voltmean_24h'].isnull()]
	
	#1.4.std every 24h
	temp = []
	for col in fields:
		temp.append(pd.pivot_table(telemetry,
									index='dateTime',
									columns='equipment_id',
									values=col).rolling(window=24,center=False).std().resample('3H',
																			closed='left',
																			label='right').first().unstack())
	telemetry_sd_24h = pd.concat(temp, axis=1)
	telemetry_sd_24h.columns = [i + 'sd_24h' for i in fields]
	telemetry_sd_24h = telemetry_sd_24h.loc[-telemetry_sd_24h['voltsd_24h'].isnull()]
	telemetry_sd_24h.reset_index(inplace=True)
	
	#1.5.combine the last four features
	telemetry_feat = pd.concat([telemetry_mean_3h,
								telemetry_sd_3h.iloc[:, 2:7],
								telemetry_mean_24h.iloc[:, 2:7],
								telemetry_sd_24h.iloc[:, 2:7]],
								axis=1).dropna()
	
	if(telemetry_feat.empty):
		return 0
	
	#2.errors features
	error_count = pd.get_dummies(errors.set_index('dateTime')).reset_index()
	error_count.columns = [em[11:] if em.startswith('error') else em for em in error_count.columns]
	error_count = error_count.groupby(['equipment_id','dateTime']).sum().reset_index()
	error_count = telemetry[['dateTime', 'equipment_id']].merge(error_count, on=['equipment_id', 'dateTime'], how='left').fillna(0.0)
	
	
	temp = []
	fields = ['error%d' % i for i in range(1, 6)]
	# for col in fields:
		# if col not in error_count:
			# error_count[col] = [0] * len(error_count.index)
		# temp.append(pd.pivot_table(error_count,
								# index='dateTime',
								# columns='equipment_id',
								# values=col).resample('3H', closed='left', label='right').first().unstack())
	for col in fields:
		if col not in error_count:
			error_count[col] = [0] * len(error_count.index)
		temp.append(pd.pivot_table(error_count,
									index='dateTime',
									columns='equipment_id',
									values=col).rolling(window=24,center=False).sum().resample('3H',
																								closed='left',
																								label='right').first().unstack())
	error_count = pd.concat(temp, axis=1)
	error_count.columns = [i + 'count' for i in fields]
	error_count.reset_index(inplace=True)
	error_count = error_count.dropna()
	error_count = error_count.loc[:, ['equipment_id', 'dateTime', 'error1count', 'error2count', 'error3count', 'error4count', 'error5count']]
	
	if(error_count.empty):
		return 1
	
	#3.maintenance features
	comp_rep = pd.get_dummies(maintenances.set_index('dateTime')).reset_index()
	comp_rep.columns = [em[5:] if em.startswith('comp') else em for em in comp_rep.columns]
	components = ['comp%d' % i for i in range(1, 5)]
	for comp in components:
		if comp not in comp_rep:
			comp_rep[comp] = [0.0] * len(comp_rep.index)
	comp_rep = comp_rep.groupby(['equipment_id', 'dateTime']).sum().reset_index()
	comp_rep = telemetry[['dateTime', 'equipment_id']].merge(comp_rep,
														on=['dateTime', 'equipment_id'],
														how='outer').fillna(0).sort_values(by=['equipment_id', 'dateTime'])
	for comp in components:
		comp_rep.loc[comp_rep[comp] < 1, comp] = None
		comp_rep.loc[-comp_rep[comp].isnull(), comp] = comp_rep.loc[-comp_rep[comp].isnull(), 'dateTime']
		comp_rep[comp] = pd.to_datetime(comp_rep[comp], format="%Y-%m-%d %H:%M:%S")
		comp_rep[comp] = pd.DatetimeIndex(comp_rep[comp]).tz_localize(None)
		comp_rep[comp] = comp_rep[comp].fillna(method='ffill')
	for comp in components:
		comp_rep[comp] = (comp_rep['dateTime'] - comp_rep[comp]) / np.timedelta64(1, 'D')
		comp_rep[comp] = comp_rep[comp].fillna(100.0)
	
	comp_rep = comp_rep.loc[:, ['equipment_id', 'dateTime', 'comp1', 'comp2', 'comp3', 'comp4']]
	
	if(comp_rep.empty):
		return 2
	
	#4.equipments features
	equipments.columns = ['equipment_id', 'model', 'age', 'code']
	
	now = datetime.now()
	equipments['age'] = (now - equipments['age']) / np.timedelta64(1, 'Y')

	x = equipments['model']
	y = equipments.drop('model', axis=1)

	hash = ce.HashingEncoder(cols='model', n_components=6)
	z = hash.fit_transform(x, y['age'])

	equipments = pd.concat([z, y], axis=1)
	
	if(equipments.empty):
		return 3

	#5.combine all features
	final_feat = telemetry_feat.merge(error_count, on=['dateTime', 'equipment_id'], how='left')
	final_feat = final_feat.merge(comp_rep, on=['dateTime', 'equipment_id'], how='left')
	final_feat = final_feat.merge(equipments, on=['equipment_id'], how='left')
	
	if(final_feat.empty):
		return 4
	
	#6.label construction
	if not failures.empty:
		labeled_features = final_feat.merge(failures, on=['dateTime', 'equipment_id'], how='left')
		labeled_features = labeled_features.bfill(axis=1, limit=7)
		labeled_features = labeled_features.fillna('none')
	else:
		labeled_features['comp'] = 'none'
	labeled_features_for_prediction = pd.get_dummies(labeled_features.drop(['dateTime', 'equipment_id', 'comp', 'code'], 1))
	
	#7.get model
	module_dir = os.path.dirname(__file__)
	file_path = os.path.join(module_dir, 'prediction_model.pkl')
	
	try:
		gradientBoostingClassifier = pickle.load(open(file_path, 'rb'))
	except:
		return -1
	
	#8.final results
	try:
		labeled_features['predicted_failure'] = gradientBoostingClassifier.predict(labeled_features_for_prediction)
	except:
		return -2
	
	# labeled_features = labeled_features.loc[:, ['equipment_id', 'predicted_failure']].values.tolist()
	labeled_features = labeled_features.loc[labeled_features['predicted_failure'] != 'none', ['equipment_id', 'code', 'predicted_failure']].values.tolist()
	return labeled_features
	