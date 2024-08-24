import os
from django.shortcuts import render
 
 
ZOOM_API_KEY = os.environ.get('ZOOM_API_KEY')
ZOOM_API_SEC = os.environ.get('ZOOM_API_SEC')
 

def view(request):
    return render(request, 'zoom.html', dict(ZOOM_SDK_KEY=ZOOM_API_KEY, ZOOM_SDK_SEC=ZOOM_API_SEC))
 