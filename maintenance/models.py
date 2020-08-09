from django.db import models

class Equipment(models.Model):
    id = models.BigAutoField(primary_key=True)
    model = models.CharField(max_length = 30)
    commissioned_on = models.DateTimeField()
    class Meta:
        managed = False
        db_table = 'equipments'

class Component(models.Model):
    id = models.BigAutoField(primary_key=True)
    designation = models.CharField(max_length = 30)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    class Meta:
        managed = False
        db_table = 'components'

class Telemetry(models.Model):
    id = models.BigAutoField(primary_key=True)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    volt = models.FloatField()
    rotate = models.FloatField()
    pressure = models.FloatField()
    vibration = models.FloatField()
    dateTime = models.DateTimeField(blank=True, null=True)
    class Meta:
        managed = False
        db_table = 'telemetries'

class Maintenance(models.Model):
    id = models.BigAutoField(primary_key=True)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    comp = models.CharField(max_length = 50)
    dateTime = models.DateTimeField(blank=True, null=True)
    class Meta:
        managed = False
        db_table = 'maintenances'

class Failure(models.Model):
    id = models.BigAutoField(primary_key=True)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    comp = models.CharField(max_length = 50)
    dateTime = models.DateTimeField(blank=True, null=True)
    class Meta:
        managed = False
        db_table = 'failures'

class Error(models.Model):
    id = models.BigAutoField(primary_key=True)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    error_code = models.CharField(max_length = 10)
    dateTime = models.DateTimeField(blank=True, null=True)
    class Meta:
        managed = False
        db_table = 'errors'