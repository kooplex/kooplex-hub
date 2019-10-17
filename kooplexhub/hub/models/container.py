import logging
import os
import datetime
import requests
import time

from django.db import models
from django.utils import timezone
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.contrib.auth.models import User

from .project import Project, UserProjectBinding
from .report import Report
from .course import Course
from .volume import Volume, VolumeProjectBinding
from .image import Image
from .versioncontrol import VCProjectProjectBinding
from .filesync import FSLibraryProjectBinding

from kooplex.settings import KOOPLEX
from kooplex.lib import  standardize_str, now

logger = logging.getLogger(__name__)


ST_LOOKUP = {
    'np': 'Not present in docker engine.',
    'man': 'Manifested but not running.',
    'run': 'Running in docker engine.',
}

class Container(models.Model):
    ST_NOTPRESENT = 'np'
    ST_NOTRUNNING = 'man'
    ST_RUNNING = 'run'
    STATE_LIST = [ ST_NOTPRESENT, ST_NOTRUNNING, ST_RUNNING ]

    name = models.CharField(max_length = 200, null = False)
    user = models.ForeignKey(User, null = False)
    image = models.ForeignKey(Image, null = True)
    launched_at = models.DateTimeField(default = timezone.now)
    marked_to_remove = models.BooleanField(default = False)

    state = models.CharField(max_length = 16, choices = [ (x, ST_LOOKUP[x]) for x in STATE_LIST ], default = ST_NOTPRESENT)
    last_message = models.CharField(max_length = 512, null = True)
    last_message_at = models.DateTimeField(default = None, null = True)


    def __lt__(self, c):
        return self.launched_at < c.launched_at

    def __str__(self):
        return "<Container %s@%s>" % (self.name, self.user)

    @property
    def is_created(self):
        return self.state != self.ST_NOTPRESENT

    @property
    def is_running(self):
        return self.state == self.ST_RUNNING

    @property
    def is_stopped(self):
        return self.state == self.ST_NOTRUNNING

    @property
    def uptime(self):
        timenow = now()
        delta = timenow - self.launched_at
        return delta if self.is_running else -1

    @property
    def url(self):
        return "http://%s:%d" % (self.name, KOOPLEX.get('spawner', {}).get('port', 8000))

    @property
    def url_test(self):
        return "http://%s:%d" % (self.name, KOOPLEX.get('spawner', {}).get('port_test', 9000))

    @property
    def url_external(self):
        return os.path.join(KOOPLEX['base_url'], self.proxy_path, '?token=%s' % self.user.profile.token)

    @property
    def proxy_path(self):
        info = { 'containername': self.name }
        return KOOPLEX['spawner']['pattern_proxypath'] % info

    @property
    def proxy_path_test(self):
        info = { 'containername': self.name }
        return KOOPLEX['spawner']['pattern_proxypath_test'] % info

    @property
    def projects(self):
        for binding in ProjectContainerBinding.objects.filter(container = self):
            yield binding.project

    @property
    def course(self):
        try:
            return CourseContainerBinding.objects.get(container = self).course
        except CourseContainerBinding.DoesNotExist:
            return None

    @property
    def report(self):
        try:
            return ReportContainerBinding.objects.get(container = self).report
        except ReportContainerBinding.DoesNotExist:
            return None

    @property
    def userprojectbindings(self):
        for project in self.projects:
            yield UserProjectBinding.objects.get(user = self.user, project = project)

    @property
    def vcprojectprojectbindings(self):
        serve_history = {}
        for project in self.projects:
            creator = project.creator
            for vcppb in VCProjectProjectBinding.objects.filter(project = project):
                if vcppb.vcproject.token.user == self.user:
                    yield vcppb
                    serve_history[project] = None
                if vcppb.vcproject.token.user == creator:
                    if not project in serve_history:
                        serve_history[project] = vcppb
        for vcppb in serve_history.values():
            if vcppb is not None:
                yield vcppb

    @property
    def fslibraryprojectbindings(self):
        for project in self.projects:
            for fslpb in FSLibraryProjectBinding.objects.filter(project = project, fslibrary__token__user = self.user):
                yield fslpb

    @property
    def projects_addable(self):
        bound_projects = set(self.projects)
        for binding in UserProjectBinding.objects.filter(user = self.user):
            if binding.project in bound_projects:
                continue
            img = binding.project.image
            if self.image is None or img is None or self.image == img:
                yield binding.project

    @property
    def volumecontainerbindings(self):
        for binding in VolumeContainerBinding.objects.filter(container = self):
            logger.debug(binding)
            yield binding

    @property
    def volumes(self):
        for volume in VolumeContainerBinding.list_containervolumes(container = self):
            yield volume

    def wait_until_ready(self):
        from kooplex.lib import keeptrying
        return keeptrying(method = requests.get, times = 10, url = self.api)

    @property
    def n_projects(self):
        return len(list(self.projects))

    @staticmethod
    def get_userprojectcontainer(user, project_id, create):
        logger.debug("project id %s & user %s" % (project_id, user))
        project = Project.get_userproject(project_id, user)
        logger.debug("found project %s and authorized for user %s" % (project, user))
        for binding in ProjectContainerBinding.objects.filter(project = project):
            if binding.container.user == user:
                logger.debug("container in db %s" % binding.container)
                return binding.container
        if create:
            containername = "%s-%s-%s" % (user.username, project.cleanname, project.creator.username)
            container = Container.objects.create(name = containername, user = user)
            ProjectContainerBinding.objects.create(project = project, container = container)
            logger.debug("new container in db %s" % container)
            return container 
        raise Container.DoesNotExist

    @staticmethod
    def get_usercoursecontainer(user, course_id, create):
        logger.debug("course id %s & user %s" % (course_id, user))
        course = Course.get_usercourse(course_id, user)
        logger.debug("found course %s and authorized for user %s" % (course, user))
        for binding in CourseContainerBinding.objects.filter(course = course):
            if binding.container.user == user:
                logger.debug("container in db %s" % binding.container)
                return binding.container
        if create:
            containername = "%s-%s" % (user.username, course.folder)
            container = Container.objects.create(name = containername, user = user)
            CourseContainerBinding.objects.create(course = course, container = container)
            logger.debug("new container in db %s" % container)
            return container 
        raise Container.DoesNotExist

    @staticmethod
    def get_reportcontainer(report, create):
        logger.debug("report %s" % (report))
        try:
            return ReportContainerBinding.objects.get(report = report).container
        except ReportContainerBinding.DoesNotExist:
            logger.debug("ReportContainer for report %s does not exist" % report)
        if create:
            containername = "report-%s-%s-%s" % (report.creator.username, report.cleanname, report.ts_human.replace(':', '').replace('_', ''))
            container = Container.objects.create(name = containername, user = report.creator, image=report.image)
            ReportContainerBinding.objects.create(report = report, container = container)
            logger.debug("new container in db %s" % container)
            return container 
        raise Container.DoesNotExist

    def docker_start(self):
        self.state = self.ST_RUNNING
        self.save()

    def docker_stop(self):
        self.state = self.ST_NOTRUNNING
        self.save()

    def docker_remove(self):
        self.state = self.ST_NOTPRESENT
        self.save()

    @property
    def environment(self):
        envs = {
            'NB_USER': self.user.username,
            'NB_UID': self.user.profile.userid,
            'NB_GID': self.user.profile.groupid,
            'NB_URL': self.proxy_path,
            'NB_PORT': KOOPLEX.get('spawner', {}).get('port', 8000),
            'NB_TOKEN': self.user.profile.token,
            'CONTAINER_NAME': self.name,
        }
        for ce in ContainerEnvironment.objects.filter(container = self):
            envs[ce.name] = ce.value
            logger.debug("Adding extra envs: %s"%ce.value)
        report = self.report
        if report:
            envs['REPORT_TYPE'] = report.reporttype
            envs['REPORT_DIR'] = os.path.join('/home/', 'report', report.cleanname, report.ts_human)
            envs['REPORT_PORT'] = 9000
            envs['REPORT_INDEX'] = report.index
        return envs

    @property
    def api(self):
        return os.path.join(self.url, 'notebook', self.proxy_path)

    def managemount(self):
        import threading
        if hasattr(self, '_timer'):
            logger.debug("still aggregating...")
            return
        else:
            logger.debug("bla")
            self._timer = threading.Timer(1, self._managemount)
            self._timer.start()
            logger.debug("Aggregating timer started.")

    def _managemount(self):
        from kooplex.lib import Docker
        try: 
            logger.debug("Aggregating timer expired.")
            assert self.is_created, "%s is not manifested in docker engine"
            Docker().managemount(self)
        except Exception as e: 
            logger.error("cannot manage mapping in container %s -- %s" % (self, e)) 
        finally:
            del self._timer

    def refresh_state(self):
        from kooplex.lib import Docker 
        try:
            Docker().refresh_container_state(self)
        except TypeError:
            pass

