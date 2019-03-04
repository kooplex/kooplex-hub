import logging

from django.core.management.base import BaseCommand, CommandError
from hub.models import Image, Volume

from kooplex.lib import Docker


logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Refresh Image and Volume instances'

    def add_arguments(self, parser):
        parser.add_argument('--dry', help = "Dry run: list tasks to be done, and do not actually do anything with them", action = "store_true")
        parser.add_argument('--task', help = "Whether Image or Volume instances to update. All if not specified.", choices = ['image', 'volume'], nargs = 1)
    
    def handle(self, *args, **options):
        logger.info("call %s %s" % (args, options))
        if 'image' in options.get('tasks', ['image']):
            self.handle_images(options['dry'])
        if 'volume' in options.get('tasks', ['volume']):
            self.handle_volumes(options['dry'])

    def handle_images(self, dry):
        # the list of the names of the currently available images as of docker API information
        images = list(Docker().list_imagenames())
        for image in Image.objects.all():
            if image.name in images:
                # it is already in the model, make sure it is available
                images.remove(image.name)
                logger.debug("%s mark as present" % image)
                if not dry:
                    image.present = True
                    image.save()
            else:
                # the image may have been removed from the docker engine, mark it is not present any more
                logger.debug("%s mark as not present" % image)
                if not dry:
                    image.present = False
                    image.save()
        for image_name in images:
            # create image representation for all new images
            logger.debug("new image %s" % image_name)
            if not dry:
                Image.objects.create(name = image_name)

    def handle_volumes(self, dry):
        volumes = list(Docker().list_volumenames())
        logger.debug(volumes)
        for volume in Volume.objects.all():
            logger.debug("%s mark as not present" % volume)
            if not dry:
                volume.is_present = False
                volume.save()
        for volumename in Docker().list_volumenames():
            logger.debug("vol: %s" % volumename)
            try:
                volume = Volume.objects.get(name = volumename)
                logger.debug("%s mark as present" % volume)
                if not dry:
                    volume.is_present = True
                    volume.save()
            except Volume.DoesNotExist:
                logger.debug("try volume %s" % volumename)
                if not dry:
                    volume = Volume.try_create(volumename)
                    if volume:
                        logger.debug("Created volume %s" % volume)

