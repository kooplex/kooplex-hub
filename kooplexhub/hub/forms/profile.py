from django.forms import ModelForm

from django.contrib.auth.models import User
from hub.models import Profile

class UserForm(ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

class ProfileForm(ModelForm):
    class Meta:
        model = Profile
        fields = ('bio', 'location', 'birth_date')