class ContainerEnvironment(models.Model):
    name = models.CharField(max_length = 200, null = False)
    value = models.CharField(max_length = 200, null = False)
    container = models.ForeignKey(Container, null = False)


@receiver(pre_save, sender = Container)
def container_state_change(sender, instance, **kwargs):
    from kooplex.lib import Docker
    from kooplex.lib.proxy import addroute, removeroute
    is_new = instance.id is None
    logger.debug("DDDD %s"%instance.image)
    old_instance = Container() if is_new else Container.objects.get(id = instance.id)
    msg = "%s %s" % (instance.id, is_new)
    if not is_new and instance.state == old_instance.state:
        return
    msg += "%s statchange %s -> %s" % (instance, ST_LOOKUP[old_instance.state], ST_LOOKUP[instance.state])
    logger.debug(msg)
    docker = Docker()
    # FIXME
    #assert instance.n_projects > 0 or instance.course or instance.report or instance.state == Container.ST_NOTPRESENT, 'container %s with 0 projects' % instance
    if old_instance.state == Container.ST_NOTPRESENT and instance.state == Container.ST_RUNNING:
        docker.run_container(instance)
        addroute(instance)
        instance.marked_to_remove = False

    elif old_instance.state == Container.ST_RUNNING and instance.state == Container.ST_NOTRUNNING:
        docker.stop_container(instance)
        removeroute(instance)
        if instance.marked_to_remove:
            docker.remove_container(instance)
            instance.marked_to_remove = False
            instance.state = Container.ST_NOTPRESENT
    elif old_instance.state == Container.ST_NOTRUNNING and instance.state == Container.ST_RUNNING:
        docker.run_container(instance)
        addroute(instance)
    elif old_instance.state == Container.ST_NOTRUNNING and instance.state == Container.ST_NOTPRESENT:
        docker.remove_container(instance)
        instance.marked_to_remove = False
    elif old_instance.state == Container.ST_RUNNING and instance.state == Container.ST_NOTPRESENT:
        docker.stop_container(instance)
        removeroute(instance)
        docker.remove_container(instance)
        instance.marked_to_remove = False
    else:
         logger.critical(msg)

