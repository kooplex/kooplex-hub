import os

from social_core.backends.google import GoogleOAuth2

from kooplex.settings import KOOPLEX

class my_GoogleOAuth2(GoogleOAuth2):
    def get_redirect_uri(self, state = None):
        """Build redirect with redirect_state parameter."""
        base_url = KOOPLEX.get('base_url', 'http://localhost')
        url = os.path.join(base_url, "hub/oauth/complete/google-oauth2/")
        if self.REDIRECT_STATE and state:
            uri = url_add_parameters(url, {'redirect_state': state})
        else:
            uri = url
        return uri

