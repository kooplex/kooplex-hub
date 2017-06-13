from django.db import models

from .container import Container

class Notebook(Container):
    username = models.CharField(max_length=200)
    port = models.IntegerField()
    proxy_path = models.CharField(max_length=200)
    external_url = models.CharField(max_length=200)
    project_id = models.IntegerField(null=True)


    class Meta:
        db_table = "kooplex_hub_notebook"