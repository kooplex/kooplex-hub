"""
Definition of forms.
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.utils.translation import ugettext_lazy as _

class BootstrapAuthenticationForm(AuthenticationForm):
    """Authentication form which uses boostrap CSS."""
    username = forms.CharField(
        max_length = 30, 
        widget = forms.TextInput( { 'class': 'form-control' } )
    )
    password = forms.CharField(
        max_length = 128, 
        widget=forms.PasswordInput( {'class': 'form-control' } )
    )

#HACK
    def __init__(self, req, *k, **kw):
        if req.method != 'GET':
            raise Exception(str(req) + str(k) + str(kw))
        AuthenticationForm.__init__(self, req, *k, **kw)

    def confirm_login_allowed(self, user):
        raise Exception("almafa")
        raise forms.ValidationError( _("ALMA" + str(user)), code = 'debug' )
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

