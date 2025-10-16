import logging
logger = logging.getLogger("test")

from kooplexhub.settings import KOOPLEX


def test_get_test_user(username="wfct0p"):
    """Get a test user by username, defaulting to 'wfct0p'."""
    from hub.models import User
    # FIXME will need a testuser here
    if not username:
        # Pick a random existing user
        u = User.objects.order_by('?').first()
        if not u:
            raise ValueError("No users found to select as test user")
        return u
    else:
        return User.objects.get(username=username)
        

def test_create_env(user=None, image=None):
    """Create a test environment (container) with a given user and image."""
    from container.models import Container
    if not user:
        user = test_get_test_user()
    if not image:
        from container.models import Image
        # Get all present/enabled images 
        image = Image.objects.filter(present=True, imagetype=Image.TP_PROJECT).first()
        if not image:
            raise ValueError("No present images found")
    cname = "test-"+user.username+"-"+image.name.split("/")[1]
    new_c, exists = Container.objects.get_or_create(name=cname, user = user, image=image)
    if exists:
        logger.debug(f"Container {new_c.name} already exists for user {user.username}")
    else:
        logger.debug(f"Created new container {new_c.name} for user {user.username}")
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
 
        upb = UserProjectBinding(project=project, user=user, role=UserProjectBinding.Role.CREATOR)
        logger.debug(f"Creating UserProjectBinding for {user.username} in project {project.name}")
        project.save()
        upb.save()
        return project, upb
    except Exception as e:
        print(e)    

def test_create_attachment(folder_name=None, user=None, description=None):
    """Create a test attachment with a name, and description.
    In the context of this code, an attachment is a volume that can be bound to a user.
    The code cannot be more generic as only to this type of volume can storage space be assigned.
    #FIXME: this should be more generic, e.g. creating a persisntent volume or claim also"""
    from volume.models import Volume, UserVolumeBinding
   
    if not folder_name:
        logging.warning("No attachment name provided, creating a default attachment")
        folder_name = "Test Attachment"
    if not user:
        logging.warning("No user provided, retrieving the test user")
        user = test_get_test_user()
    if not description:
        description = "This is a test attachment"
    subpath = "test_attachment"

    # Create an attachment
    try:
        # a, created = Attachment.objects.get_or_create(name=folder_name, description=description, subpath=subpath)
        claim_attachment = KOOPLEX.get('userdata', {}).get('claim-attachment', 'attachments')
        attachment, exists = Volume.objects.get_or_create(folder=folder_name, description=description, claim=claim_attachment, scope= Volume.Scope.ATTACHMENT, subpath=subpath)
        if exists:
            logger.debug(f"Attachment {attachment.folder} already exists for user {user.username}")
        else:
            logger.debug(f"Created new attachment {attachment.folder} for user {user.username}")
            attachment.save()
        
        uab, exists = UserVolumeBinding.objects.get_or_create(volume=attachment, user=user, role=UserVolumeBinding.Role.OWNER)
        if exists:
            logger.debug(f"UserAttachmentBinding for {user.username} in attachment {attachment.folder} already exists")
        else:
            logger.debug(f"Created new UserAttachmentBinding for {user.username} in attachment {attachment.folder}")
            uab.save()
            
        return attachment, uab
    except Exception as e:
        raise e
        print(e)

def check_container_running(container):
    """Check if a container is running."""
    # FIXME maybe this should be more sophisticated, e.g. checking the container state
    pod_state, label, ns = get_container_state(container)
    if pod_state:
        # if pod_state.status.phase != "Running" or pod_state.status.container_statuses[0].last_state.terminated or pod_state.status.container_statuses[0].state.waiting:
        if pod_state.status.phase == "Running" and pod_state.status.container_statuses[0].state.running:
            logger.debug(f"Container {container.name} is {pod_state.status.phase}")
            return True
        else:        
            logger.debug(f"Container {container.name} is not running ({pod_state.status.phase})")
            return False
    return False

def check_container_error(container):
    """Check if a container is in an error state."""
    pod_state, label, ns = get_container_state(container)
    if pod_state:
        if pod_state.status.container_statuses[0].last_state.terminated:
            logger.debug(f"Container {container.name} is in error state: {pod_state.status.container_statuses[0].last_state.terminated}")
            return True
        else:        
            logger.debug(f"Container {container.name} is running")
            return False
    return False
    
def get_container_state(container):
    """Get the current state of a container through the kubernetes API."""
    from kubernetes.client import CoreV1Api
    v1 = CoreV1Api()
    namespace = KOOPLEX['environmental_variables']['POD_NAMESPACE']
    try:
        pod = v1.list_namespaced_pod( namespace=namespace,
        label_selector=f"lbl=lbl-{container.label}").items[0]
    except Exception as e:
        return None, None, None
    logger.debug(f"Getting state for container {container.label}")
    return pod, container.label, namespace