def remove_container_environment(instance, env):
    logger.debug("Removing environment from %s"%(instance))
    try:
         for ce in ContainerEnvironment.objects.filter(container = instance, name = env):
             ce.delete()
    except:
         logger.error('Container %s environments had no environments or couldn''t deleted. %s' % (instance, e))   

@receiver(pre_save, sender = Container)
def container_image_change(sender, instance, **kwargs):
    import pwgen
    is_new = instance.id is None
    old_instance = Container() if is_new else Container.objects.get(id = instance.id)
    logger.debug("Changing image from %s to %s"%(old_instance.image, instance.image))
    if not is_new and old_instance.image != instance.image:
         remove_container_environment(instance, 'PASSWORD')
         instance.marked_to_remove = True
         if instance.state == Container.ST_NOTRUNNING:
             from kooplex.lib import Docker
             docker = Docker()
             docker.remove_container(instance)
             instance.state = Container.ST_NOTPRESENT
         if instance.state == Container.ST_NOTPRESENT:
             instance.marked_to_remove = False
    if instance.image is None:
        return
    if instance.marked_to_remove:
         remove_container_environment(instance, 'PASSWORD')
    if instance.image.name == 'rstudio' and not instance.marked_to_remove: #FIXME: hard coded stuf!!!!!!!!!!!!!!!!!
         try:
             ContainerEnvironment.objects.get(container = instance, name = 'PASSWORD')
         except:
             ContainerEnvironment.objects.get_or_create(container = instance, name = 'PASSWORD', value = pwgen.pwgen(16))

