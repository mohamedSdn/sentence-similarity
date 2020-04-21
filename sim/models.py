# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Forum(models.Model):
    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=191)
    body = models.TextField()
    votes = models.IntegerField()
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    class Meta:
        managed = False
        db_table = 'forums'

class Embedding(models.Model):
	id = models.BigAutoField(primary_key=True)
	question = models.ForeignKey(Forum, on_delete=models.CASCADE)
	index = models.IntegerField()
	value = models.FloatField()
	class Meta:
		db_table = 'embeddings'