from django.db import models
from kooplex.lib.docker import Docker

class Image(models.Model):
    id = models.AutoField(primary_key = True)
    name = models.CharField(max_length = 32)

    def __str__(self):
        return self.name


def init_model():
    Image.objects.all().delete()
    for image_name in Docker().list_imagenames():
        Image(name = image_name).save()