@receiver(pre_save, sender = Container)
def container_message_change(sender, instance, **kwargs):
    is_new = instance.id is None
    old_instance = Container() if is_new else Container.objects.get(id = instance.id)
    if old_instance.last_message != instance.last_message:
         logger.debug("msg of %s: %s" % (instance, instance.last_message))
         instance.last_message_at = now()



@receiver(post_save, sender = Container)
def bind_home(sender, instance, created, **kwargs):
    if created and instance.report is None:
        try:
            v_home = Volume.objects.get(volumetype = Volume.HOME)
            VolumeContainerBinding.objects.create(container = instance, volume = v_home)
        except Exception as e:
            logger.error('Home not bound -- %s' % e)


@receiver(post_save, sender = Container)
def bind_report(sender, instance, created, **kwargs):
    if created:# and not instance.course:
        try:
            v_report = Volume.objects.get(volumetype = Volume.REPORT)
            VolumeContainerBinding.objects.create(container = instance, volume = v_report)
        except Exception as e:
            logger.error('Report not bound -- %s' % e)


@receiver(post_save, sender = Container)
def bind_garbage(sender, instance, created, **kwargs):
    if created and instance.report is None:
        try:
            v_garbage = Volume.objects.get(volumetype = Volume.GARBAGE)
            VolumeContainerBinding.objects.create(container = instance, volume = v_garbage)
        except Exception as e:
            logger.error('Garbage not bound -- %s' % e)

@receiver(post_save, sender = Container)
def bind_filesync(sender, instance, created, **kwargs):
    if created and instance.report is None:
        try:
            v_filesync = Volume.objects.get(volumetype = Volume.FILESYNC)
            VolumeContainerBinding.objects.create(container = instance, volume = v_filesync)
        except Exception as e:
            logger.error('Filesync not bound -- %s' % e)

class ProjectContainerBinding(models.Model):
    project = models.ForeignKey(Project, null = False)
    container = models.ForeignKey(Container, null = False)

    def __str__(self):
        return "<ProjectContainerBinding %s-%s>" % (self.project, self.container)


@receiver(post_save, sender = ProjectContainerBinding)
def bind_share(sender, instance, created, **kwargs):
    if created:
        c = instance.container
        try:
            v_share = Volume.objects.get(volumetype = Volume.SHARE)
            VolumeContainerBinding.objects.get(container = c, volume = v_share)
            logger.debug('Share already bound to container %s' % c)
        except VolumeContainerBinding.DoesNotExist:
            VolumeContainerBinding.objects.create(container = c, volume = v_share)
            logger.debug('Share bound to container %s' % c)
        except Exception as e:
            logger.error('Share not bound to container %s -- %s' % (c, e))

@receiver(pre_delete, sender = ProjectContainerBinding)
def container_to_be_removed(sender, instance, **kwargs):
        logger.debug('Set %s container to be removed' % instance)
        c = instance.container
        c.marked_to_remove = True
        c.save()


#@receiver(pre_delete, sender = ProjectContainerBinding)                                                   
@receiver(pre_delete, sender = Container)    
def container_environmentS(sender, instance, **kwargs):                                                   
        c = instance                                                                             
        remove_container_environment(c, 'PASSWORD')
                                                                                                                                                                          

@receiver(post_delete, sender = ProjectContainerBinding)
def remove_bind_share(sender, instance, **kwargs):
    c = instance.container
    if not ProjectContainerBinding.objects.filter(container = c):
        try:
            v_share = Volume.objects.get(volumetype = Volume.SHARE)
            VolumeContainerBinding.objects.get(container = c, volume = v_share).delete()
            logger.debug('Share unbound from container %s' % instance)
        except Exception as e:
            logger.error('Share was not unbound from container %s -- %s' % (instance, e))



@receiver(post_save, sender = ProjectContainerBinding)
def bind_workdir(sender, instance, created, **kwargs):
    if created:
        c = instance.container
        try:
            v_workdir = Volume.objects.get(volumetype = Volume.WORKDIR)
            VolumeContainerBinding.objects.get(container = c, volume = v_workdir)
            logger.debug('Workdir already bound to container %s' % c)
        except VolumeContainerBinding.DoesNotExist:
            VolumeContainerBinding.objects.create(container = c, volume = v_workdir)
            logger.debug('Workdir bound to container %s' % c)
        except Exception as e:
            logger.error('Workdir not bound to container %s -- %s' % (c, e))


