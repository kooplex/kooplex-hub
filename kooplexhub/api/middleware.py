from django.utils.deprecation import MiddlewareMixin
from hub.models import Profile

class TokenAuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        try:
            if request.user.is_authenticated:
                return
        except:
            pass
        token = request.COOKIES.get('api_token', None)
        username = request.COOKIES.get('api_user', None)
        try:
            request.user = Profile.objects.get(user__username = username, token = token).user
        except:
            pass

