import json
from django.db import models

from .modelbase import ModelBase
from .container import Container
from .notebook import Notebook

class Session(models.Model, ModelBase):
    id = models.UUIDField(primary_key=True)
    notebook = models.ForeignKey(Notebook, on_delete=models.CASCADE)
    notebook_path = models.CharField(max_length=200)
    kernel_id = models.UUIDField()
    kernel_name = models.CharField(max_length=15)
    external_url = models.CharField(max_length=200)
    
    def from_jupyter_dict(notebook, dict):
        s = Session()
        s.id = ModelBase.get_from_dict(dict, 'id')
        s.notebook_id = notebook.id
        s.notebook_path = ModelBase.get_from_dict(dict, ['notebook', 'path'])
        s.kernel_id = ModelBase.get_from_dict(dict, ['kernel', 'id'])
        s.kernel_name = ModelBase.get_from_dict(dict, ['kernel', 'name'])
        return s

    def to_jupyter_dict(self):
        data = {
            'notebook': { 'path': self.notebook_path },
            'kernel': { 'name': self.kernel_name }
        }
        return data



