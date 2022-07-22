from django.utils.html import format_html
import django_tables2 as tables

from project.models import UserProjectBinding
from project.models import ProjectContainerBinding
from education.models import UserCourseBinding
from education.models import CourseContainerBinding
from ..models import Attachment
from ..models import AttachmentContainerBinding
from volume.models import Volume, VolumeContainerBinding

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
        icon = "bi-patch-plus" if p in self.bound_projects else "bi-patch-minus"
        return format_html(f"""
<input type="checkbox" class="btn-check" name="attach-project" value="{p.id}" id="btn-pr-{p.id}" autocomplete="off" {state}>
<label class="btn btn-outline-secondary" for="btn-pr-{p.id}"><i class="bi {icon}"></i></label>
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
        icon = "bi-patch-plus" if c in self.bound_courses else "bi-patch-minus"
        return format_html(f"""
<input type="checkbox" class="btn-check" name="attach-course" value="{c.id}" id="btn-crs-{c.id}" autocomplete="off" {state}>
<label class="btn btn-outline-secondary" for="btn-crs-{c.id}"><i class="bi {icon}"></i></label>
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
        icon = "oi-envelope-open" if record in self.bound_attachments.keys() else "oi-envelope-closed"
        return format_html(f"""
<input type="checkbox" class="btn-check" name="attach" value="{record.id}" id="btn-{record.id}" autocomplete="off" {state}>
<label class="btn btn-outline-secondary" for="btn-{record.id}"><i class="oi {icon}"></i></label>
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
        super(TableContainerVolume, self).__init__(Volume.objects.all()) #FIXME: filter volumes user can attach

    def render_button(self, record):
        state = "checked" if record in self.bound_volumes else ""
        icon = "bi-file-earmark-check" if record in self.bound_volumes else "bi-file-earmark"
        volume = record
        return format_html(f"""
<input type="checkbox" class="btn-check" name="volume" value="{record.id}" id="btn-volume-{record.id}" autocomplete="off" {state}>
<label class="btn btn-outline-secondary" for="btn-volume-{record.id}"><i class="oi {icon}"></i></label>
        """)

