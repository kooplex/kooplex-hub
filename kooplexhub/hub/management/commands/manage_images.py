import logging
  
from django.core.management.base import BaseCommand, CommandError
from container.models import Image, Proxy, EnvVarMapping
from hub.models import Thumbnail

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Manage images'

    def add_arguments(self, parser):
        parser.add_argument('--add_image', help = "Add image", nargs = 2)
        parser.add_argument('--add_imagedescription', help = "Add description to the image", nargs = 3)
        parser.add_argument('--add_proxy', help = "Add Proxy", nargs = 5)
        parser.add_argument('--add_envvar', help = "Add Proxy", nargs = 3)
#        parser.add_argument('--add_type', help = "Add Type", nargs = 3)
        parser.add_argument('--remove', help = "Remove image", nargs = 1)
        parser.add_argument('--remove_proxy', help = "Remove Proxy", nargs = 1)
        parser.add_argument('--remove_envvar', help = "Remove Proxy", nargs = 1)

    def handle(self, *args, **options):
        logger.info("call %s %s" % (args, options))
        add_image = options.get('add_image')
        add_imagedescription = options.get('add_imagedescription')
        add_proxy = options.get('add_proxy')
        add_envvar = options.get('add_envvar')
        remove_image = options.get('remove')
        remove_proxy = options.get('remove_proxy')
        remove_envvar = options.get('remove_envvar')
        if add_image:
            imagetype = add_image.pop() 
            rt = Thumbnail.objects.get(name=imagetype)
            #imagetype=Image.TP_LOOKUP.get(imagetype)
            name = add_image.pop()
            i, s = Image.objects.get_or_create(name=name, thumbnail=rt)
            #i.imagetype=imagetype
            #i.save()
            logger.info('Image %s %s' % (i, 'created' if s else 'exists'))
        if add_imagedescription:
            dockerfile = add_imagedescription.pop() 
            description = add_imagedescription.pop()
            name = add_imagedescription.pop()
            i, s = Image.objects.get_or_create(name=name)
            i.description=description
            i.dockerfile=dockerfile
            i.save()
            logger.info(f"Image {i} {'created' if s else 'exists'}, {i.description}")
        if remove_image:
            try:
                i = Image.objects.get(name = remove_image.pop())
                i.delete()
                logger.info('Removed image %s' % i.name)
            except Image.DoesNotExist:
                pass
        if add_proxy:
            port = add_proxy.pop()
            token_as_argument = add_proxy.pop()
            default = add_proxy.pop()
            image_name = add_proxy.pop()
            image = Image.objects.get(name = image_name)
            name = add_proxy.pop()
            i, s = Proxy.objects.get_or_create(name = name, image = image, default = default, token_as_argument = token_as_argument, port=port)
            logger.info('Proxy %s %s' % (i, 'created' if s else 'exists'))
        if remove_proxy:
            name = remove_proxy.pop()
            i, s = Proxy.objects.filter(name = name).delete()
            logger.info('Proxy %s %s' % (i, 'removed' if s else "didn't exist"))
        if add_envvar:
            valuemap = add_envvar.pop()
            name = add_envvar.pop()
            image_name = add_envvar.pop()
            image = Image.objects.get(name = image_name)
            i, s = EnvVarMapping.objects.get_or_create(name = name, image = image, valuemap = valuemap)
            logger.info('EnvVarMapping %s %s' % (i, 'created' if s else 'exists'))
        if remove_envvar:
            valuemap = add_envvar.pop()
            name = remove_envvar.pop()
            i, s = EnvVarMapping.objects.filter(name = name, valuemap = valuemap).delete()
            logger.info('EnvVarMapping %s %s' % (i, 'removed' if s else "didn't exist"))
