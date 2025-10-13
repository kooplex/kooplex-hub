#test creation
#teest permissions

from django.core.management.base import BaseCommand
from project.models import *
import time
import logging

from test.utils import test_create_project, launch_env, test_get_test_user, test_create_env

logger = logging.getLogger("test")

class Command(BaseCommand):
    help = "Test create and delete a project with a user"

    def handle(self, *args, **options):
        logger.debug(f"TEST: {__name__}")
       
        testuser = test_get_test_user(username="test1")

        try:
            logger.debug("Creating test project")
            p, upb = test_create_project(user=testuser)            

            # Mount project to environment
            from project.models import ProjectContainerBinding
            # Create a test container for the project
            #container = Container(name=f'test-container-{p.name}', user=upb.user, image=image)
            #container.save()
            container = test_create_env(user=testuser)
            logger.debug(f"Container {container.name} created for project {p.name}")
            # Bind the container to the project
            pcb = ProjectContainerBinding(project=p, container=container)
            pcb.save()
            logger.debug(f"ProjectContainerBinding created for project {p.name} and container {container.name}")

            # Launch the environment
            if launch_env(container):
                logger.debug(f"Environment for project {p.name} started successfully")
            else:
                logger.error(f"Failed to start environment for project {p.name}")
            
            p.delete()
            logger.debug(f"Project {p.name} deleted")
        except Exception as e:
            print(e)
        
            
