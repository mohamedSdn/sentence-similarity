from django.http import HttpResponse, JsonResponse
from sim.models import Forum, Embedding
from sim.serializers import ForumSerializer
from rest_framework.parsers import JSONParser
from django.views.decorators.csrf import csrf_exempt


from sentence_transformers import SentenceTransformer
import scipy.spatial


def createEmb(pk):
	try:
		forum = Forum.objects.get(pk = pk)
	except Forum.DoesNotExist:
		return [[]]
	forumVector = [[]]
	if forum.embedding_set.count() == 0:
		model = SentenceTransformer('distiluse-base-multilingual-cased')
		forumVector = model.encode([forum.title])
		emb = zip(range(512), forumVector[0])
		for idx, val in emb:
			forum.embedding_set.create(index = idx, value = val)
	else:
		embs = forum.embedding_set.all().order_by('index')
		for em in embs:
			forumVector[0].append(em.value)
	return forumVector

@csrf_exempt
def simForums(request, pk):
	if request.method == 'GET':
		forumVector = createEmb(pk)
		if len(forumVector[0]) == 0:
			return HttpResponse(status=404)
		otherForumVectors = []
		counter = 0
		forums = Forum.objects.exclude(pk = pk).order_by('id')
		for frm in forums:
			embs = frm.embedding_set.all().order_by('index')
			if len(embs) == 512:
				otherForumVectors.append([])
				for em in embs:
					otherForumVectors[counter].append(em.value)
				counter += 1
		if len(otherForumVectors) == 0:
			return HttpResponse(status = 404)
		distances = scipy.spatial.distance.cdist(forumVector, otherForumVectors, "correlation")[0]
		finalResults = zip(forums, distances)
		finalResults = sorted(finalResults, key=lambda x: x[1])
		selectedForums = []
		counter = 0
		for key, value in finalResults:
			if counter == 3 or value > .5:
				break
			selectedForums.append(key)
			counter += 1
		serializer = ForumSerializer(selectedForums, many = True)
		return JsonResponse(serializer.data, safe = False)
	else:
		return HttpResponse(status = 405)

@csrf_exempt
def insertEmbs(request, pk):
	if request.method == 'POST':
		forumVector = createEmb(pk)
		if len(forumVector) == 0:
			return HttpResponse(status = 404)
		else:
			return HttpResponse(status = 201)
	else:
		return HttpResponse(status = 405)