# FIXME: this should be part of the container model
def check_container_liveness(container):
    """Check if a container is alive using its liveness probe."""
    
    logger.debug(f"Checking {KOOPLEX['environmental_variables']['POD_NAMESPACE']}, lbl=lbl-{container.label}")
    pod_state, label, ns = get_container_state(container)

    if pod_state.status.container_statuses[0].last_state.terminated is not None:
        logger.debug(f"Liveness probe for container {container.name} failed due to: {pod_state.status.container_statuses[0].last_state.terminated}")
        return False
    elif pod_state.status.container_statuses[0].state.waiting is not None:
        logger.debug(f"Container {container.name} is still waiting: {pod_state.status.container_statuses[0].state.waiting}")
        return False
    elif pod_state.status.container_statuses[0].state.running is not None:
        logger.debug(f"Liveness probe for container {container.name} succeeded")
        return True
    else:
        logger.debug(f"Liveness probe for container {container.name} failed due to unknown state")
        return False
    

def launch_env(container, stop_after_start=True, exec_command=None):
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
        
    else:
        logger.warning(f"Container {container.name} did not start properly")
        return False
    
    if stop_after_start:
        container.stop()
        logger.debug(f"Container {container.name} stopped")

    return True

def kube_api():
    """Load the kube config and return the CoreV1Api client."""
    from kubernetes import client, config
    config.load_kube_config()
    v1 = client.CoreV1Api()
    return v1

def exec_command_in_pod(container, command, user=None):
    pod, container_label, namespace = get_container_state(container)
    # print(pod)
    k_api = kube_api()
    from kubernetes.stream import stream
    if user:
        command = f"su {user.username} -c '{command}'"
    
    exec_command = ["/bin/sh", "-c", command]
    
    resp = stream(k_api.connect_get_namespaced_pod_exec,
                    pod.metadata.name,
                    namespace,
                    command=exec_command,
                    container=container_label,
                    stderr=True, stdin=False,
                    stdout=True, tty=False)
    return resp

def test_create_course(cname=None, user=None, description=None):
    """Create a test course with a name, and description."""
    from education.models import Course, UserCourseBinding
    
    if not cname:
        logging.warning("No course name provided, creating a default course")
        cname = "Test Course"
    if not user:
        logging.warning("No user provided, retrieving the test user")
        user = test_get_test_user()
    if not description:
        description = "This is a test course"
    folder = "testcourse"

    # Create a course
    try:
        # course = Course(name=cname, description=description, folder=folder)
        course, exists = Course.objects.get_or_create(name=cname, description=description, folder=folder)

                        #group_teachers=teacher_group, group_students=student_group)
        
        logger.debug(f"Creating course {course.name} for user {user.username}")
        
        ucb = UserCourseBinding(course=course, user=user, is_teacher=True)
        logger.debug(f"Creating UserCourseBinding for {user.username} in course {course.name}")
        
        course.save()
        ucb.save()
        
        return course, ucb
    except Exception as e:
        print(f"{__name__}: {e}")

class Test_Course():
    

    """Create a test course with a name, and description."""
    def __init__(self, course_name=None, user=None, description=None):
        self.course = None
        self.ucb = None
        self.assignment = None
        from education.models import Course, UserCourseBinding
    
        if not course_name:
            logging.warning("No course name provided, creating a default course")
            course_name = "Test Course"
        if not user:
            logging.warning("No user provided, retrieving the test user")
            user = test_get_test_user()
        if not description:
            description = "This is a test course"
        folder = "testcourse"

        # Create a course
        try:
            self.course, exists = Course.objects.get_or_create(name=course_name, description=description, folder=folder)
                            #group_teachers=teacher_group, group_students=student_group)
            
            logger.debug(f"Creating course {self.course.name} for user {user.username}")
            
            self.ucb, exists = UserCourseBinding.objects.get_or_create(course=self.course, user=user, is_teacher=True)
            logger.debug(f"Creating UserCourseBinding for {user.username} in course {self.course.name}")
            
            self.course.save()
            self.ucb.save()
        
        except Exception as e:
            print(e)

    class Test_Assignment():
        def __init__(self, course, name="Test Handout"):
            """Create a test handout for a course."""
            if not course:
                raise ValueError("No course provided")
            from education.models import Assignment
            self.assignment, exists = Assignment.objects.get_or_create(course=course, name=name
            , folder="handout", description="This is a test handout", creator=course.teachers[0])
            self.assignment.save()
            #assignment.handout()
            logger.debug(f"Created handout {self.assignment.name} for course {course.name}")
             

    def create_assignment(self, name="Test Handout"):
        """Create a test assignment for the course."""
        if not self.course:
            raise ValueError("No course available")
        ta = self.Test_Assignment(self.course)
        self.assignment = ta.assignment

    def add_student(self, name="Test Handout"):
        """Add student to the course's assignment."""
        if not self.assignment:
            raise ValueError("No assignment available")
        from education.models import UserAssignmentBinding
        uab, exists = UserAssignmentBinding.objects.get_or_create(assignment=self.assignment, 
            user=test_get_test_user(username="test2"))
        if not exists:
            logger.debug(f"Added student {uab.user.username} to course {self.assignment.name}")
            uab.save()
        return uab
        
