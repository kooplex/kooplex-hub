import logging
import os

from urllib.parse import urlencode
from social_core.backends.open_id_connect import BaseOAuth2

from kooplexhub.settings import KOOPLEX_OID_AUTHORIZATION_URL, KOOPLEX_OID_ACCESS_TOKEN_URL, FQDN_AUTH

logger = logging.getLogger(__name__)

class KooplexOpenID(BaseOAuth2):
    name = 'kooplex'
    AUTHORIZATION_URL = KOOPLEX_OID_AUTHORIZATION_URL
    ACCESS_TOKEN_URL = KOOPLEX_OID_ACCESS_TOKEN_URL
    ACCESS_TOKEN_METHOD = 'POST'
    SCOPE_SEPARATOR = ','

    def get_user_details(self, response):
        # logging
        logger.debug("Oauth user data {}".format(response))
        return { 'username': response.get('username'),
                 'email': response.get('email') or '',
                 'first_name': response.get('first_name') or '',
                 'last_name': response.get('last_name') or '',
                 }

    def user_data( self, access_token, *args, **kwargs):
        url = f'https://{FQDN_AUTH}/oauth/profile?' + urlencode({'access_token': access_token})
        return self.get_json(url)

