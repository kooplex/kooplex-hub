import logging
import json
import threading
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.core.exceptions import ValidationError

from channels.generic.websocket import WebsocketConsumer

from hub.util import normalize_pk
from django.contrib.auth.models import User
from project.models import Project, UserProjectBinding, ProjectContainerBinding
from volume.models import Volume, ProjectVolumeBinding
from container.models import Image

from project.tables import TableCollaborators
logger = logging.getLogger(__name__)

#################
from django.core.exceptions import FieldDoesNotExist
from django.db.models.query import QuerySet
# FIXME put somewhere common 



class SyncConsumer(WebsocketConsumer):
    def connect(self):
        if not self.scope['user'].is_authenticated:
            return
        self.accept()
        self.userid = int(self.scope["url_route"]["kwargs"].get('userid'))
        assert self.scope['user'].id == self.userid, "not authorized"

    def disconnect(self, close_code):
        pass

class UserHandler(SyncConsumer):
    def get_course(self, course_id):
        #FIXME: code repetition!
        c=Course.objects.get(id = course_id)
        assert self.userid in map(lambda o:o.id, c.teachers), "You are not a teacher to config"
        return c

    def _chg_user_bindings(self, project, ids, marked):
        c=[]
        a=[]
        r=[]
        m=""
        for user in User.objects.filter(id__in = ids):
            upb, created = UserProjectBinding.objects.get_or_create(project = project, user = user)
            if created:
                a.append(str(user))
            if upb.role != UserProjectBinding.Role.CREATOR:
                upb.role = UserProjectBinding.Role.ADMIN if user.id in marked else UserProjectBinding.Role.COLLABORATOR
                upb.save()
                if not created:
                    c.append(str(user))
        for upb in UserProjectBinding.objects.filter(project = project).exclude(user__id__in = ids).exclude(role = UserProjectBinding.Role.CREATOR):
            upb.delete()
            r.append(str(upb.user))
        if a:
            m += "added " + ", ".join(a) + "\n"
        if r:
            m += "removed " + ", ".join(r) + "\n"
        if c:
            m += "role changed " + ", ".join(c) + "\n"
        return m

    def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        request = parsed.get('request')
        project_id = normalize_pk(parsed.get('pk'))
        try:
            project = UserProjectBinding.objects.get(user__id = self.userid, project__id = project_id, role__in = [UserProjectBinding.Role.CREATOR, UserProjectBinding.Role.ADMIN]).project
        except UserProjectBinding.DoesNotExist:
            project = None
        response = {
            'response': request,
            'request_id': parsed.get('request_id'),
            'pk': project_id,
        }
        if request=='parse-users-from-file':
            usernames = parsed.get('content').splitlines()
            users = User.objects.filter(username__in = usernames)
            response['ids'] = list(map(lambda u: u.id, users))
            logger.debug(response)
            self.send(text_data=json.dumps(response))
        elif request=='get-users':
            _uid = lambda b: b.user.id
            response['ids'] = list(map(_uid, UserProjectBinding.objects.filter(project=project).exclude(user__id=self.userid)))
            response['marked_ids'] = list(map(_uid, UserProjectBinding.objects.filter(project=project, role__in = [UserProjectBinding.Role.CREATOR, UserProjectBinding.Role.ADMIN]).exclude(user__id=self.userid)))
            logger.debug(response)
            self.send(text_data=json.dumps(response))
        elif request=='save-users':
            message = self._chg_user_bindings(project, parsed.get('ids'), parsed.get('marked_ids', []))
            if message:
                collaborators = project.collaborators_excluding(User.objects.get(pk=self.userid))
                t_collaborators = TableCollaborators(collaborators)
                response['feedback'] = message
                response['refresh'] = render_to_string('widgets/table_users.html', {'pk': project_id, 'table': t_collaborators})
                self.send(text_data=json.dumps(response))
        else:
            logger.critical(request)


