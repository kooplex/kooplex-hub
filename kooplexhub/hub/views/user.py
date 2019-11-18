import logging
import pwgen

from django.conf.urls import url
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from hub.forms import FormBiography
from hub.forms import table_vctoken
from hub.models import VCRepository, VCToken, FSServer, FSToken
from kooplex.lib import seafilepw_update

logger = logging.getLogger(__name__)


@login_required
def updateprofile(request, next_page):
    logger.debug("user %s" % request.user)
    user_id = request.POST.get('user_id')
    if user_id is not None and int(user_id) == request.user.id:
        form = FormBiography(request.POST, instance = request.user.profile)
        form.save()
        messages.info(request, 'Your profile is updated')
    else:
        logger.error("user id mismatch: %s tries to save %s %s" % (request.user, request.user.id, request.POST.get('user_id')))
        messages.error(request, 'Profile update is refused.')
    return redirect(next_page)


@login_required
def managetoken(request, next_page):
    user = request.user
    logger.debug("user %s" % user)
    button = request.POST.get('button')
    if request.method == 'GET':
        context_dict = {
            't_vctoken': table_vctoken(user),
            'next_page': next_page,
        }
        return render(request, 'usertokens.html', context = context_dict)
    elif button == 'reset_notebook_token':
        return redirect('user:changetoken', next_page)
    elif button == 'reset_seaf_token':
        return redirect('user:changeseaftoken', next_page)
    elif button == 'apply':
        token_ids = request.POST.getlist('token_ids')
        for rm_token_id in request.POST.getlist('rm_token_ids'):
            try:
                token_ids.remove(rm_token_id)
                VCToken.objects.get(id = rm_token_id, user = user).delete()
                messages.info(request, "Deleted your token and related vcprojects")
                logger.debug("user %s deleted vctoken" % user)
            except Exception as e:
                logger.debug("user %s tried to delete vctoken id %s -- %s" % (user, rm_token_id, e))
        for new_repository_id in request.POST.getlist('new_repository_ids'):
            try:
                repository = VCRepository.objects.get(id = new_repository_id)
                fn_rsa = request.POST.get('fn_rsa-%s' % new_repository_id)
                token = request.POST.get('token-%s' % new_repository_id)
                un = request.POST.get('username-%s' % new_repository_id)
                assert len(fn_rsa), "The RSA filename cannot be empty"
                assert len(token), "Your token cannot be empty"
                vctoken = VCToken.objects.create(repository = repository, user = user, username = un, fn_rsa = fn_rsa, token = token)
                messages.info(request, "Your vctoken %s token is saved" % vctoken)
            except Exception as e:
                messages.error(request, "Cannot create your token -- %s" % e)
                logger.error("user %s cannot save vctoken" % (user))
        for tid in token_ids:
            try:
                fn_rsa_before = request.POST.get('fn_rsa_before-%s' % tid)
                token_before = request.POST.get('token_before-%s' % tid)
                un_before = request.POST.get('username_before-%s' % tid)
                fn_rsa = request.POST.get('fn_rsa_after-%s' % tid)
                token = request.POST.get('token_after-%s' % tid)
                un = request.POST.get('username_after-%s' % tid)
                assert len(fn_rsa), "The RSA filename cannot be empty"
                assert len(token), "Your token cannot be empty"
                if fn_rsa_before == fn_rsa and token_before == token and un_before == un:
                    continue
                vctoken = VCToken.objects.get(id = tid, user = user, username = un_before, fn_rsa = fn_rsa_before, token = token_before)
                vctoken.fn_rsa = fn_rsa
                vctoken.token = token
                vctoken.username = un
                vctoken.save()
                messages.info(request, "Your vctoken %s token is updated" % vctoken)
            except Exception as e:
                messages.error(request, "Cannot create your token -- %s" % e)
                logger.error("user %s cannot save vctoken" % (user))
        return redirect(next_page)
    else:
        messages.error(request, 'Abused call')
        return redirect(next_page)


@login_required
def changetoken(request, next_page):
    logger.debug("user %s" % request.user)
    profile = request.user.profile
    profile.token = pwgen.pwgen(64)
    profile.save()
    messages.warning(request, 'Your secret token is updated. You will not be able to access your running containers until you restart them.')
    return redirect(next_page)


@login_required
def changeseaftoken(request, next_page):
    #TODO: what if more fs servers present???
    logger.debug("user %s" % request.user)
    try:
        token = FSToken.objects.get(user = request.user)
        token.token = pwgen.pwgen(64)
        token.save()
        messages.warning(request, 'Your seafile secret token is updated. You may experience problem with running file syncronization tasks.')
    except FSToken.DoesNotExist:
        fsserver = FSServer.objects.all()[0]  #FIXME: ugly
        token = FSToken.objects.create(user = request.user, syncserver = fsserver, token = pwgen.pwgen(64))
        token.save()
        messages.info(request, 'New seafile secret token is created for %s' % fsserver)
    seafilepw_update(request.user.username, token.token)
    return redirect(next_page)


urlpatterns = [
    url(r'^profile/(?P<next_page>\w+:?\w*)$', updateprofile, name = 'updateprofile'),
    url(r'^token/(?P<next_page>\w+:?\w*)$', changetoken, name = 'changetoken'),
    url(r'^token/seafile/(?P<next_page>\w+:?\w*)$', changeseaftoken, name = 'changeseaftoken'),
    url(r'^manage/(?P<next_page>\w+:?\w*)$', managetoken, name = 'managetokens'),
]

