import logging
import json
import threading
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string

from channels.generic.websocket import WebsocketConsumer

from django.contrib.auth.models import User
from project.models import Project, UserProjectBinding, ProjectContainerBinding
from volume.models import Volume, ProjectVolumeBinding
from container.models import Image

logger = logging.getLogger(__name__)

#################
from django.core.exceptions import FieldDoesNotExist
from django.db.models.query import QuerySet
# FIXME put somewhere common 

def model_field(instance, attr_name):
    # Get the class of the instance
    cls = instance.__class__
    # Check if the attribute is a Django model field
    try:
        instance._meta.get_field(attr_name)
        return True
    except FieldDoesNotExist:
        pass
    return False


class SyncConsumer(WebsocketConsumer):
    def connect(self):
        if not self.scope['user'].is_authenticated:
            return
        self.accept()
        self.userid = int(self.scope["url_route"]["kwargs"].get('userid'))
        assert self.scope['user'].id == self.userid, "not authorized"

    def disconnect(self, close_code):
        pass

class ProjectConfigConsumer(SyncConsumer):
    def receive(self, text_data):
        from kooplexhub.lib.libbase import standardize_str
        parsed = json.loads(text_data)
        logger.debug(parsed)
        assert parsed.get('request')=='configure-project', "wrong request"
        failed={}
        success=False
        pk = parsed.get('pk')
        changes = parsed.get('changes')
        if pk == "None":
            name=changes['name']
            subpath=standardize_str(name)
            s={'scope': changes['scope']} if 'scope' in changes else {}
            project=Project(name=name, subpath=subpath, preferred_image_id=changes['image'], description=changes['description'], **s)
            #FIXME: validate
            project.save()
            UserProjectBinding(user_id = self.userid, project = project, role = UserProjectBinding.RL_CREATOR).save()
            reloadpage=True
        else:
            reloadpage=False
            pid = int(pk)
            project = UserProjectBinding.objects.get(user__id = self.userid, project__id = pid, role__in = [UserProjectBinding.RL_CREATOR, UserProjectBinding.RL_ADMIN]).project
        # Iterate over the changes and try to update the model instance
        for field, new_value in changes.items():
            if field == 'image':
                new_value=Image.objects.get(id=new_value)
                field='preferred_image'
            # Check if the field is a valid attribute of the model
            if model_field(project, field):
                old_value = getattr(project, field)
                try:
                    # Try assigning the new value to the model's field
                    setattr(project, field, new_value)
                    # Run Django's model validation for the field
                    project.full_clean(validate_unique=True, exclude=[f for f in changes.keys() if f != field])
                    # If no exception was raised, add it to the success response
                    success=True
                except ValidationError as e:
                    # Validation failed, record the error message
                    failed[field] = { "error": str(e), "value": old_value }
            elif field == 'users':
                for user in User.objects.filter(id__in = new_value):
                    upb, _ = UserProjectBinding.objects.get_or_create(project = project, user = user)
                    if upb.role != UserProjectBinding.RL_CREATOR:
                        upb.role = UserProjectBinding.RL_ADMIN if user.id in changes.get('marked') else UserProjectBinding.RL_COLLABORATOR
                        upb.save()
                UserProjectBinding.objects.filter(project = project).exclude(user__id__in = new_value).exclude(role = UserProjectBinding.RL_CREATOR).delete()
                success=True
            elif field == 'volumes':
                for volume in Volume.objects.filter(id__in = new_value):
                    ProjectVolumeBinding.objects.get_or_create(volume = volume, project = project)
                ProjectVolumeBinding.objects.filter(project = project).exclude(volume__id__in = new_value).delete()
                success=True
            else:
                # Attribute does not exist on the model
                logger.error(f"Project model attribute {field} does not exist.")
        # Save the instance if there are any successful changes
        if success:
            project.save()
        message_back = {
            "feedback": f"Project {project.name} is configured",
            "response": "reloadpage" if reloadpage else render_to_string("project.html", {'project':project}),
            "project_id": project.id,
        }
        logger.debug(message_back["feedback"])
        self.send(text_data=json.dumps(message_back))


