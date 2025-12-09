# NOTE: migration steps
# manage.py makemigrations
# find generated migration script and
#    add these mappings
#    add mapping instructions
# manage.py migrate
#
# These are the mappings
########################
# def convert_textchoices_to_integerchoices(apps, schema_editor):
#     MyModel = apps.get_model("container", "image")
# 
#     mapping = {
#         "projectimage": 10,
#         "jobimage": 20,
#         "reportimage": 30,
#         "appimage": 40,
#         "apiimage": 50,
#     }
# 
#     for text, integer in mapping.items():
#         MyModel.objects.filter(imagetype=text).update(imagetype=integer)
# 
# def reverse_convert(apps, schema_editor):
#     MyModel = apps.get_model("container", "image")
# 
#     reverse_map = {
#             10: "projectimage",
#             20: "jobimage",
#             30: "reportimage",
#             40: "appimage",
#             50: "apiimage",
#     }
# 
#     for integer, text in reverse_map.items():
#         MyModel.objects.filter(imagetype=integer).update(imagetype=text)
#
# This is the mapping instriction
#################################
#    operations = [
#        migrations.AlterModelOptions(
#            name='image',
#            options={'ordering': ['imagetype', 'name']},
#        ),
#        migrations.RunPython(convert_textchoices_to_integerchoices,
#                             reverse_convert),
#        migrations.AlterField(
#            model_name='image',
#            name='imagetype',
#            field=models.IntegerField(choices=[(10, 'project image'), (20, 'job image'), (30, 'report image'), (40, 'app image'), (50, 'api image')], default=10),
#        ),
#    ]
#
####
from django.db import models

from hub.models import Thumbnail
from kubernetes.client import V1Probe, V1HTTPGetAction


class Image(models.Model):
    class ImageType(models.IntegerChoices):
        PROJECT = 10, 'project image'
        JOB = 20, 'job image'
        REPORT = 30, 'report image'
        APP = 40, 'app image'
        API = 50, 'api image'

    name = models.CharField(max_length = 64, unique = True)
    present = models.BooleanField(default = True)
    imagetype = models.IntegerField(choices = ImageType.choices, default = ImageType.PROJECT)
    description = models.CharField(max_length = 250, default = "description missing")
    dockerfile = models.TextField(max_length = 4096)
    command = models.CharField(max_length = 250, default = "/entrypoint.sh")
    thumbnail = models.ForeignKey(Thumbnail, on_delete = models.CASCADE, default = None, null = True)
    liveness_probe = models.ForeignKey('Liveness_Probe', on_delete = models.SET_NULL, null = True, blank = True, default = None)

    class Meta:
        ordering = ['imagetype', 'name']

    def __str__(self):
        return self.name

    @property
    def hr(self):
        return self.name.split('/')[-1]

    @property
    def require_home(self):
        return self.imagetype == self.ImageType.PROJECT

    @property
    def mount_project(self):
        return self.imagetype == self.ImageType.PROJECT

    @property
    def mount_report(self):
        return True


# Implement a default liveness probe and model for images
class Liveness_Probe(models.Model):
    # ... existing fields ...
    class Probe_Methods(models.TextChoices):
        HTTP_GET = 'httpGet', 'HTTP GET'
        TCP_SOCKET = 'tcpSocket', 'TCP Socket'
        EXEC = 'exec', 'Exec'

    name = models.CharField(max_length = 64, unique = True)
    method = models.CharField(max_length = 32, choices = Probe_Methods.choices, default = Probe_Methods.HTTP_GET)
    path = models.CharField(max_length = 256, null = True, blank = True, default = 'notebook/{container.label}')
    port = models.PositiveIntegerField(null = True, blank = True, default = 8000)
    initial_delay_seconds = models.PositiveIntegerField(default = 120)
    period_seconds = models.PositiveIntegerField(default = 120)
    timeout_seconds = models.PositiveIntegerField(default = 5)
    success_threshold = models.PositiveIntegerField(default = 1)
    failure_threshold = models.PositiveIntegerField(default = 3)

    def __str__(self):
        return self.name    

    def as_api_object(self):
        # v1 = CoreV1Api()
        obj = V1Probe(
            http_get=V1HTTPGetAction(
                path=self.path,
                port=self.port,
            ),
            initial_delay_seconds=self.initial_delay_seconds,
            period_seconds=self.period_seconds,
            timeout_seconds=self.timeout_seconds,
            success_threshold=self.success_threshold,
            failure_threshold=self.failure_threshold
        )
        return obj
