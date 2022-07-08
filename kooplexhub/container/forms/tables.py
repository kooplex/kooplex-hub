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
        fields = ('id', 'project', 'collaborator')
        attrs = {
                 "class": "table table-striped table-bordered",
                 "thead": { "class": "thead-dark table-sm" },
                 "td": { "style": "padding:.5ex" },
                 "th": { "style": "padding:.5ex", "class": "table-secondary" }
                }
    id = tables.Column(verbose_name = 'Do', orderable = False)
    collaborator = tables.Column(verbose_name = 'Collaborators', empty_values = (), orderable = False)

    def __init__(self, container, userprojectbindings):
        self.bound_projects = [ b.project for b in ProjectContainerBinding.objects.filter(container = container) ]
        super(TableContainerProject, self).__init__(userprojectbindings)
        #self.columns['id'].verbose_name = 'Select'

    def render_id(self, record):
        p = record.project
        if p in self.bound_projects:
            template = f"""
<div class="form-check form-switch">
  <input type="hidden" name="project_ids_before" value="{p.id}">
  <input class="form-check-input" type="checkbox" id="cb_pid-{p.id}" name="project_ids_after" value="{p.id}" checked />
  <label class="form-check-label" for="cb_pid-{p.id}"> Keep added</label>
</div>
            """
        else:
            template = f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="cb_pid-{p.id}" name="project_ids_after" value="{p.id}" />
  <label class="form-check-label" for="cb_pid-{p.id}"> Add</label>
</div>
            """
        return format_html(template)

    def render_collaborator(self, record):
        return format_html(', '.join(map(lambda c: c.username, record.project.collaborators)))


class TableContainerCourse(tables.Table):
    class Meta:
        model = UserCourseBinding
        fields = ('id', 'course', 'description', 'teachers')
        attrs = {
                 "class": "table table-striped table-bordered",
                 "thead": { "class": "thead-dark table-sm" },
                 "td": { "style": "padding:.5ex" },
                 "th": { "style": "padding:.5ex", "class": "table-secondary" }
                }
    id = tables.Column(verbose_name = 'Do', orderable = False)
    description = tables.Column(empty_values = (), orderable = False)
    teachers = tables.Column(empty_values = (), orderable = False)

    def __init__(self, container, usercoursebindings):
        self.bound_courses = [ b.course for b in CourseContainerBinding.objects.filter(container = container) ]
        super(TableContainerCourse, self).__init__(usercoursebindings)
        #self.columns['id'].verbose_name = 'Select'

    def render_id(self, record):
        c = record.course
        if c in self.bound_courses:
            template = f"""
<div class="form-check form-switch">
  <input type="hidden" name="course_ids_before" value="{c.id}">
  <input class="form-check-input" type="checkbox" id="cb_cid-{c.id}" name="course_ids_after" value="{c.id}" checked />
  <label class="form-check-label" for="cb_cid-{c.id}"> Keep added</label>
</div>
            """
        else:
            template = f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="cb_cid-{c.id}" name="course_ids_after" value="{c.id}" />
  <label class="form-check-label" for="cb_cid-{c.id}"> Add</label>
</div>
            """
        return format_html(template)

    def render_description(self, record):
        return format_html(record.course.description)

    def render_teachers(self, record):
        return record.course.teachers

    def render_course(self, record):
        return format_html(f"""
<span data-toggle="tooltip" title="The folder associated with course {record.course.name} is {record.course.folder}" data-placement="bottom">{record.course.name}</span>
        """)


class TableContainerAttachment(tables.Table):
    class Meta:
        model = Attachment
        fields = ('id', 'name', 'folder', 'description')
        sequence = ('id', 'name', 'folder', 'description')
        attrs = {
                 "class": "table table-striped table-bordered",
                 "thead": { "class": "thead-dark table-sm" },
                 "td": { "style": "padding:.5ex" },
                 "th": { "style": "padding:.5ex", "class": "table-secondary" }
                }

    def __init__(self, container, attachments):
        self.bound_attachments = dict([ (b.attachment, b.id) for b in AttachmentContainerBinding.objects.filter(container = container) ])
        super(TableContainerAttachment, self).__init__(attachments)
        #self.columns['id'].verbose_name = 'Mount'

    def render_id(self, record):
        if record in self.bound_attachments.keys():
            template = f"""
<div class="form-check form-switch">
  <input type="hidden" name="asb_ids_before" value="{self.bound_attachments[record]}">
  <input class="form-check-input" type="checkbox" id="cb_asbid-{record.id}" name="asb_ids_after" value="{self.bound_attachments[record]}" checked />
  <label class="form-check-label" for="cb_asbid-{record.id}"> Mounted</label>
</div>
            """
        else:
            template = f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="cb_a-{record.id}" name="a_ids" value="{record.id}" />
  <label class="form-check-label" for="cb_a-{record.id}"> Mount</label>
</div>
            """
        return format_html(template)


class TableContainerVolume(tables.Table):
    class Meta:
        model = Volume
        fields = ('id', 'name', 'description')
        sequence = ('id', 'name', 'description')
        attrs = {
                 "class": "table table-striped table-bordered",
                 "thead": { "class": "thead-dark table-sm" },
                 "td": { "style": "padding:.5ex" },
                 "th": { "style": "padding:.5ex", "class": "table-secondary" }
                }

    def __init__(self, container, uservolumebindings):
        self.bound_volumes = [ b.volume for b in VolumeContainerBinding.objects.filter(container = container) ]
        super(TableContainerVolume, self).__init__(uservolumebindings)
        #self.columns['id'].verbose_name = 'Mount'

    def render_id(self, record):
        volume = record
        if volume in self.bound_volumes:
            template = f"""
<div class="form-check form-switch">
  <input type="hidden" name="volume_ids_before" value="{volume.id}">
  <input class="form-check-input" type="checkbox" id="cb_vsid-{volume.id}" name="volume_ids_after" value="{volume.id}" checked />
  <label class="form-check-label" for="cb_vsid-{volume.id}"> Mounted</label>
</div>
            """
        else:
            template = f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="cb_v-{volume.id}" name="volume_ids_after" value="{volume.id}" />
  <label class="form-check-label" for="cb_v-{volume.id}"> Mount</label>
</div>
            """
        return format_html(template)
