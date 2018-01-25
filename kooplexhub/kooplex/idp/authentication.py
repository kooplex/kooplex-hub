import os
import logging
import requests

from kooplex.hub.models import User

logger = logging.getLogger(__name__)

def create_user(username, first_name, last_name, email):
    user = User(username = username, first_name = first_name, last_name = last_name, email = email)
    logger.info("Creating new user: %(username)s (%(first_name)s %(last_name)s; %(email)s)" % user)
    response = user.create()
    assert response['status_code'] == 0, response['messages']
    

############ these are used to manipulate with passwords stored locally
from .local import AuthBackend

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


