from django.db import models
from kooplex.lib.libbase import get_settings
from .container import Container

class Dashboard_server(Container):
    dashboard_port = models.IntegerField()
    dir_to = models.CharField(max_length=200)
    external_url = models.CharField(max_length=200)
    dashboard_name = models.CharField(max_length=200)
    kernel_gateway_name = models.CharField(max_length=200)

    class Meta:
        db_table = "kooplex_hub_dasboard_server"

    def get_dir_to(self, username, path_with_namespace, extradir):
        dashboards_dir = get_settings('dashboards', 'dir_to', None, '')
        dashboards_dir = dashboards_dir.replace('${image_postfix}', self.image)
        dashboards_dir = dashboards_dir.replace('${username}', username)
        dashboards_dir = dashboards_dir.replace('${path_with_namespace}', path_with_namespace)
        self.dir_to = os.path.join(dashboards_dir, extradir, file)
        return self.dir_to