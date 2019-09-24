import logging
import os

from social_core.backends.open_id_connect import OpenIdConnectAuth

from hub.models import CourseCode, UserCourseCodeBinding
from kooplex.settings import KOOPLEX

logger = logging.getLogger(__name__)


class my_ElteOpenID(OpenIdConnectAuth):
    name = 'elteoidc'
    OIDC_ENDPOINT = 'https://auth.elte.hu:4444'

    def get_redirect_uri(self, state = None):
        """Build redirect with redirect_state parameter."""
        base_url = KOOPLEX.get('base_url', 'http://localhost')
        url = os.path.join(base_url, "hub/oauth/complete/elteoidc/")
        if self.REDIRECT_STATE and state:
            uri = url_add_parameters(url, {'redirect_state': state})
        else:
            uri = url
        logger.debug("init: %s" % uri)
        return uri

    def get_user_details(self, response):
        logger.debug(str(response))
        return {
            'username': response['idp_user'],
            'email': response['mail'][0],
            'fullname': response['displayName'][0],
            'first_name': response['givenName'][0],
            'last_name': response['sn'][0],
        }

    def authenticate(self, request, **credentials):
        logger.debug(str(request))
        user = super(my_ElteOpenID, self).authenticate(request, **credentials)
        logger.debug(str(user))
        response = credentials.get('response', {})
        logger.debug("IDP resp %s" % response)
        try:
            logger.debug("Authenticated (username) %s" % user.username)
        except:
            pass
        # currently held courses
        a = response.get('niifEduPersonHeldCourse', {})
        coursecodes = CourseCode.parse(a)
        UserCourseCodeBinding.userattributes(user, coursecodes, is_teacher = True)
        # currently attended courses
        a = response.get('niifEduPersonAttendedCourse', {})
        coursecodes = CourseCode.parse(a)
        UserCourseCodeBinding.userattributes(user, coursecodes, is_teacher = False)
        return user
