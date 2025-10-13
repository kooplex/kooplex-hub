#test creation
#teest permissions

from django.core.management.base import BaseCommand
import time
import logging

from test.utils import test_create_course, \
            launch_env, \
            test_get_test_user, \
            test_create_env

logger = logging.getLogger("test")

class Command(BaseCommand):
    help = "Test create and delete a course with a user"

    def handle(self, *args, **options):
        logger.debug(f"TEST: {__name__}")
       
        testuser = test_get_test_user(username="test1")

        try:
            logger.debug("Creating test course")
            # Create a course
            test_course, ucb = test_create_course(user=testuser)         

            # Mount course to environment
            from education.models import CourseContainerBinding            

            # Create a test container for the user
            container = test_create_env(user=testuser)
            logger.debug(f"Container {container.name} created for user {testuser.username}")
                
            # Bind the container to the course
            ccb = CourseContainerBinding(course=test_course, container=container)
            ccb.save()
            logger.debug(f"CourseContainerBinding created for course {test_course.name} and container {container.name}")
            
            # Launch the environment
            if launch_env(container):
                logger.debug(f"Environment for course {test_course.name} started successfully")
            else:
                logger.error(f"Failed to start environment for course {test_course.name}")
            
            # Delete the course
            test_course.delete()
            logger.debug(f"course {test_course.name} deleted")
            # Delete the container
            container.delete()
            logger.debug(f"Container {container.name} deleted")
        except Exception as e:
            raise e
            print(e)


        logger.debug(f"Test FINISHED: {__name__}")