class ProjectConfigHandler:
    def __init__(self, instance, user):
        self.instance = instance
        self.user = user
        self.attribute_handlers = {
            'name': (False, self.handle_name_update),
            'description': (False, self.handle_description_update),
            'preferred_image': (False, self.handle_image_update),
            'scope': (False, self.handle_scope_update),
            'volumes': (True, self.handle_mounts_update),
        }

    def handle_attribute(self, attribute_name, new_value):
        pass_attribute, handler = self.attribute_handlers.get(attribute_name)
        if handler and pass_attribute:
            return handler(attribute_name, new_value)
        elif handler:
            return handler(new_value)
        else:
            logger.critical(f"No handler for container configuration attribute: {attribute_name}")

    def handle_name_update(self, new_value):
        from .templatetags.project_tags import render_name
        old_value = self.instance.name
        self.instance.name = new_value
        try:
            self.instance.full_clean()
            self.instance.save()
            return f"name changed from {old_value} to {new_value}", {f"[data-name=name][data-pk={self.instance.pk}][data-model=project]": render_name(self.instance, self.user)}
        except ValidationError as e:
            self.instance.name = old_value
            return str(e), {f"[data-name=name][data-pk={self.instance.pk}][data-model=project]": render_name(self.instance, self.user)}

    def handle_description_update(self, new_value):
        from .templatetags.project_tags import render_description
        old_value = self.instance.description
        self.instance.description = new_value
        try:
            self.instance.full_clean()
            self.instance.save()
            return f"description changed from {old_value} to {new_value}", {f"[data-name=description][data-pk={self.instance.pk}][data-model=project]": render_description(self.instance, self.user)}
        except ValidationError as e:
            self.instance.description = old_value
            return str(e), {f"[data-name=description][data-pk={self.instance.pk}][data-model=project]": render_description(self.instance, self.user)}

    def handle_image_update(self, new_value):
        from container.templatetags.container_buttons import button_image
        old_value = self.instance.preferred_image.name
        image = Image.objects.get(id=new_value)
        self.instance.preferred_image = image
        self.instance.save()
        return f"image changed from {old_value} to {image.name}", {f"[data-name=preferred_image][data-pk={self.instance.pk}][data-model=project]": button_image(self.instance, 'project', 'preferred_image')}

    def handle_scope_update(self, new_value):
        from .templatetags.project_buttons import project_scope
        old_value = self.instance.scope
        self.instance.scope = new_value
        self.instance.save()
        return f"scope changed from {old_value} to {new_value}", {f"[data-name=scope][data-pk={self.instance.pk}][data-model=project]": project_scope(self.instance, is_admin=True)}

    def handle_mounts_update(self, attribute, new_value):
        from .templatetags.project_tags import render_volumes
        obj_type, bind_type = Volume, ProjectVolumeBinding
        attribute='volume'
        a=[]
        r=[]
        m=f"mounts changed: "
        n = lambda b: getattr(b, attribute).folder
        for o in obj_type.objects.filter(id__in = new_value):
            b, _=bind_type.objects.get_or_create(**{attribute: o, 'project': self.instance})
            a.append(n(b))
        for b in bind_type.objects.filter(project=self.instance).exclude(**{f"{attribute}__id__in": new_value}):
            r.append(n(b))
            b.delete()
        if a:
            m += "added " + ", ".join(a) + "\n"
        if r:
            m += "removed " + ", ".join(r) + "\n"
        if a or r:
            return m, {f"[data-name=volumes][data-pk={self.instance.pk}][data-model=project]": render_volumes(self.instance, self.user)}
        else:
            return "", {}


