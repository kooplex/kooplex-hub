"""
Definition of forms.
"""
import logging
logger = logging.getLogger(__name__)
from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import redirect

from kooplex.hub.models import User
from kooplex.lib import Gitlab

class BootstrapAuthenticationForm(AuthenticationForm):
    """Authentication form which uses boostrap CSS."""
    username = forms.CharField(
        max_length = 30, 
        widget = forms.TextInput( { 'class': 'form-control'} )
    )
    password = forms.CharField(
        max_length = 128, 
        widget=forms.PasswordInput( {'class': 'form-control' } )
    )

#HACK
    def __init__(self, req, *k, **kw):
        #is_bound = True
        #_errors = None
        #empty_permitted = True
#        super(AuthenticationForm, self)
        AuthenticationForm.__init__(self, req, *k, **kw)
        logger.debug("Login tortent")
        if req.method == 'POST':
            username = req.POST['username']
            password = req.POST['password']
            g = Gitlab()
            res, u = g.authenticate_user(username, password)
            if u is not None:
                try:
                    User.objects.get(username=username)
                except User.DoesNotExist:
                    # Authenticate user does not exist
                    # Create a new user.
                    user = User(
                        username=username,
                        email=u['email'],
                        is_superuser=u['is_admin'],
                        gitlab_id=u['id'])
                    user.save()
            redirect('projects')
        else:
            AuthenticationForm.__init__(self, req, *k, **kw)

    def confirm_login_allowed(self, user):
        #raise Exception("almafa")
        #raise forms.ValidationError( _("ALMA" + str(user)), code = 'debug' )
        return True
#ENDHACK

class BootstrapPasswordChangeForm(PasswordChangeForm):
    """Authentication form which uses boostrap CSS."""
    username = forms.CharField(max_length=254,
                               widget=forms.TextInput({
                                   'class': 'form-control',
                                   'placeholder': 'User name'}))
    oldpassword = forms.CharField(label=_("Password"),
                               widget=forms.PasswordInput({
                                   'class': 'form-control',
                                   'placeholder':'Password'}))
    newpassword1 = forms.CharField(label=_("Password"),
                               widget=forms.PasswordInput({
                                   'class': 'form-control',
                                   'placeholder': 'Password'}))
    newpassword2 = forms.CharField(label=_("Password"),
                               widget=forms.PasswordInput({
                                   'class': 'form-control',
                                   'placeholder': 'Password'}))

