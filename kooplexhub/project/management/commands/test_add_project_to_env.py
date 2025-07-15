#test creation
#teest permissions

from django.core.management.base import BaseCommand
from project.models import *
import time
import logging

from test.utils import test_create_project, run_env_start_stop

logger = logging.getLogger("test")

class Command(BaseCommand):
    help = "Test create and delete a project with a user"

    def handle(self, *args, **options):
        logger.debug(f"TEST: {__name__}")
       
        try:
            logger.debug("Creating test project")
            p, upb = test_create_project()            

            # Mount project to environment
            from container.models import Container
            from project.models import ProjectContainerBinding
            from container.models import Image
            # Get the first available image
            image = Image.objects.filter(present=True).first()
            if not image:
                raise ValueError("No present images found") 
            # Create a test container for the project
            container = Container(name=f'test-container-{p.name}', user=upb.user, image=image)
            container.save()
            logger.debug(f"Container {container.name} created for project {p.name}")
            # Bind the container to the project
            pcb = ProjectContainerBinding(project=p, container=container)
            pcb.save()
            logger.debug(f"ProjectContainerBinding created for project {p.name} and container {container.name}")

            # Launch the environment
            if run_env_start_stop(container):
                logger.debug(f"Environment for project {p.name} started successfully")
            else:
                logger.error(f"Failed to start environment for project {p.name}")
            
            p.delete()
            logger.debug(f"Project {p.name} deleted")
        except Exception as e:
            print(e)
        
            
