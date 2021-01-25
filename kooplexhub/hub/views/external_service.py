import logging
import pwgen

from django.contrib import messages
from django.conf.urls import url, include
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django_tables2 import RequestConfig

from kooplex.lib import list_projects, test_token, upload_rsa, impersonator_repo
from kooplex.lib import list_libraries, impersonator_sync
from kooplex.lib import now
from kooplex.lib import seafilepw_update

from hub.forms import T_FSLIBRARY_SYNC
from hub.forms import T_REPOSITORY_CLONE
from hub.models import VCRepository, VCToken, VCProject, VCProjectServiceBinding
from hub.models import FSServer, FSToken, FSLibrary, FSLibraryServiceBinding

logger = logging.getLogger(__name__)


@login_required
def filesynchronization(request):
    user = request.user
    logger.debug("user %s" % user)
    pattern = request.POST.get('library', user.search.external_library)
    if pattern:
        libraries = FSLibrary.objects.filter(token__user = user, library_name__icontains = pattern)
    else:
        libraries = FSLibrary.objects.filter(token__user = user)
    if len(libraries) and pattern != user.search.external_library:
        user.search.external_library = pattern
        user.search.save()
    tbl_libraries = T_FSLIBRARY_SYNC(libraries)
    RequestConfig(request).configure(tbl_libraries)
    context_dict = {
        'next_page': 'service_external:filesync',
        'menu_service': 'active',
        'syncservers': FSServer.objects.all(),
        'tbl_libraries': tbl_libraries,
        'search_value': pattern,
    }
    return render(request, 'external_service/filesynchronization.html', context = context_dict)

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
    return redirect('service_external:filesync')


@login_required
def fs_newtoken(request, server_id):
    """Request a new token for the user"""
    user = request.user
    logger.debug("user %s" % user)
    try:
        fsserver = FSServer.objects.get(id = server_id)
        token = FSToken.objects.create(user = request.user, syncserver = fsserver, token = pwgen.pwgen(64))
        seafilepw_update(request.user.username, token.token)
        messages.info(request, f'Your seafile secret token is updated for {token.syncserver}')
    except Exception as e:
        logger.error(f"System abuse {request.user} {server_id} -- {e}")
        message.error(request, f"System abuse {e}")
    return redirect('service_external:filesync')


@login_required
def fs_resettoken(request, token_id):
    """Request a new password for the user"""
    user = request.user
    logger.debug("user %s" % user)
    token = FSToken.objects.get(user = request.user, id = token_id)
    token.token = pwgen.pwgen(64)
    token.save()
    seafilepw_update(request.user.username, token.token)
    messages.info(request, f'Your seafile secret token is updated for {token.syncserver}')
    return redirect('service_external:filesync')


@login_required
def fs_droptoken(request, token_id):
    """Drop user's password"""
    user = request.user
    logger.debug("user %s" % user)
    try:
        token = FSToken.objects.get(user = request.user, id = token_id)
        token.delete()
        messages.info(request, f'Your seafile secret token for {token.syncserver} is deleted')
    except FSToken.DoesNotExist:
        messages.error(request, f'Token deletion is denied')
    return redirect('service_external:filesync')


