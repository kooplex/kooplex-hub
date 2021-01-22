import logging
import os

from social_core.backends.open_id_connect import OpenIdConnectAuth

from hub.models import CourseCode, UserCourseCodeBinding
from kooplex.settings import KOOPLEX

logger = logging.getLogger(__name__)


class KooplexOpenID(OpenIdConnectAuth):
    name = 'kooplex'
#    OIDC_ENDPOINT = "https://veo.vo.elte.hu/oauth/accounts/login" #KOOPLEX.get('hydra_oidc_endpoint', 'https://localhost:4444')
    OIDC_ENDPOINT = "https://veo.vo.elte.hu/oauth/o/authorize" #KOOPLEX.get('hydra_oidc_endpoint', 'https://localhost:4444')

    def get_redirect_uri(self, state = None):
        """Build redirect with redirect_state parameter."""
        base_url = KOOPLEX.get('base_url', 'http://localhost')
        url = os.path.join(base_url, "hub/oauth/complete/oidc/")
        logger.debug("IDP resp" )
        if self.REDIRECT_STATE and state:
            uri = url_add_parameters(url, {'redirect_state': state})
        else:
            uri = url
        return uri

    def get_user_details(self, response):
        first_name = response['givenName'][0] if 'givenName' in response else ' '.join(response['displayName'].split()[:-1])
        last_name = response['sn'][0] if 'sn' in response else response['displayName'].split()[-1]
        email = response['mail'][0] if isinstance(response['mail'], list) else response['mail']
        return {
               'username': response['idp_user'],
               'email': email,
               'fullname': response['displayName'][0],
               'first_name': first_name,
               'last_name': last_name,
           }

    def authenticate(self, request, **credentials):
        user = super(OpenIdConnectAuth, self).authenticate(request, **credentials)
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
