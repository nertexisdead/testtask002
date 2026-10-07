from django.contrib import admin
from django.http import HttpResponse, JsonResponse
from django.urls import path


def health(request):
    return JsonResponse({"status": "ok"})


def home(request):
    return HttpResponse("<h1>Чек на удачу</h1><p>Пустой Django-проект готов к работе.</p>")


urlpatterns = [path("", home), path("admin/", admin.site.urls), path("health/", health)]
