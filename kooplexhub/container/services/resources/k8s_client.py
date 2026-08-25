import os

from kubernetes import client, config


def get_kubernetes_api_client() -> client.ApiClient:
    """
    Preferred:
      use in-cluster service account.

    Temporary fallback:
      use KOOPLEX_K8S_API_HOST and KOOPLEX_K8S_BEARER_TOKEN.
    """

    bearer_token = os.environ.get("KOOPLEX_K8S_BEARER_TOKEN")
    bearer_token="""eyJhbGciOiJSUzI1NiIsImtpZCI6ImV6STFaM1VSSkdpaXJWT3pOVnM1aDA0dDYzRC1aNTNDRjJPOHFkTngybTQifQ.eyJhdWQiOlsiaHR0cHM6Ly9rdWJlcm5ldGVzLmRlZmF1bHQuc3ZjLmNsdXN0ZXIubG9jYWwiLCJrM3MiXSwiZXhwIjoxNzgwNjY1MTI3LCJpYXQiOjE3ODA2NjE1MjcsImlzcyI6Imh0dHBzOi8va3ViZXJuZXRlcy5kZWZhdWx0LnN2Yy5jbHVzdGVyLmxvY2FsIiwianRpIjoiZjQ4MTlkYzAtZThkOS00MzY5LWEyNzYtNmFkZTdhYmI3YTA0Iiwia3ViZXJuZXRlcy5pbyI6eyJuYW1lc3BhY2UiOiJrb29wbGV4Iiwic2VydmljZWFjY291bnQiOnsibmFtZSI6Imtvb3BsZXgtbm9kZS1tZXRyaWMtc2EiLCJ1aWQiOiJmMzAyYjg5Mi1iN2ZlLTQ1MmYtYjk5Yy1jODdhMzJmNzY4MDYifX0sIm5iZiI6MTc4MDY2MTUyNywic3ViIjoic3lzdGVtOnNlcnZpY2VhY2NvdW50Omtvb3BsZXg6a29vcGxleC1ub2RlLW1ldHJpYy1zYSJ9.atVjJoTqe76nCoaAwltqWYidysS_UMAMOy8M8Dwtcb5TdutR-8_cJ7cibrDf3IbawrMNCEkJYgAb1tHPO8B5WpJrNEfPf7UYfSA3QcDD8lz46QzgUU_CPsh0Icce-RsIX1qU0U0XDBZ332g4VqbkHWAHAB5ZmaVAemGwbn2n41guaB2AQltRSw37P6H2c0nHPOx-qgtthOvG01dwlm3Q5OXzfd2hYhPsqEBscXhxpJLEjDlcz158x6ykHAZ8xbcPHv0vGYJ7PWQkOXq36m1sELJZuslpNRlQka5vWYgdavVbLGY6EybeaNT982cIXsCI2h7udYUzsA--KXHzN6wrWg"""
    api_host = os.environ.get("KOOPLEX_K8S_API_HOST")
    api_host = "https://10.96.0.1:443"

    if bearer_token and api_host:
        configuration = client.Configuration()
        configuration.host = api_host
        configuration.verify_ssl = True
        configuration.ssl_ca_cert = os.environ.get(
            "KOOPLEX_K8S_CA_CERT",
            "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt",
        )
        configuration.api_key = {
            "authorization": "Bearer " + bearer_token.strip()
        }
        print(1)
        return client.ApiClient(configuration)

    try:
        config.load_incluster_config()
        print(2)
    except config.ConfigException:
        config.load_kube_config()
        print(3)

    return client.ApiClient()
