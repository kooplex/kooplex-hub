import logging
import re
import pwgen

from kooplex.lib import get_settings
from kooplex.lib import Ldap, GitlabAdmin
from kooplex.lib.sendemail import send_new_password, send_token
from kooplex.lib.filesystem import mkdir_homefolderstructure, cleanup_home, write_davsecret, generate_rsakey, read_rsapubkey
from kooplex.logic.impersonator import update_fstab
from kooplex.hub.models import User

logger = logging.getLogger(__name__)

def generatenewpassword(user):
    # generate password
    user.password = pwgen.pwgen(12)
    with open(get_settings('user', 'pattern_passwordfile') % user, 'w') as f:
        f.write(user.password)

def add(user):
    """
    @summary: create a new user
              1. generate a password
              2. create an ldap entry
              3. create home directory structure
              4. create a gitlab account
              5. generate and upload RSA key
              6. update fstab in impersonator container
    @param user: a new user to add to the system
    @type user: kooplex.hub.models.User
    @returns: { 'status_code': int, 'messages': list(str) }
              status_code:
              - flag: 0x000001: wrong characters in username or username or email already in use
              - flag: 0x000010: ldap failure
              - flag: 0x000100: filesystem failure
              - flag: 0x001000: gitlab add failure
              - flag: 0x010000: gitlab upload failure
              - flag: 0x100000: fstab update error
    """
    logger.debug('call %s' % user)
    # check
    wrong_characters = "".join( re.split('[a-z0-9]+', user.username) )
    if wrong_characters != "":
        msg = "Username contains blacklisted characters: %s" % wrong_characters
        logger.error(msg)
        return { 'status_code': 0x00001, 'messages': [ msg ] }
    try:
        User.objects.get(username = user.username)
        msg = "Username already exists: %s" % user
        logger.error(msg)
        return { 'status_code': 0x00001, 'messages': [ msg ] }
    except User.DoesNotExist:
        pass
    try:
        User.objects.get(email = user.email)
        msg = "Email is already registered: %s" % user
        logger.error(msg)
        return { 'status_code': 0x00001, 'messages': [ msg ] }
    except User.DoesNotExist:
        pass

    status = 0
    messages = []
    generatenewpassword(user)
    # create new ldap entry
    try:
        Ldap().adduser(user)
    except Exception as e:
        msg = "Failed to create ldap entry for %s (%s)" % (user, e)
        logger.error(msg)
        messages.append(msg)
        status |= 0x000010
    # create home filesystem save dav secret
    try:
        mkdir_homefolderstructure(user)
        write_davsecret(user)
    except Exception as e:
        msg = "Failed to create home for %s (%s)" % (user, e)
        logger.error(msg)
        messages.append(msg)
        status |= 0x000100
    # create gitlab account and retrieve new user's gitlab_id
    try:
        gad = GitlabAdmin()
        user.gitlab_id = gad.create_user(user)['id']
    except Exception as e:
        msg = "Failed to create gitlab entry for %s (%s)" % (user, e)
        logger.error(msg)
        messages.append(msg)
        status |= 0x001000
    # generate and upload rsa key
    try:
        generate_rsakey(user)
        pub_key_content = read_rsapubkey(user)
        gad.upload_userkey(user, pub_key_content)
    except Exception as e:
        msg = "Failed to upload rsa key in gitlab for %s (%s)" % (user, e)
        logger.error(msg)
        messages.append(msg)
        status |= 0x010000
    try:
        update_fstab()
    except Exception as e:
        status |= 0x100000
        msg = 'cannot update /etc/fstab in impersonator container -- %s' % e
        logger.error(msg)
        messages.append(msg)
    return { 'status_code': status, 'messages': messages }

def remove(user):
    """
    @summary: remove a user
              1. delete ldap entry
              2. garbage collect home directory structure
              3. remove a gitlab account
              4. update fstab in impersonator container
    @param user: the user to be removed from the system
    @type user: kooplex.hub.models.User
    @returns: { 'status_code': int, 'messages': list(str) }
              status_code:
              - flag: 0x0001: ldap failure
              - flag: 0x0010: filesystem failure
              - flag: 0x0100: gitlab removeuser failure
              - flag: 0x1000: fstab update error
    """
    logger.debug('call %s' % user)
    status = 0
    # remove ldap entry
    try:
        Ldap().removeuser(user)
    except Exception as e:
        logger.error("Failed to remove ldap entry for %s (%s)" % (user, e))
        status |= 0x0001
    # remove folders from the filesyystem
    status_fs = cleanup_home(user)
    if status_fs != 0:
        status |= 0x0010
        logger.error("Failed to remove some directories for %s (status: %d)" % (user, status_fs))
    # remove gitlab account
    try:
        GitlabAdmin().delete_user(user)
    except Exception as e:
        logger.error("Failed to delete gitlab entry for %s (%s)" % (user, e))
        status |= 0x0100
    try:
        update_fstab()
    except Exception as e:
        status |= 0x1000
        msg = 'cannot update /etc/fstab in impersonator container -- %s' % e
        logger.error(msg)
        messages.append(msg)
    return status