@login_required
def fs_commit(request):
    user = request.user
    logger.debug("user %s" % user)
    currently_syncing = [ l.library_id for l in FSLibrary.objects.filter(token__user = user, syncing = True) ]
    request_syncing = request.POST.getlist('sync_library_id')
    drop_cache = request.POST.getlist('dropcache_library_id')
    n_start = 0
    n_stop = 0
    n_drop = 0
    unbound = []
    for l_id in drop_cache:
        if l_id in request_syncing:
            request_syncing.remove(l_id)
        if l_id in currently_syncing:
            currently_syncing.remove(l_id)
        try:
            l = FSLibrary.objects.get(token__user = user, library_id = l_id)
            impersonator_sync(l, 'drop')
            for b in FSLibraryServiceBinding.objects.filter(fslibrary = l):
                unbound.append(b.service.name)
                b.service.mark_restart(f'synced library {l.library_name} deleted')
                b.delete()
            l.sync_folder = None
            l.syncing = False
            l.save()
            n_drop += 1
        except Exception as e:
            logger.error(e)
            raise #FIXME
    for l_id in request_syncing:
        if l_id in currently_syncing:
            currently_syncing.remove(l_id)
        else:
            try:
                l = FSLibrary.objects.get(token__user = user, syncing = False, library_id = l_id)
                l.sync_folder = impersonator_sync(l, 'start')
                l.syncing = True
                l.save()
                n_start += 1
            except Exception as e:
                logger.error(e)
                raise #FIXME
    for l_id in currently_syncing:
        try:
            l = FSLibrary.objects.get(token__user = user, syncing = True, library_id = l_id)
            impersonator_sync(l, 'stop')
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
    if n_drop:
        messages.info(request, "{} synchronization folders droped".format(n_drop))
    if unbound:
        messages.warning(request, 'Your environments {} need to be restarted'.format(', '.join(unbound)))
    return redirect('service_external:filesync')



@login_required
def versioncontrol(request):
    user = request.user
    logger.debug("user %s" % user)
    pattern = request.POST.get('repository', user.search.external_repository)
    if pattern:
        repositories = VCProject.objects.filter(token__user = user, project_name__icontains = pattern)
    else:
        repositories = VCProject.objects.filter(token__user = user)
    if len(repositories) and pattern != user.search.external_repository:
        user.search.external_repository = pattern
        user.search.save()
    tbl_repositories = T_REPOSITORY_CLONE(repositories)
    RequestConfig(request).configure(tbl_repositories)
    context_dict = {
        'next_page': 'service_external:versioncontrol',
        'menu_service': 'active',
        'reposervers': VCRepository.objects.all(),
        'tbl_repositories': tbl_repositories,
    }
    return render(request, 'external_service/versioncontrol.html', context = context_dict)







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
        for p_dict in list_projects(token):
            try:
                p = VCProject.objects.get(token = token, project_id = p_dict['id'])
                p.last_seen = now_
                p.save()
                old_list.remove(p)
                logger.debug('still present: {p[name]} of {p[owner_name]}'.format(p = p_dict))
            except VCProject.DoesNotExist:
                VCProject.objects.create(token = token, 
                       project_id = p_dict['id'],
                       project_name = p_dict['name'],
                       project_description = p_dict['description'],
                       project_created_at = p_dict['created_at'],
                       project_updated_at = p_dict['updated_at'],
                       project_fullname = p_dict['full_name'],
                       project_owner = p_dict['owner_name'],
                       project_ssh_url = p_dict['ssh_url']
                        )
                logger.debug('inserted present: {p[name]} of {p[owner_name]}'.format(p = p_dict))
                cnt_new += 1
        while len(old_list):
            p = old_list.pop()
            p.delete()
            #logger.debug('removed: {p.project_name} of {p.project_owner}'.format(p = p))
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
    return redirect('service_external:versioncontrol')


@login_required
def vc_commit(request):
    user = request.user
    logger.debug("user %s" % user)
    request_clone = request.POST.getlist('clone')
    request_rmcache = request.POST.getlist('removecache')
    clone_folders = []
    rmcache = []
    unbound = []
    for r_id in request_clone:
        try:
            r = VCProject.objects.get(token__user = user, cloned = False, id = r_id)
            r.clone_folder = impersonator_repo(r, 'clone')
            r.cloned = True
            r.save()
            clone_folders.append(r.clone_folder)
        except Exception as e:
            logger.error(e)
            messages.error(request, "clone oops -- {}".format(e))
    for r_id in request_rmcache:
        try:
            r = VCProject.objects.get(token__user = user, cloned = True, id = r_id)
            impersonator_repo(r, 'drop')
            for b in VCProjectServiceBinding.objects.filter(vcproject = r):
                unbound.append(b.service.name)
                b.service.mark_restart(f'version control repo {r.project_name} deleted')
                b.delete()
            rmcache.append(r.clone_folder)
            r.cloned = False
            r.clone_folder = None
            r.save()
        except Exception as e:
            logger.error(e)
            messages.error(request, "rm oops -- {}".format(e))
    if clone_folders:
        messages.info(request, "version control projects cloned in folders: {}".format(', '.join(clone_folders)))
    if rmcache:
        messages.info(request, "removed version control project folders: {}".format(', '.join(rmcache)))
    if unbound:
        messages.warning(request, 'Your environments {} need to be restarted'.format(', '.join(unbound)))
    return redirect('service_external:versioncontrol')


