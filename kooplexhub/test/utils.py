import logging
logger = logging.getLogger("test")

def test_get_test_user(username="wfct0p"):
    """Get a test user by username, defaulting to 'wfct0p'."""
    from hub.models import User
    # FIXME will need a testuser here
    if not username:
        username = "wfct0p"
    u = User.objects.get(username=username)
    return u

def test_create_env(user=None, image=None):
    """Create a test environment (container) with a given user and image."""
    from container.models import Container
    if not user:
        user = test_get_test_user()
    if not image:
        from container.models import Image
        # Get all present/enabled images 
        image = Image.objects.filter(present=True).first()
        if not image:
            raise ValueError("No present images found")
    cname = "test-"+user.username+"-"+image.name.split("/")[1]
    new_c = Container(name=cname, user = user, image=image)
    new_c.save()
    return new_c

def test_create_project(pname=None, user=None, description=None):
    """Create a test project with a name, and description."""
    from project.models import Project, UserProjectBinding
   
    if not pname:
        logging.warning("No project provided, creating a default project")
        pname="Deaths in London"
    if not user:
        logging.warning("No user provided, retrieving the test user")
        user = test_get_test_user()
    if not description:
        description="Once there were many, seemingly correlated deaths in London"
    subpath="deathsinlondon"

    ## Create a project
    try:
        #p, created = Project.objects.get_or_create(name=pname, description=description, subpath=subpath)
        project = Project(name=pname, description=description, subpath=subpath)
        logger.debug(f"Creating project {project.name} for user {user.username}")
 
        upb = UserProjectBinding(project=project, user=user, role=UserProjectBinding.RL_CREATOR)
        logger.debug(f"Creating UserProjectBinding for {user.username} in project {project.name}")
        project.save()
        upb.save()
        return project, upb
    except Exception as e:
        print(e)    

def check_container_running(container):
    """Check if a container is running."""
    # FIXME maybe this should be more sophisticated, e.g. checking the container state
    if len(container.retrieve_log()):
        logger.debug(f"Container {container.name} is running")
        return True
    else:        
        logger.debug(f"Container {container.name} is not running")
        return False
    
def run_env_start_stop(container):
    """Start and stop a container environment."""
    if not container:
        raise ValueError("No container provided")
    logger.debug(f"Starting container {container.name}")
    container.start()
    logger.debug(f"Container {container.name} started")
    
    # Wait for the container to start
    import time
    time.sleep(2)
    
    if check_container_running(container):
        logger.debug(f"Container {container.name}  is running")
        logger.debug(f"Stopping container {container.name}")
        container.stop()
        logger.debug(f"Container {container.name} stopped")
    else:
        logger.warning(f"Container {container.name} did not start properly")
        return False
    
    return True