import re
import logging

from django.template import RequestContext
from django.conf.urls import url, include
from django.shortcuts import render, redirect
from django.http import HttpRequest
from django.contrib import messages

from kooplex.lib import get_settings
from kooplex.hub.models import User
from kooplex.idp.authentication import check_password, set_password
from kooplex.lib.sendemail import send_new_password

logger = logging.getLogger(__name__)

def passwordchangeForm(request):
    """Renders the password change page."""
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect('/')
    errors = []
    if request.method == 'POST':
        if 'btn_cabcel' in request.POST.keys():
            return redirect('/')
        elif 'btn_pwchange' in request.POST.keys():
            username = request.POST['username']  #FIXME: we could use request.user as the user is already authenticated
            oldpassword = request.POST['oldpassword']
            newpassword1 = request.POST['newpassword1']
            newpassword2 = request.POST['newpassword2']
            try:
                user = User.objects.get(username = username)
            except User.DoesNotExist:
                errors.append('Username is lost... are you hacking?')
            if not len(newpassword1):
                errors.append('You cannot have an empty password.')
            if not newpassword1 == newpassword2:
                errors.append('Your passwords do not match.')
            if not check_password(user, oldpassword):
                errors.append('Please check your old password.')
            if len(errors) == 0:
                set_password(user, newpassword1)
                return redirect('/')
    return render(
        request,
        'auth/passwordchange.html',
        context =  { 'errors': errors }
    )

def passwordresetForm(request):
    """Renders the password reset request page."""
    assert isinstance(request, HttpRequest)
    errors = []
    if request.method == 'POST':
        if 'btn_pwlogin' in request.POST.keys():
            return redirect('/hub/login')
        elif 'btn_sendtoken' in request.POST.keys():
            username = request.POST['username']
            email = request.POST['email']
            try:
                user = User.objects.get(username = username, email = email)
                user.sendtoken()
                return render(
                    request,
                    'auth/tokenpassword.html',
                    context =  { 'username': username }
                )
            except User.DoesNotExist:
                errors.append('Please provide valid username and e-mail address')
                user = None
    return render(
        request,
        'auth/passwordreset.html',
        context =  { 'errors': errors }
    )

def passwordtokenForm(request):
    """Renders the password reset token input form."""
    assert isinstance(request, HttpRequest)
    errors = []
    if request.method != 'POST':
        return render(
            request,
            'auth/passwordreset.html',
            context =  { }
        )
    username = request.POST['username']
    password1 = request.POST['password1']
    password2 = request.POST['password2']
    token = request.POST['token']
    try:
        user = User.objects.get(username = username)
    except User.DoesNotExist:
        errors.append('Username is lost... are you hacking?')
    if not user.is_validtoken(token):
        errors.append('Please check your e-mail for the token and type it.')
    if not len(password1):
        errors.append('You cannot have an empty password.')
    if not password1 == password2:
        errors.append('Your passwords do not match.')
    if len(errors):
        return render(
            request,
            'auth/tokenpassword.html',
            context =  { 'username': username, 'errors': errors }
        )
    set_password(user, password1)
    return redirect('/hub/login')

def guestAccountRequestForm(request):
    """Renders the guest account request input form."""
    assert isinstance(request, HttpRequest)
    error = False
    if request.method != 'POST':
        return render(
            request,
            'auth/guest.html',
            context =  { }
        )
    if 'btn_cancel' in request.POST:
        return redirect('/hub/login')
    username = request.POST['username'].strip()
    firstname = request.POST['firstname'].strip()
    lastname = request.POST['lastname'].strip()
    email = request.POST['email'].strip()
    if not re.match(get_settings('hub', 'pattern_guestusername'), username):
        messages.error(request, 'Username must follow the rules')
        error = True
    if not len(firstname):
        messages.error(request, 'First name must not be empty')
        error = True
    if not len(lastname):
        messages.error(request, 'Last name must not be empty')
        error = True
    if not re.match(r'[\w\.]+@\w+\.\w+', email):
        messages.error(request, 'E-mail should be valid')
        error = True
    try:
        user = User.objects.get(username = username)
        messages.error(request, 'Username is already in use')
        error = True
    except User.DoesNotExist:
        pass
    try:
        user = User.objects.get(email = email)
        messages.error(request, 'Email is already taken by another user')
        error = True
    except User.DoesNotExist:
        pass
    if error:
        return render(
            request,
            'auth/guest.html',
            context =  { }
        )

    try:
        user = User(username = username, first_name = firstname, last_name = lastname, email = email)
        user.create()
        logger.info("user created: %s" % user)
        mailstatus = send_new_password(user)
        if mailstatus == 0:
            messages.info(request, 'Try to log in with the password sent to %s' % email)
            user.save()
        else:
            messages.error(request, 'Cannot send an email to %s. Will remove this account.' % email)
            user.remove()
            user.delete()
    except Exception as e:
        messages.error(request, 'Error. Ask the administrator to check the logs. Removing account...')
        logger.error("Error during creation of a guest account %s -- %s" % (user, e))
        try:
            user.remove()
        except Exception as e:
            logger.error("Error during removal of a guest account %s -- %s" % (user, e))
        try:
            user.delete()
        except Exception as e:
            logger.error("Error during instance deletion of a guest account %s -- %s" % (user, e))

    return redirect('/hub/login')

def tokenchangeForm(request):
    from kooplex.logic.spawner import remove_container
    from kooplex.hub.models import ProjectContainer
    """Renders the password change page."""
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect('/')
    containers = ProjectContainer.objects.filter(user = request.user, is_running = True)
    if request.method == 'POST':
        if 'btn_cabcel' in request.POST.keys():
            return redirect('/')
        elif 'btn_tokenchange' in request.POST.keys():
            # remove those project containers running
            for container in containers:
                try:
                    remove_container(container)
                    msg = "Your running container %s has been removed." % container
                    messages.info(request, msg)
                    logger.info(msg)
                except Exception as e:
                    msg = "Exception thrown while removing your running container %s -- %s" % (container, e)
                    messages.error(request, msg)
                    logger.error(msg)
            # generate a new token
            request.user.settoken()
            messages.info(request, "Your new token is saved.")
    elif request.method == 'GET':
        # remove those project containers not running
        for container in ProjectContainer.objects.filter(user = request.user, is_running = False):
            try:
                remove_container(container)
                msg = "Your container %s, which was not running has been removed." % container
                logger.info(msg)
                messages.info(request, msg)
            except Exception as e:
                msg = "Exception thrown while removing your stopped container %s -- %s" % (container, e)
                messages.error(request, msg)
                logger.error(msg)
        if len(containers):
            return render(
                request,
                'auth/tokenchange.html',
                context =  { 'containers': containers }
            )
        else:
            # generate a new token
            request.user.settoken()
            messages.info(request, "Your new token is saved.")
    return redirect('/')

