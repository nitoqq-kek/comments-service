from django.conf import settings
from django.conf.urls import url
from django.contrib import admin
from django.shortcuts import render
from django.urls import path, include
from rest_framework_jwt.views import obtain_jwt_token

from comments.views import router

urlpatterns = [
    path('admin/', admin.site.urls),
    url(r'^', include(router.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^api-token-auth/', obtain_jwt_token),
]

def kek(request):
    return render(request, 'websocket.html')

if settings.DEBUG:
    import django.views.static

    # static files (images, css, javascript, etc.)
    urlpatterns += [
        url(r'^media/(?P<path>.*)$', django.views.static.serve, {
            'document_root': settings.MEDIA_ROOT
        })
    ]
