from django.urls import path, re_path, include
from slth import urls
from django.conf import settings

from slth.views import dispatcher, index, service_worker, media
from django.shortcuts import render

urlpatterns = [
    path('', index),
    path('service-worker.js', service_worker),
    re_path(r'^app/(?P<path>.*)/$', index),
    path('api/', include(urls)),
    path('', dispatcher),
    path('zoom/', lambda request: render(request, 'zoom.html', {})),
    path('media/<path:file_path>/', media, name='secure_media'),
]
