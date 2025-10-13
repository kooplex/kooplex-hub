#test creation
#teest permissions

from django.core.management.base import BaseCommand
import time, os
import logging

from test.utils import *
logger = logging.getLogger("test")

class Command(BaseCommand):
    help = "Test create and delete a course with a user"

    def handle(self, *args, **options):
        logger.debug(f"TEST: {__name__}")
       
        user = test_get_test_user()

        logger.debug("Creating test course")
        # Create a course
        test_course, ucb = test_create_course(user=user)


        try:
            # Mount course to environment
            from education.models import CourseContainerBinding            

            # Create a test container for the user
            container = test_create_env(user=user)
            logger.debug(f"Container {container.name} created for user {user.username}")
                
            # Bind the container to the course
            ccb = CourseContainerBinding(course=test_course, container=container)
            ccb.save()
            logger.debug(f"CourseContainerBinding created for course {test_course.name} and container {container.name}")
            
            # Launch the environment
            if launch_env(container):
                logger.debug(f"Environment for course {test_course.name} started successfully")
            else:
                logger.error(f"Failed to start environment for course {test_course.name}")
            
            # Check whether pod is running
            while not check_container_running(container):
                logger.debug(f"Container {container.name} is NOT RUNNING yet")
                time.sleep(5)
          


            com = f'ls /v/courses;'
            logger.debug(f"Executing command: {com} -> {exec_command_in_pod(container, com, user)}")

            from education.conf import EDUCATION_SETTINGS
            # assignment_prepare
            folder = EDUCATION_SETTINGS.get('mounts').get('assignment_prepare').get('mountpoint').format(course=test_course)
            com = f"echo Permissions checked > {folder}/permissions.txt;"
            logger.debug(f"Executing command: {com} -> {exec_command_in_pod(container, com, user)}")
            com = f"cat {folder}/permissions.txt;"
            logger.debug(f"Executing command: {com} -> {exec_command_in_pod(container, com, user)}")

            # assignments
            folder = EDUCATION_SETTINGS.get('mounts').get('assignment').get('mountpoint').format(course=test_course, user=user)
            com = f"echo Permissions checked > {folder}/permissions.txt;"
            logger.debug(f"Executing command: {com} -> {exec_command_in_pod(container, com, user)}")
            com = f"cat {folder}/permissions.txt;"
            logger.debug(f"Executing command: {com} -> {exec_command_in_pod(container, com, user)}")

            # public
            folder = EDUCATION_SETTINGS.get('mounts').get('public').get('mountpoint').format(course=test_course)
            com = f"echo Permissions checked; > {folder}/permissions.txt;"
            logger.debug(f"Executing command: {com} -> {exec_command_in_pod(container, com, user)}")
            com = f"cat {folder}/permissions.txt;"
            logger.debug(f"Executing command: {com} -> {exec_command_in_pod(container, com, user)}")

            # correct
            folder = EDUCATION_SETTINGS.get('mounts').get('assignment_correct').get('mountpoint').format(course=test_course, user=user)
            com = f"echo Permissions checked > {folder}/permissions.txt;"
            logger.debug(f"Executing command: {com} -> {exec_command_in_pod(container, com, user)}")
            com = f"cat {folder}/permissions.txt;"
            logger.debug(f"Executing command: {com} -> {exec_command_in_pod(container, com, user)}")

        except Exception as e:
            print(e)
        finally:
            # Delete container manually
            container.delete()
            logger.debug(f"Container {container.name} deleted")
            # Delete course
            test_course.delete()
            logger.debug(f"Course {test_course.name} deleted")        
        logger.debug(f"Test FINISHED: {__name__}")
            
