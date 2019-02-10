import logging
import os

from social_core.backends.open_id_connect import OpenIdConnectAuth

from hub.models import CourseCode, UserCourseCodeBinding
from kooplex.settings import KOOPLEX

logger = logging.getLogger(__name__)


class HydraOpenID(OpenIdConnectAuth):
    name = 'hydraoidc'
    OIDC_ENDPOINT = KOOPLEX.get('hydra_oidc_endpoint', 'https://localhost:4444')

    def get_redirect_uri(self, state = None):
        """Build redirect with redirect_state parameter."""
        base_url = KOOPLEX.get('base_url', 'http://localhost')
        url = os.path.join(base_url, "hub/oauth/complete/hydraoidc/")
        logger.debug("IDP resp" )
        if self.REDIRECT_STATE and state:
            uri = url_add_parameters(url, {'redirect_state': state})
        else:
            uri = url
        return uri

    def get_user_details(self, response):
        return {#FIXME: a hydra most furan tolja az attributumokat!
            'username': response['idp_user'],
            'email': response['mail'][0],
            'fullname': response['displayName'][0],
            'first_name': response['givenName'][0],
            'last_name': response['sn'][0],
        }

    def authenticate(self, request, **credentials):
        user = super(HydraOpenID, self).authenticate(request, **credentials)
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
