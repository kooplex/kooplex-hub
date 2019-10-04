import logging

from django.contrib import messages
from django.conf.urls import url, include
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
#from django.contrib.auth.models import User
#from django.utils.html import format_html
#import django_tables2 as tables
from django_tables2 import RequestConfig
#from django.utils.translation import gettext_lazy as _
#from django.db.models import Q
#
#from kooplex.lib import list_projects
from kooplex.lib import list_libraries, impersonator_sync
from kooplex.lib import now
#
#from hub.forms import FormProject
#from hub.forms import table_collaboration, T_JOINABLEPROJECT
#from hub.forms import table_volume
#from hub.forms import table_vcproject
from hub.forms import T_FSLIBRARY_SYNC
#from hub.models import Project, UserProjectBinding, Volume
#from hub.models import Image
#from hub.models import Profile
#from hub.models import VCToken, VCProject, VCProjectProjectBinding, ProjectContainerBinding
from hub.models import FSToken, FSLibrary#, FSLibraryProjectBinding#, ProjectContainerBinding
#
#from django.utils.safestring import mark_safe
#
logger = logging.getLogger(__name__)


@login_required
def filesynchronization(request):
    user = request.user
    logger.debug("user %s" % user)
    fs_tokens = FSToken.objects.filter(user = user)
    pattern = request.POST.get('library', '')
    libraries = FSLibrary.f_user(user = user) if pattern == '' else FSLibrary.f_user_namelike(user = user, l = pattern)
    tbl_libraries = T_FSLIBRARY_SYNC(libraries)
    RequestConfig(request).configure(tbl_libraries)
    context_dict = {
        'next_page': 'service:filesync',
        'menu_service': 'active',
        'submenu': 'filesynch',
        'fs_tokens': fs_tokens,
        'tbl_libraries': tbl_libraries,
        'search_library': pattern,
    }
    return render(request, 'service/filesynchronization.html', context = context_dict)

@login_required
def fs_refresh(request, token_id):
    """Refresh users file snchronization libraries."""
    user = request.user
    logger.debug("user %s" % user)
    try:
        now_ = now()
        token = FSToken.objects.get(user = user, id = token_id)
        old_list = list(FSLibrary.objects.filter(token = token))
        cnt_new = 0
        cnt_del = 0
        for r in list_libraries(token):
            try:
                l = FSLibrary.objects.get(token = token, library_name = r.name, library_id = r.id)
                l.last_seen = now_
                l.save()
                old_list.remove(l)
                logger.debug('still present: %s' % r.name)
            except FSLibrary.DoesNotExist:
                FSLibrary.objects.create(token = token, library_name = r.name, library_id = r.id)
                logger.debug('inserted present: %s' % r.name)
                cnt_new += 1
        while len(old_list):
            l = old_list.pop()
            l.remove()
            logger.debug('removed: %s' % l.library_name)
            cnt_del += 1
        if cnt_new:
            messages.info(request, "%d new libraries found" % cnt_new)
        if cnt_del:
            messages.warning(request, "%d libraries removed" % cnt_del)
        token.last_used = now_
        token.save()
    except FSToken.DoesNotExist:
        messages.error(request, "System abuse")
    except Exception as e:
        messages.error(request, "System abuse -- %s" % e)
    return redirect('service:filesync')


@login_required
def fs_commit(request):
    user = request.user
    logger.debug("user %s" % user)
    currently_syncing = [ l.library_id for l in FSLibrary.objects.filter(token__user = user, syncing = True) ]
    request_syncing = request.POST.getlist('sync_library_id')
    n_start = 0
    n_stop = 0
    for l_id in request_syncing:
        if l_id in currently_syncing:
            currently_syncing.remove(l_id)
        else:
            try:
                l = FSLibrary.objects.get(token__user = user, syncing = False, library_id = l_id)
                impersonator_sync(l, start = True)
                l.syncing = True
                l.save()
                n_start += 1
            except Exception as e:
                logger.error(e)
                raise #FIXME
    for l_id in currently_syncing:
        try:
            l = FSLibrary.objects.get(token__user = user, syncing = True, library_id = l_id)
            impersonator_sync(l, start = False)
            l.syncing = False
            l.save()
            n_stop += 1
        except Exception as e:
            logger.error(e)
            raise #FIXME
    if n_start:
        messages.info(request, "{} new synchronization processes started".format(n_start))
    if n_stop:
        messages.info(request, "{} old synchronization processes stopped".format(n_stop))
    return redirect('service:filesync')


def nothing(request):
    messages.error(request, 'NOT IMPLEMETED YET')
    return redirect('indexpage')

urlpatterns = [
    url(r'^filesynchronization', filesynchronization, name = 'filesync'), 
    url(r'^fs_search', filesynchronization, name = 'fs_search'), 
    url(r'^fs_refresh/(?P<token_id>\d+)', fs_refresh, name = 'fs_refresh'), 
    url(r'^fs_commit', fs_commit, name = 'commit_sync'), 

    url(r'^versioncontrol', nothing, name = 'versioncontrol'), 
]