@receiver(post_delete, sender = ProjectContainerBinding)
def remove_bind_workdir(sender, instance, **kwargs):
    c = instance.container
    if not ProjectContainerBinding.objects.filter(container = c):
        try:
            v_workdir = Volume.objects.get(volumetype = Volume.WORKDIR)
            VolumeContainerBinding.objects.get(container = c, volume = v_workdir).delete()
            logger.debug('Workdir unbound from container %s' % instance)
        except Exception as e:
            logger.error('Workdir was not unbound from container %s -- %s' % (instance, e))


@receiver(post_save, sender = ProjectContainerBinding)
def bind_git(sender, instance, created, **kwargs):
    if created:
        c = instance.container
        try:
            v_git = Volume.objects.get(volumetype = Volume.GIT)
            VolumeContainerBinding.objects.get(container = c, volume = v_git)
            logger.debug('Git cache already bound to container %s' % c)
        except VolumeContainerBinding.DoesNotExist:
            VolumeContainerBinding.objects.create(container = c, volume = v_git)
            logger.debug('Git cache bound to container %s' % c)
        except Exception as e:
            logger.error('Git cache not bound to container %s -- %s' % (c, e))


@receiver(post_delete, sender = ProjectContainerBinding)
def remove_bind_git(sender, instance, **kwargs):
    c = instance.container
    if not ProjectContainerBinding.objects.filter(container = c):
        try:
            v_git = Volume.objects.get(volumetype = Volume.GIT)
            VolumeContainerBinding.objects.get(container = c, volume = v_git).delete()
            logger.debug('Git cache unbound from container %s' % instance)
        except Exception as e:
            logger.error('Git cache was not unbound from container %s -- %s' % (instance, e))


@receiver(post_save, sender = ProjectContainerBinding)
def bind_stg(sender, instance, created, **kwargs):
    if created:
        c = instance.container
        for vpb in VolumeProjectBinding.objects.filter(project = instance.project, volume__volumetype = Volume.STORAGE):
            v = vpb.volume
            try:
                VolumeContainerBinding.objects.get(container = c, volume = v)
                logger.debug('Storage bound to container %s' % c)
            except VolumeContainerBinding.DoesNotExist:
                VolumeContainerBinding.objects.create(container = c, volume = v)
                logger.debug('Storage bound to container %s' % c)
            except Exception as e:
                logger.error('Storage not bound to container %s -- %s' % (c, e))

@receiver(post_save, sender = ProjectContainerBinding)
def bind_vol(sender, instance, created, **kwargs):
    if created:
        c = instance.container
        for vpb in VolumeProjectBinding.objects.filter(project = instance.project, volume__volumetype = Volume.FUNCTIONAL):
            v = vpb.volume
            try:
                VolumeContainerBinding.objects.get(container = c, volume = v)
                logger.debug('Functional volume bound to container %s' % c)
            except VolumeContainerBinding.DoesNotExist:
                VolumeContainerBinding.objects.create(container = c, volume = v)
                logger.debug('Functional volume was not bound, binding now to container %s' % c)
            except Exception as e:
                logger.error('Functional volume not bound to container %s -- %s' % (c, e))


#FIXME: remove_bind_stg


@receiver(post_save, sender = ProjectContainerBinding)
def managemount_add_project(sender, instance, created, **kwargs):
    if created:
        c = instance.container
        try:
            c.managemount()
        except Exception as e:
            logger.error('Container %s -- %s' % (c, e))


@receiver(post_delete, sender = ProjectContainerBinding)
def managemount_remove_project(sender, instance, **kwargs):
    c = instance.container
    try:
        c.managemount()
    except Exception as e:
        logger.error('Container %s -- %s' % (c, e))


@receiver(post_save, sender = VCProjectProjectBinding)
def managemount_add_vcprojectprojectbinding(sender, instance, created, **kwargs):
    if created:
        for c in Container.objects.filter(user = instance.vcproject.token.user, state = Container.ST_RUNNING):
            try:
                c.managemount()
            except Exception as e:
                logger.error('Container %s -- %s' % (c, e))


@receiver(post_delete, sender = VCProjectProjectBinding)
def managemount_remove_vcprojectprojectbinding(sender, instance, **kwargs):
    for c in Container.objects.filter(user = instance.vcproject.token.user, state = Container.ST_RUNNING):
        try:
            c.managemount()
        except Exception as e:
            logger.error('Container %s -- %s' % (c, e))


