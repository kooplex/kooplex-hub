"""
Definition of forms.
"""
import logging
from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import redirect

from kooplex.hub.models import User
from kooplex.idp import authenticate

logger = logging.getLogger(__name__)

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
        logger.debug("Login")
        if req.method == 'POST':
            username = req.POST['username']
            password = req.POST['password']
            authenticated_flag, userdscriptor = authenticate(username, password)
            if authenticated_flag:
                try:
                    User.objects.get(username = username)
                except User.DoesNotExist:
                    User(**userdscriptor).save()
            redirect('projects')
        else:
            AuthenticationForm.__init__(self, req, *k, **kw)

    def confirm_login_allowed(self, user):
#        raise Exception("almafa %s" % user )
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