class ProjectConfigConsumer(SyncConsumer):
    def receive(self, text_data):
        from kooplexhub.lib.libbase import standardize_str
        parsed = json.loads(text_data)
        logger.debug(parsed)
        request = parsed.get('request')
        if request == "create-project":
            name=parsed.get('name')
            subpath=standardize_str(name)
            scope=parsed.get('scope', Project.Scope.PRIVATE)
            project=Project(name=name, subpath=subpath, preferred_image_id=parsed.get('preferred_image'), description=parsed.get('description'), scope=scope)
            #FIXME: validate
            project.save()
            user=UserProjectBinding.objects.create(user_id = self.userid, project = project, role = UserProjectBinding.Role.CREATOR).user
            self.send(text_data=json.dumps({
                'feedback': f"New project {project.name} is created",
                'reload_page': True,
            }))
            configurator = ProjectConfigHandler(project, user)
            changes = { k: parsed[k] for k in configurator.attribute_handlers.keys() if k in parsed and not k in ["name", "description", "preferred_image", "scope"] }
        elif request == "configure-project":
            pk = parsed.get('pk')
            changes = parsed.get('changes')
            b = UserProjectBinding.objects.get(user__id = self.userid, project__id = pk, role__in = [UserProjectBinding.Role.CREATOR, UserProjectBinding.Role.ADMIN])
            project = b.project
            user = b.user
            configurator = ProjectConfigHandler(project, user)
        elif request == "update-widget":
            field=parsed.get('field')
            if field=='name':
                from .templatetags.project_tags import render_name
                self.send(text_data=json.dumps({'replace_widgets': {f"[data-name=name][data-pk=None][data-model=project]": render_name(value=parsed.get('value'))}}))
            elif field=='description':
                from .templatetags.project_tags import render_description
                self.send(text_data=json.dumps({'replace_widgets': {f"[data-name=description][data-pk=None][data-model=project]": render_description(value=parsed.get('value'))}}))
            elif field=='preferred_image':
                from container.templatetags.container_buttons import button_image
                image = Image.objects.get(id=parsed.get('value'))
                self.send(text_data=json.dumps({'replace_widgets': {f"[data-name=preferred_image][data-pk=None][data-model=project]": button_image(model='project', attr='preferred_image', value=image)}}))
            elif field=='volumes':
                from .templatetags.course_tags import render_volumes
                from volume.models import Volume
                self.send(text_data=json.dumps({'replace_widgets': {f"[data-name=volumes][data-pk=None][data-model=project]": render_volumes(None, user, value=Volume.objects.filter(pk__in=parsed.get('value'))) }}))
            elif field=='scope':
                from .templatetags.project_buttons import project_scope
                self.send(text_data=json.dumps({'replace_widgets': {f"[data-name=scope][data-pk=None][data-model=project]": project_scope(value=parsed.get('value'), is_admin=True)}}))
            else:
                logger.critical(f"unknown widget field {field}")
            return
        else:
            logger.critical(f"Unknown request: {request}")
            return
        failed={}
        # Iterate over the changes and try to update the model instance
        widgets={}
        messages=[]
        for field, new_value in changes.items():
            m, w = configurator.handle_attribute(field, new_value)
            messages.append(m)
            widgets.update(w)
        if messages:
            self.send(text_data=json.dumps({
                'feedback': f"Project {project.name} is configured: " + ",".join(messages) + ".",
                'replace_widgets': widgets,
            }))


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
            "replace_widgets": {
                f'[id=environmentControl-{projectid}]': render_to_string("container/table_control_shortcut.html", {"containers": list(map(lambda o: o.container, bindings)), "pk": upb.id, "objectId": projectid }),
            },
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


class JoinProjectConsumer(SyncConsumer):
    def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        request = parsed.get('request')
        response = {
            'response': request,
        }
        published = list(map(lambda b: b.project, UserProjectBinding.objects.filter(project__scope__in = [ Project.Scope.INTERNAL, Project.Scope.PUBLIC ], role = UserProjectBinding.Role.CREATOR).exclude(user__id = self.userid)))
        joined = list(map(lambda b: b.project, UserProjectBinding.objects.filter(user__id = self.userid, role__in = [ UserProjectBinding.Role.ADMIN, UserProjectBinding.Role.COLLABORATOR ])))
        joinable = set(published).difference(joined)
        if request=='get-joinable':
            response.update({
                "feedback": f"Joinable project list is refreshed",
                "replace": render_to_string('project/list_joinableprojects.html', {'projects': joinable})
            })
            logger.debug(response)
            self.send(text_data=json.dumps(response))
        elif request=='join':
            projectid = parsed.get('pk')
            if filter(lambda p: p.id==projectid, joinable):
                UserProjectBinding.objects.create(project_id=projectid, user_id=self.userid, role=UserProjectBinding.Role.COLLABORATOR)
            response["reloadpage"]=True
            logger.debug(response)
            self.send(text_data=json.dumps(response))
        else:
            logger.critical(request)