@receiver(post_delete, sender = ProjectContainerBinding)
def assert_container_has_projects(sender, instance, **kwargs):
    container = instance.container
    if container.n_projects == 0:
        container.state = Container.ST_NOTPRESENT
        container.save()
         



class VolumeContainerBinding(models.Model):
    volume = models.ForeignKey(Volume, null = False)
    container = models.ForeignKey(Container, null = False)

    def __str__(self):
       return "%s-%s" % (self.container.name, self.volume.name)

    @staticmethod
    def list_containervolumes(container):
        for binding in VolumeContainerBinding.objects.filter(container = container):
            yield binding.volume
               

@receiver(pre_save, sender = ProjectContainerBinding)
def update_image(sender, instance, **kwargs):
    if instance.container.image is None:
        instance.container.image = instance.project.image
        instance.container.save()
        logger.debug("container (%s) image is set %s" % (instance.container, instance.container.image))
    if instance.project.image is not None:
        assert instance.container.image == instance.project.image, "Conflicting images %s =/= %s" % (instance.container.image, instance.project.image)



@receiver(pre_save, sender = Project)
def container_check_image(sender, instance, **kwargs):
    try:
        old = sender.objects.get(id = instance.id)
    except sender.DoesNotExist:
        return
    if old.image != instance.image:
        pcbs = ProjectContainerBinding.objects.filter(project = instance)
        for pcb in pcbs:
            c = pcb.container
            #assert c.image is None or c.image == instance.image, "Conflict with container %s" % c #FIXME: ez igy nem jo
        for pcb in pcbs:
            c = pcb.container
            if c.is_running or c.is_stopped:
                c.marked_to_remove = True
            c.image = instance.image
            c.save()




class CourseContainerBinding(models.Model):
    course = models.ForeignKey(Course, null = False)
    container = models.ForeignKey(Container, null = False)

    def __str__(self):
        return "<CourseContainerBinding %s-%s>" % (self.course, self.container)


@receiver(pre_save, sender = Course)
def update_courseimage(sender, instance, **kwargs):
    ccbs = CourseContainerBinding.objects.filter(course = instance)
    for ccb in ccbs:
        c = ccb.container
        if c.is_running or c.is_stopped:
            c.marked_to_remove = True
        c.image = instance.image
        c.save()
        logger.debug("container (%s) image is set %s" % (c, c.image))


@receiver(pre_save, sender = CourseContainerBinding)
def update_course_image(sender, instance, **kwargs):
    if instance.container.image is None:
        instance.container.image = instance.course.image
        instance.container.save()
        logger.debug("container (%s) image is set %s" % (instance.container, instance.container.image))
    if instance.course.image is not None:
        assert instance.container.image == instance.course.image, "Conflicting images %s =/= %s" % (instance.container.image, instance.course.image)


@receiver(post_save, sender = CourseContainerBinding)
def bind_courserelatedvolumes(sender, instance, created, **kwargs):
    if created:
        for vt in [ Volume.COURSE_SHARE, Volume.COURSE_WORKDIR, Volume.COURSE_ASSIGNMENTDIR ]:
            try:
                volume = Volume.objects.get(volumetype = vt)
                binding = VolumeContainerBinding.objects.create(container = instance.container, volume = volume)
                logger.debug("binding created %s" % binding)
            except Volume.DoesNotExist:
                logger.error("cannot create binding coursecontainerbinding %s volume %s" % (instance, vt))


class ReportContainerBinding(models.Model):
    report = models.ForeignKey(Report, null = False)
    container = models.ForeignKey(Container, null = False)

    def __str__(self):
        return "<ReportContainerBinding %s-%s>" % (self.report, self.container)

@receiver(post_save, sender = ReportContainerBinding)
def bind_reportvolume(sender, instance, created, **kwargs):
    if created:
        try:
            volume = Volume.objects.get(volumetype = Volume.REPORT)
            binding = VolumeContainerBinding.objects.create(container = instance.container, volume = volume)
            logger.debug("binding created %s" % binding)
        except Volume.DoesNotExist:
            logger.error("cannot create binding coursecontainerbinding %s volume %s" % (instance, vt))

