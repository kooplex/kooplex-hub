import os
import logging
import requests

from kooplex.lib import get_settings, keeptrying
from kooplex.hub.models import User

logger = logging.getLogger(__name__)

def create_user(username, first_name, last_name, email):
    raise NotImplementedError

def check_password(user, password):
    logger.debug(user)
    backend = AuthBackend()
    user_back = backend.authenticate(username = user.username, password = password)
    return user_back == user

def set_password(user, password):
    from kooplex.lib import Ldap
    logger.debug(user)
    user.changepassword(password)
    Ldap().changepassword(user, password)


