"""
Definition of forms.
"""
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import ugettext_lazy as _

class authenticationForm(AuthenticationForm):
    """Authentication form which uses boostrap CSS."""
    username = forms.CharField(
        max_length = 30, 
        widget = forms.TextInput( { 'class': 'form-control' } )
    )
    password = forms.CharField(
        max_length = 128, 
        widget=forms.PasswordInput( {'class': 'form-control' } )
    )

