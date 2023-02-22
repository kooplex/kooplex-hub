from django.core.management.base import BaseCommand
from education.models import Course

class Command(BaseCommand):
    help = "List courses and corresponding groups"


    def handle(self, *args, **options):
        for c in Course.objects.all():
            print (f'Course {c.name} [ folder: {c.folder}; group: {c.os_group} ]')


