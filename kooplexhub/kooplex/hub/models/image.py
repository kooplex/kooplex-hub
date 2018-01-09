from django.db import models


class Image(models.Model):
    id = models.AutoField(primary_key = True)
    name = models.CharField(max_length = 32)


def init_model():
#TODO: a docker API
    pass
