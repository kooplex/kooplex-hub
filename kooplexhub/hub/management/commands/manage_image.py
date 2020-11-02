import logging

from django.core.management.base import BaseCommand, CommandError
from hub.models import Image

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Manage images'

    def add_arguments(self, parser):
        parser.add_argument('--add', help = "Add image", nargs = 1)
        parser.add_argument('--remove', help = "Remove image", nargs = 1)
    
    def handle(self, *args, **options):
        logger.info("call %s %s" % (args, options))
        add_image = options.get('add')
        remove_image = options.get('remove')
        if add_image:
            i, s = Image.objects.get_or_create(name = add_image.pop())
            logger.info('Image %s %s' % (i, 'created' if s else 'exists'))
        if remove_image:
            try:
                i = Image.objects.get(name = remove_image.pop())
                i.delete()
                logger.info('Removed image %s' % i.name)
            except Image.DoesNotExist:
                pass