def vc_tokenmanagement(request, server_id):
    user = request.user
    logger.debug("user %s" % user)
    button = request.POST.get('button')
    token = request.POST.get('token').strip()
    un = request.POST.get('username').strip()
    try:
        assert len(token), "your token cannot be empty"
        assert len(un), "your username cannot be empty"
        repository = VCRepository.objects.get(id = server_id)
    except AssertionError as e:
        messages.error(request, "Cannot create your token: %s" % e)
        logger.error("user %s cannot save vctoken -- %s" % (user, e))
        return redirect('service_external:versioncontrol')
    except VCRepositoty.DoesNotExist:
        logger.error("user %s tries to access undefined repository" % (user))
        return redirect('service_external:versioncontrol')
    if button == 'newtoken':
        try:
            vctoken = VCToken.objects.create(repository = repository, user = user, username = un, token = token)
            messages.info(request, "Your vctoken for %s token is saved" % vctoken.repository)
            logger.info(f'Token created for {user} at {repository}')
            test_token(vctoken)
            upload_rsa(vctoken)
            logger.info(f'Generated RSA public kes uploaded.')
        except Exception as e:
            messages.error(request, "Cannot create your token")
            logger.error("user %s cannot save vctoken -- %s" % (user, e))
    elif button == 'updatetoken':
        try:
            token_id = request.POST.get('token_id')
            vctoken = VCToken.objects.get(repository = repository, user = user, id = token_id)
            vctoken.username = un
            vctoken.token = token
            test_token(vctoken)
            vctoken.save()
            messages.info(request, f'Your token for {vctoken.repository} is updated')
            logger.info(f'Token updated for {user} at {repository}')
        except Exception as e:
            messages.error(request, f"Cannot update your token: {e}")
            logger.error("user %s cannot update vctoken -- %s" % (user, e))
    return redirect('service_external:versioncontrol')


@login_required
def vc_droptoken(request, token_id):
    """Drop user's password"""
    user = request.user
    logger.debug("user %s" % user)
    try:
        token = VCToken.objects.get(user = request.user, id = token_id)
        token.delete()
        messages.info(request, f'Your seafile secret token for {token.repository} is deleted')
    except VCToken.DoesNotExist:
        messages.error(request, f'Token deletion is denied')
    return redirect('service_external:versioncontrol')


urlpatterns = [
    url(r'^filesynchronization', filesynchronization, name = 'filesync'), 
    url(r'^fs_search', filesynchronization, name = 'fs_search'), 
    url(r'^fs_refresh/(?P<token_id>\d+)', fs_refresh, name = 'fs_refresh'), 
    url(r'^fs_newtoken/(?P<server_id>\d+)', fs_newtoken, name = 'fs_newtoken'), 
    url(r'^fs_resettoken/(?P<token_id>\d+)', fs_resettoken, name = 'fs_resettoken'), 
    url(r'^fs_droptoken/(?P<token_id>\d+)', fs_droptoken, name = 'fs_droptoken'), 
    url(r'^fs_commit', fs_commit, name = 'commit_sync'), 

    url(r'^versioncontrol', versioncontrol, name = 'versioncontrol'), 
    url(r'^vc_search', versioncontrol, name = 'vc_search'), 
    url(r'^vc_refresh/(?P<token_id>\d+)', vc_refresh, name = 'vc_refresh'), 
    url(r'^vc_token/(?P<server_id>\d+)', vc_tokenmanagement, name = 'vc_tokenmanagement'),
    url(r'^vc_clone', vc_commit, name = 'commit_repo'), 
]

