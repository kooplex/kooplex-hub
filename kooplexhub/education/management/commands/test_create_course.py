#test creation
#teest permissions

from django.core.management.base import BaseCommand
import time
import logging

from test.utils import test_create_course

logger = logging.getLogger("test")

class Command(BaseCommand):
    help = "Test create and delete a course with a user"

    def handle(self, *args, **options):
        logger.debug(f"TEST: {__name__}")
       
        try:
            logger.debug("Creating test course")
            c, ucb = test_create_course()            
            gs = c.group_students
            gt = c.group_teachers
            logger.debug(f"Deleting test course {c.name} with user {ucb.user.username}, and groups {gs.name}, {gt.name}")
            c.delete()
            gs.delete()
            gt.delete()
            logger.debug(f"Create {c.name} deleted")
        except Exception as e:
            print(e)

        logger.debug(f"TEST FINISHED: {__name__}")
        
            
