from sim.models import Forum
from rest_framework import serializers

class ForumSerializer(serializers.HyperlinkedModelSerializer):
	class Meta:
		model = Forum
		fields = ['id', 'title']