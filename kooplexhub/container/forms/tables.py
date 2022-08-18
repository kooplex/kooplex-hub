from django.utils.html import format_html
import django_tables2 as tables

from project.models import UserProjectBinding
from project.models import ProjectContainerBinding
from education.models import UserCourseBinding
from education.models import CourseContainerBinding
from ..models import Attachment
from ..models import AttachmentContainerBinding
from volume.models import Volume, VolumeContainerBinding, UserVolumeBinding

class TableContainerProject(tables.Table):
    class Meta:
        model = UserProjectBinding
        fields = ('project', 'collaborator')
        sequence = ('button', 'project', 'collaborator')
        attrs = {
                 "class": "table table-striped table-bordered mt-3",
                 "thead": { "class": "thead-dark table-sm" },
                 "td": { "class": "p-1" },
                 "th": { "class": "table-secondary p-1" }
                }
    button = tables.Column(verbose_name = 'Attach', orderable = False, empty_values = ())
    project = tables.Column(orderable = False)
    collaborator = tables.Column(verbose_name = 'Collaborators', empty_values = (), orderable = False)

    def __init__(self, container, user):
        upbs = UserProjectBinding.objects.filter(user = user)
        self.bound_projects = [ b.project for b in ProjectContainerBinding.objects.filter(container = container) ]
        super(TableContainerProject, self).__init__(upbs)

    def render_button(self, record):
        p = record.project
        state = "checked" if p in self.bound_projects else ""
        o_bound = "opacity-75" if p in self.bound_projects else ""
        o_notbound = "" if p in self.bound_projects else "opacity-75"
        return format_html(f"""
<input id="btn-pr-{p.id}" data-size="small"
     type="checkbox" data-toggle="toggle" name="attach-project"
     data-on="<span class=' bi bi-person-workspace'></span>"
     data-off="<span class='bi bi-person-video3'></span>"
     data-onstyle="success {o_bound}" data-offstyle="secondary {o_notbound}" value="{p.id}" {state}>
        """)

    def render_collaborator(self, record):
        return format_html(', '.join(map(lambda c: c.username, record.project.collaborators)))


class TableContainerCourse(tables.Table):
    class Meta:
        model = UserCourseBinding
        fields = ('course',)
        sequence = ('button', 'course', 'description', 'teachers')
        attrs = {
                 "class": "table table-striped table-bordered mt-3",
                 "thead": { "class": "thead-dark table-sm" },
                 "td": { "class": "p-1" },
                 "th": { "class": "table-secondary p-1" }
                }
    button = tables.Column(verbose_name = 'Do', orderable = False, empty_values = ())
    description = tables.Column(empty_values = (), orderable = False)
    course = tables.Column(orderable = False)
    teachers = tables.Column(empty_values = (), orderable = False)

    def __init__(self, container, user):
        ucbs = UserCourseBinding.objects.filter(user = user)
        self.bound_courses = [ b.course for b in CourseContainerBinding.objects.filter(container = container) ]
        super(TableContainerCourse, self).__init__(ucbs)

    def render_button(self, record):
        c = record.course
        state = "checked" if c in self.bound_courses else ""
        o_bound = "opacity-75" if c in self.bound_courses else ""
        o_notbound = "" if c in self.bound_courses else "opacity-75"
        return format_html(f"""
<input id="btn-crs-{c.id}" data-size="small"
     type="checkbox" data-toggle="toggle" name="attach-course"
     data-on="<span class='bi bi-journal-bookmark-fill'></span>"
     data-off="<span class='bi bi-journal-bookmark'></span>"
     data-onstyle="success {o_bound}" data-offstyle="secondary {o_notbound}" value="{c.id}" {state}>
        """)

    def render_description(self, record):
        return record.course.description

    def render_teachers(self, record):
        return record.course.teachers

    def render_course(self, record):
        return format_html(f"""
<span data-toggle="tooltip" title="folder: {record.course.folder}" data-placement="bottom">{record.course.name}</span>
        """)


class TableContainerAttachment(tables.Table):
    class Meta:
        attrs = {
                 "class": "table table-striped table-bordered mt-3",
                 "thead": { "class": "thead-dark table-sm" },
                 "td": { "class": "p-1" },
                 "th": { "class": "table-secondary p-1" }
                }
    button = tables.Column(verbose_name = 'Mount', orderable = False, empty_values = ())
    name = tables.Column(verbose_name = 'Attachment', empty_values = (), orderable = False)
    description = tables.Column(verbose_name = 'Description', empty_values = (), orderable = False)

    def __init__(self, container):
        self.bound_attachments = dict([ (b.attachment, b.id) for b in AttachmentContainerBinding.objects.filter(container = container) ])
        super(TableContainerAttachment, self).__init__(Attachment.objects.all())

    def render_name(self, record):
        return format_html(f"""
<span data-toggle="tooltip" title="folder: {record.folder}" data-placement="bottom">{record.name}</span>
        """)

    def render_button(self, record):
        state = "checked" if record in self.bound_attachments.keys() else ""
        o_bound = "opacity-75" if record in self.bound_attachments.keys() else ""
        o_notbound = "" if record in self.bound_attachments.keys() else "opacity-75"
        return format_html(f"""
<input id="btn-{record.id}" data-size="small"
     type="checkbox" data-toggle="toggle" name="attach"
     data-on="<span class='ri-attachment-line'></span>"
     data-off="<span class='ri-attachment-2'></span>"
     data-onstyle="success {o_bound}" data-offstyle="secondary {o_notbound}" value="{record.id}" {state}>
        """)


class TableContainerVolume(tables.Table):
    class Meta:
        model = Volume
        fields = ('name', 'description')
        sequence = ('button', 'name', 'description')
        attrs = {
                 "class": "table table-striped table-bordered mt-3",
                 "thead": { "class": "thead-dark table-sm" },
                 "td": { "class": "p-1" },
                 "th": { "class": "table-secondary p-1" }
                }
    button = tables.Column(verbose_name = 'Mount', orderable = False, empty_values = ())
    name = tables.Column(verbose_name = 'Volume', orderable = False)
    description = tables.Column(verbose_name = 'Description', orderable = False)

    def __init__(self, container, user):
        self.bound_volumes = [ b.volume for b in VolumeContainerBinding.objects.filter(container = container) ]
        volumes = [ b.volume for b in UserVolumeBinding.objects.filter(user = user) ]
        super(TableContainerVolume, self).__init__(volumes)

    def render_button(self, record):
        state = "checked" if record in self.bound_volumes else ""
        o_bound = "opacity-75" if record in self.bound_volumes else ""
        o_notbound = "" if record in self.bound_volumes else "opacity-75"
        volume = record
        return format_html(f"""
<input id="btn-volume-{record.id}" data-size="small"
     type="checkbox" data-toggle="toggle" name="volume"
     data-on="<span class='ri-database-2-fill'></span>"
     data-off="<span class='ri-database-2-line'></span>"
     data-onstyle="success {o_bound}" data-offstyle="secondary {o_notbound}" value="{record.id}" {state}>
        """)

