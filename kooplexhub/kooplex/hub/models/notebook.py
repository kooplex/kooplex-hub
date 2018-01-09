from django.db import models

from .container import Container

class Notebook(Container):
    proxy_path = models.CharField(max_length = 200)

    class Meta:
        db_table = "kooplex_hub_notebook"

    #external_url = models.CharField(max_length = 200) FIXME: let it be a property if really required
