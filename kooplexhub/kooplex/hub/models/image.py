from django.db import models

from kooplex.lib import get_settings

class Image(models.Model):
    id = models.AutoField(primary_key = True)
    name = models.CharField(max_length = 32)
    present = models.BooleanField(default = True)

    def __str__(self):
        return self.name

    @property
    def imagename(self):
        return get_settings('docker', 'pattern_imagename') % { 'imagename': self.name }

def init_model():
    from kooplex.lib import Docker
    # the list of the names of the currently available images as of docker API information
    images = list(Docker().list_imagenames())
    for image in Image.objects.all():
        if image.name in images:
            # it is already in the model, make sure it is available
            images.remove(image.name)
            image.present = True
            image.save()
        else:
            # the image may have been removed from the docker engine, mark it is not present any more
            image.present = False
            image.save()
    for image_name in images:
        # create image representation for all new images
        Image(name = image_name).save()