class ProjectGetContainersConsumer(SyncConsumer):
    def receive(self, text_data):
        from django.urls import reverse
        parsed = json.loads(text_data)
        logger.debug(parsed)
        #assert parsed.get('request')=='configure-project', "wrong request"
        if parsed.get('request')=='autoadd':
            userprojectbinding_id=parsed.get('pk')
            message, projectid=self.addcontainer(userprojectbinding_id)
        else:
            message=None
            projectid = parsed.get('pk')
        bindings=ProjectContainerBinding.objects.filter(container__user__id=self.userid, project__id=projectid)
        upb=UserProjectBinding.objects.get(user__id=self.userid, project__id=projectid)
        message_back = {
            "feedback": f"Container list refreshed",
            "response": render_to_string("widgets/widget_containertable.html", {"containers": list(map(lambda o: o.container, bindings)), "pk": upb.id }),
        }
        logger.debug(message_back)
        self.send(text_data=json.dumps(message_back))

    def addcontainer(self, userprojectbinding_id):
        """
        @summary: automagically create an environment
        @param userprojectbinding_id
        """
        from kooplexhub.lib.libbase import standardize_str
        from volume.models import ProjectVolumeBinding
        from volume.models import VolumeContainerBinding
        from container.models import Container
        try:
            upb = UserProjectBinding.objects.get(id = userprojectbinding_id, user_id = self.userid)
            project = upb.project
            user = upb.user
            container, created = Container.objects.get_or_create(
                name = f'generated for {project.name}', 
                label = f'p-{user.username}-{standardize_str(project.name)}-{project.creator.username}',
                user = user,
                image = project.preferred_image
            )
            ProjectContainerBinding.objects.create(project = project, container = container)
            for b in ProjectVolumeBinding.objects.filter(project=project):
                VolumeContainerBinding.objects.get_or_create(container=container, volume=b.volume)
            if created:
                return f'We created a new environment {container.name} for project {project.name}.', project.id
            else:
                return f'We associated your project {project.name} with your former environment {container.name}.', project.id
        except Exception as e:
            return f'We failed -- {e}', project.id


class ProjectGetJoinableConsumer(SyncConsumer):
    def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        published = list(map(lambda b: b.project, UserProjectBinding.objects.filter(project__scope__in = [ Project.SCP_INTERNAL, Project.SCP_PUBLIC ], role = UserProjectBinding.RL_CREATOR).exclude(user__id = self.userid)))
        logger.debug(published)
        joined = list(map(lambda b: b.project, UserProjectBinding.objects.filter(user__id = self.userid, role__in = [ UserProjectBinding.RL_ADMIN, UserProjectBinding.RL_COLLABORATOR ])))
        logger.debug(joined)
        joinable = set(published).difference(joined)
        logger.debug(joinable)
        message_back = {
            "feedback": f"Joinable project list refreshed",
            "response": render_to_string('widgets/list_joinableprojects.html', {'projects': joinable})
        }
        logger.debug(message_back)
        self.send(text_data=json.dumps(message_back))


class JoinProjectConsumer(SyncConsumer):
    def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        projectid = parsed.get('pk')
        published = UserProjectBinding.objects.filter(project__scope__in = [ Project.SCP_INTERNAL, Project.SCP_PUBLIC ], role = UserProjectBinding.RL_CREATOR, project__id=projectid).exclude(user__id = self.userid)
        joined = UserProjectBinding.objects.filter(user__id = self.userid, project__id = projectid)
        deny = not published or joined 
        if not deny:
            b=UserProjectBinding.objects.create(project_id=projectid, user_id=self.userid, role=UserProjectBinding.RL_COLLABORATOR)
        message_back = {
            "feedback": f"Cannot join project" if deny else f"Project {b.project.name} joined",
            "reloadpage": True,
        }
        logger.debug(message_back)
        self.send(text_data=json.dumps(message_back))
