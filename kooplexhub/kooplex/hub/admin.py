from django.conf.urls import patterns, url, include
from django.shortcuts import render
from django.http import HttpRequest, HttpResponseRedirect,HttpResponse
from django.template import RequestContext
from django.contrib import admin
from kooplex.hub.models.notebook import Notebook
from kooplex.hub.models.session import Session
from kooplex.hub.models.container import Container


# Register your models here.
@admin.register(Notebook)
class NotebookAdmin(admin.ModelAdmin):
    pass

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    pass

@admin.register(Container)
class ContainerAdmin(admin.ModelAdmin):
    pass

def admin_main(request):
    print("Hello")
    vmi=[]
    return render(
        request,
        'app/admin.html',
        context_instance=RequestContext(request,
                                        {
                                            'vmi' : vmi,
                                        })
    )


urlpatterns = [
 url(r'^', admin_main, name='admin_main'),
]