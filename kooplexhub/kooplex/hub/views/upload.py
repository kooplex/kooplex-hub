from django.conf.urls import patterns, url, include

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

from kooplex.hub.models import Fileform
from kooplex.hub.forms import DocumentForm

def list(request):
    # Handle file upload
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            newdoc = Fileform(docfile = request.FILES['docfile'])
            newdoc.save()

            # Redirect to the document list after POST
            return HttpResponseRedirect(reverse('hub.views.upload.list'))
    else:
        form = DocumentForm() # A empty, unbound form

    # Load documents for the list page
    documents = Fileform.objects.all()

    # Render list page with the documents and the form
    return render_to_response(
        'templates/app/list.html',
        {'documents': documents, 'form': form},
        context_instance=RequestContext(request)
    )

urlpatterns = [
    url(r'^$', list, name='upload')
]