from django.http import HttpResponse, JsonResponse
from sim.models import Forum, Embedding
from sim.serializers import ForumSerializer
from rest_framework.parsers import JSONParser
from django.views.decorators.csrf import csrf_exempt
import threading


from sentence_transformers import SentenceTransformer
import scipy.spatial

@csrf_exempt
def simForums(request, pk):
	if request.method == 'GET':
		forum = getForum(pk)
		if forum == -1:
			return HttpResponse(status = 404)
		forumVector = getForumEmbeddings(forum)
		if len(forumVector[0]) == 0:
			t1 = threading.Thread(target = doInThread, args = [forum])
			t1.start()
			return HttpResponse(status = 409)
		otherForumVectors = []
		counter = 0
		forums = Forum.objects.exclude(pk = pk).order_by('id')
		forums2 = []
		for frm in forums:
			embs = frm.embedding_set.all().order_by('index')
			if len(embs) == 512:
				forums2.append(frm)
				otherForumVectors.append([])
				for em in embs:
					otherForumVectors[counter].append(em.value)
				counter += 1
		if len(otherForumVectors) == 0:
			return HttpResponse(status = 404)
		distances = scipy.spatial.distance.cdist(forumVector, otherForumVectors, "correlation")[0]
		finalResults = zip(forums2, distances)
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
		forum = getForum(pk)
		if forum == -1:
			return HttpResponse(status = 404)
		else:
			t1 = threading.Thread(target = doInThread, args = [forum])
			t1.start()
			return HttpResponse(status = 200)
	else:
		return HttpResponse(status = 405)


def doInThread(forum):
	if forum.embedding_set.count() == 0:
		model = SentenceTransformer('distiluse-base-multilingual-cased')
		forumVector = model.encode([forum.title])
		emb = zip(range(512), forumVector[0])
		Embedding.objects.bulk_create(
			[
				Embedding(
					question = forum,
					index = em[0],
					value = em[1]
				) for em in emb
			]
		)


def getForum(pk):
	try:
		forum = Forum.objects.get(pk = pk)
		return forum
	except Forum.DoesNotExist:
		return -1

def getForumEmbeddings(forum):
	forumVector = [[]]
	embs = forum.embedding_set.all().order_by('index')
	for em in embs:
		forumVector[0].append(em.value)
	return forumVector
		
