from django.db import models

class Fileform(models.Model):
    docfile = models.FileField(upload_to=' ')