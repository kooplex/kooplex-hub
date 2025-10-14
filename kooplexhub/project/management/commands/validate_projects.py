from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from ...models import *
import logging

logger = logging.getLogger("test")

class Command(BaseCommand):
    help = "Validate projects"

    def handle(self, *args, **options):
        n_pass=0
        n_fail=0
        for p in Project.objects.all():
            try:
                p.full_clean()
                logger.debug(f"Project {p} passed validation")
                n_pass+=1
            except ValidationError as e:
                msg=f"Project {p} fails validation -- {e}"
                logger.critical(msg)
                print(msg)
                n_fail+=1
        msg=f"Project validation summary: {n_pass} PASSED / {n_fail} FAILED"
        print (msg)
        logger.info(msg)

