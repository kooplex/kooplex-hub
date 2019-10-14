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
from kooplex.lib import list_projects, impersonator_clone, impersonator_removecache
from kooplex.lib import list_libraries, impersonator_sync
from kooplex.lib import now
#
#from hub.forms import FormProject
#from hub.forms import table_collaboration, T_JOINABLEPROJECT
#from hub.forms import table_volume
#from hub.forms import table_vcproject
from hub.forms import T_FSLIBRARY_SYNC
from hub.forms import T_REPOSITORY_CLONE
#from hub.models import Project, UserProjectBinding, Volume
#from hub.models import Image
#from hub.models import Profile
from hub.models import VCToken, VCProject#, VCProjectProjectBinding, ProjectContainerBinding
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
    libraries = FSLibrary.objects.filter(token__user = user) if pattern == '' else FSLibrary.objects.filter(token__user = user, library_name__icontains = pattern)
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
            l.delete()
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



@login_required
def versioncontrol(request):
    user = request.user
    messages.error(request, "not implemented fully yet")
    logger.debug("user %s" % user)
    vc_tokens = VCToken.objects.filter(user = user)  #FIXME: user.profile.vctokens HASZNALJUK VALAHOL
    pattern = request.POST.get('repository', '')
    repositories = VCProject.objects.filter(token__user = user) if pattern == '' else VCProject.objects.filter(token__user = user, project_name__icontains = pattern)
    tbl_repositories = T_REPOSITORY_CLONE(repositories)
    RequestConfig(request).configure(tbl_repositories)
    context_dict = {
        'next_page': 'service:versioncontrol',
        'menu_service': 'active',
        'submenu': 'versioncontrol',
        'vc_tokens': vc_tokens,
        'tbl_repositories': tbl_repositories,
        'search_repo': pattern,
    }
    return render(request, 'service/versioncontrol.html', context = context_dict)

@login_required
def vc_refresh(request, token_id):
    """Refresh users version control repositories."""
    user = request.user
    logger.debug("user %s" % user)
    try:
        now_ = now()
        token = VCToken.objects.get(user = user, id = token_id)
        old_list = list(VCProject.objects.filter(token = token))
        cnt_new = 0
        cnt_del = 0
        for p_name in list_projects(token):
            try:
                p = VCProject.objects.get(token = token, project_name = p_name)
                p.last_seen = now_
                p.save()
                old_list.remove(p)
                logger.debug('still present: %s' % p_name)
            except VCProject.DoesNotExist:
                VCProject.objects.create(token = token, project_name = p_name)
                logger.debug('inserted present: %s' % p_name)
                cnt_new += 1
        while len(old_list):
            p = old_list.pop()
            p.delete()
            logger.debug('removed: %s' % p.project_name)
            cnt_del += 1
        if cnt_new:
            messages.info(request, "%d new project items found" % cnt_new)
        if cnt_del:
            messages.warning(request, "%d project items removed" % cnt_del)
        token.last_used = now_
        token.save()
    except VCToken.DoesNotExist:
        messages.error(request, "System abuse")
    except Exception as e:
        messages.error(request, "System abuse -- %s" % e)
    return redirect('service:versioncontrol')


@login_required
def vc_commit(request):
    user = request.user
    logger.debug("user %s" % user)
    request_clone = request.POST.getlist('clone')
    request_rmcache = request.POST.getlist('removecache')
    n_clone = 0
    n_rmcache = 0
    for r_id in request_clone:
        try:
            r = VCProject.objects.get(token__user = user, cloned = False, id = r_id)
            impersonator_clone(r)
            r.cloned = True
            r.save()
            n_clone += 1
        except Exception as e:
            logger.error(e)
            raise #FIXME
    for r_id in request_rmcache:
        try:
            r = VCProject.objects.get(token__user = user, cloned = True, id = r_id)
            impersonator_removecache(r)
            r.cloned = False
            r.save()
            n_rmcache += 1
        except Exception as e:
            logger.error(e)
            raise #FIXME
    if n_clone:
        messages.info(request, "{} version control projects cloned".format(n_clone))
    if n_rmcache:
        messages.info(request, "{} version control project folders removed".format(n_rmcache))
    return redirect('service:versioncontrol')



def nothing(request):
    messages.error(request, 'NOT IMPLEMETED YET')
    return redirect('indexpage')

urlpatterns = [
    url(r'^filesynchronization', filesynchronization, name = 'filesync'), 
    url(r'^fs_search', filesynchronization, name = 'fs_search'), 
    url(r'^fs_refresh/(?P<token_id>\d+)', fs_refresh, name = 'fs_refresh'), 
    url(r'^fs_commit', fs_commit, name = 'commit_sync'), 

    url(r'^versioncontrol', versioncontrol, name = 'versioncontrol'), 
    url(r'^vc_search', versioncontrol, name = 'vc_search'), 
    url(r'^vc_refresh/(?P<token_id>\d+)', vc_refresh, name = 'vc_refresh'), 
    url(r'^vc_clone', vc_commit, name = 'commit_repo'), 
]

