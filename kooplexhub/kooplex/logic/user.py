import logging
import pwgen

from kooplex.lib import get_settings
from kooplex.lib import Ldap
from kooplex.lib.sendemail import send_new_password, send_token
from kooplex.lib.filesystem import mkdir_homefolderstructure, cleanup_home, write_davsecret, generate_rsakey, read_rsapubkey

#FIXME:
class GitlabAdmin: pass

logger = logging.getLogger(__name__)

def generatenewpassword(user):
    # generate password
    user.password = pwgen.pwgen(12)
    with open(get_settings('user', 'pattern_passwordfile') % user, 'w') as f:
        f.write(user.password)

def add(user, skip_gitlab = False):
    logger.debug('call %s' % user)
    status = 0
    generatenewpassword(user)
    # create new ldap entry
    try:
        Ldap().adduser(user)
    except Exception as e:
        logger.error("Failed to create ldap entry for %s (%s)" % (user, e))
        status |= 0x000001
    # create home filesystem save dav secret
    try:
        mkdir_homefolderstructure(user)
        write_davsecret(user)
    except Exception as e:
        logger.error("Failed to create home for %s (%s)" % (user, e))
        status |= 0x000010
    # create gitlab account
    if not skip_gitlab: #NOTE: this is a temporary check; to be removed if not the gitlab is the IDP
        try:
            gad = GitlabAdmin()
            gad.create_user(user)
        except Exception as e:
            logger.error("Failed to create gitlab entry for %s (%s)" % (user, e))
            status |= 0x000100
    # retrieve gitlab_id
    try:
        data = gad.get_user(user)[0]
        user.gitlab_id = data['id']
    except Exception as e:
        logger.error("Failed to fetch gitlab id for %s (%s)" % (user, e))
        status |= 0x001000
    # generate and upload rsa key
    try:
        generate_rsakey(user)
        pub_key_content = read_rsapubkey(user)
        gad.upload_userkey(user, pub_key_content)
    except Exception as e:
        logger.error("Failed to upload rsa key in gitlab for %s (%s)" % (user, e))
        status |= 0x010000
        raise
    # send email with the password
    if send_new_password(user) != 0:
        logger.error("Failed to send email to %s (%s)" % (user, user.email))
        status |= 0x100000
    return status

def remove(user):
    logger.debug('call %s' % user)
    status = 0
    # remove ldap entry
    try:
        Ldap().removeuser(user)
    except Exception as e:
        logger.error("Failed to create ldap entry for %s (%s)" % (user, e))
        status |= 0x001
    # remove folders from the filesyystem
    status_fs = cleanup_home(user)
    if status_fs != 0:
        status |= 0x010
        logger.error("Failed to remove some directories for %s (status: %d)" % (user, status_fs))
    # remove gitlab account
    try:
        gad = GitlabAdmin()
        gad.delete_user(user)
    except Exception as e:
        logger.error("Failed to delete gitlab entry for %s (%s)" % (user, e))
        status |= 0x100
    return status
