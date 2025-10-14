
class ExternalAPI:
    def __init__(self, token):
        self.base_url=token.type.base_url
        self.token_value=token.value

    @property
    def headers(self):
        return None

    @property
    def url_check(self):
        return self.base_url

    def check_connection(self):
        """
        Check if the connection to the Canvas API is working
        """
        if h:=self.headers:
            response = requests.get(self.url_check, headers=h)
        else:
            response = requests.get(self.url_check)
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status
