import os
from django.core.cache import cache
from django.shortcuts import render
 
 
ZOOM_API_KEY = os.environ.get('ZOOM_API_KEY')
ZOOM_API_SEC = os.environ.get('ZOOM_API_SEC')
 

def view(request):
    data = cache.get(request.GET['token'])
    data.update(role=1 if request.GET['username'] == data['username'] else 0)
    return render(request, 'zoom.html', dict(ZOOM_SDK_KEY=ZOOM_API_KEY, ZOOM_SDK_SEC=ZOOM_API_SEC, DATA=data, USERNAME=request.GET['username']))
 