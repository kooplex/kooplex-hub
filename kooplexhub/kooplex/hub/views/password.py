from django.template import RequestContext
from django.conf.urls import url, include
from django.shortcuts import render, redirect
from django.http import HttpRequest

from kooplex.hub.models import User
from kooplex.idp.authentication import check_password, set_password

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
        context_instance = RequestContext(request, { 'errors': errors })
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
                    context_instance = RequestContext(request, { 'username': username })
                )
            except User.DoesNotExist:
                errors.append('Please provide valid username and e-mail address')
                user = None
    return render(
        request,
        'auth/passwordreset.html',
        context_instance = RequestContext(request, { 'errors': errors })
    )

def passwordtokenForm(request):
    """Renders the password reset token input form."""
    assert isinstance(request, HttpRequest)
    errors = []
    if request.method != 'POST':
        return render(
            request,
            'auth/passwordreset.html',
            context_instance = RequestContext(request, { })
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
            context_instance = RequestContext(request, { 'username': username, 'errors': errors })
        )
    user.changepassword(password1)
    return redirect('/hub/login')

