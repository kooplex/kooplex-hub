from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
import django_tables2 as tables

from hub.models import VCRepository
from hub.models import VCToken
from hub.models import VCProject, VCProjectServiceBinding

def table_vcproject(service):
    lookup = dict([ (b.vcproject, b.id) for b in VCProjectServiceBinding.objects.filter(service = service) ])

    class SelectColumn(tables.Column):
        def render(self, record):
            if record in lookup.keys():
                return format_html('<input type="hidden" name="vcpsb_ids_before" value="{0}"><input type="checkbox" name="vcpsb_ids_after" value="{0}" checked data-toggle="toggle" data-on="Attached" data-off="Detach" data-onstyle="success" data-offstyle="dark" data-size="xs">'.format(lookup[record]))
            else:
                return format_html('<input type="checkbox" name="vcp_ids" data-toggle="toggle" value="{}" data-on="Attach" data-off="Unused" data-onstyle="success" data-offstyle="dark" data-size="xs">'.format(record.id))
    sc = SelectColumn
    
    class ServiceColumn(tables.Column):
        def render(self, record):
            return format_html(", ".join([ s.name for s in record.services ]))

    class T_VCPROJECT(tables.Table):
        id = sc(verbose_name = 'status', orderable = False)
        services = ServiceColumn(verbose_name = 'Bound to service', empty_values = (), orderable = False)

        class Meta:
            model = VCProject
            fields = ('id', 'repository', 'services')
            sequence = ('id', 'repository', 'services')
            attrs = { "class": "table table-striped table-bordered", "thead": { "class": "thead-dark table-sm" }, "td": { "style": "padding:.5ex" } }

    return T_VCPROJECT


class T_REPOSITORY_CLONE(tables.Table):
    id = tables.Column(verbose_name = 'Status', orderable = False)
    class ReposColumn(tables.Column):
        def render(self, record):
            repo = record.token.repository
            if repo.backend_type == repo.TP_GITHUB:
                return format_html('<img src="/static/content/logos/github.png" alt="github" width="30px" data-toggle="tooltip" title="{}" data-placement="bottom">'.format(repo.url))
            elif repo.backend_type == repo.TP_GITLAB:
                return format_html('<img src="/static/content/logos/gitlab.png" alt="gitlab" width="30px" data-toggle="tooltip" title="{}" data-placement="bottom">'.format(repo.url))
            elif repo.backend_type == repo.TP_GITEA:
                return format_html('<img src="/static/content/logos/gitea.png" alt="gitea" width="30px" data-toggle="tooltip" title="{}" data-placement="bottom">'.format(repo.url))
            else:
                return format_html(record)
    repos = ReposColumn(verbose_name = 'Service', empty_values = (), orderable = False)
    service = tables.Column(verbose_name = 'Service environments', empty_values = (), orderable = False)

    def render_service(self, record):
        return format_html(', '.join([ s.name for s in record.services ]))

    def render_id(self, record):
        if record.cloned:
            return format_html('<input type="checkbox" data-toggle="toggle" name="removecache" value="{}" data-on="Remove" data-off="Cloned" data-onstyle="danger" data-offstyle="success" data-size="xs"'.format(record.id))
        else:
            return format_html('<input type="checkbox" data-toggle="toggle" name="clone" value="{}" data-on="Clone" data-off="Unused" data-onstyle="success" data-offstyle="secondary" data-size="xs">'.format(record.id))
    def render_project_name(self, record):
        return format_html(f'<span data-toggle="tooltip" title="Description: {record.project_description}\nCreated at: {record.project_created_at}" data-placement="bottom">{record.project_name} ({record.project_owner})</span>')

    class Meta:
        model = VCRepository
        fields = ('id', 'repos', 'project_name', 'service', 'clone_folder')
        sequence = ('id', 'repos', 'project_name', 'service', 'clone_folder')
        attrs = { "class": "table table-striped table-bordered", "thead": { "class": "thead-dark table-sm" }, "td": { "style": "padding:.5ex" } }

def s_column(project):
    lookup = dict([ (b.vcproject, b.id) for b in VCProjectProjectBinding.objects.filter(project = project) ])
    class SelectColumn(tables.Column):
        def render(self, record):
            if record in lookup.keys():
                return format_html('<input type="hidden" name="vcppb_ids_before" value="{0}"><input type="checkbox" name="vcppb_ids_after" value="{0}" checked data-toggle="toggle" data-on="Attached" data-off="Detach" data-onstyle="success" data-offstyle="dark" data-size="xs">'.format(lookup[record]))
            else:
                return format_html('<input type="checkbox" name="vcp_ids" data-toggle="toggle" value="{}" data-on="Attach" data-off="Unused" data-onstyle="success" data-offstyle="dark" data-size="xs">'.format(record.id))
    return SelectColumn

class ProjectsColumn(tables.Column):
    def render(self, record):
        return format_html(",".join(map(lambda b: str(b.project), record.vcprojectprojectbindings)))



def table_vctoken(user):
    tokens = [ t for t in user.profile.vctokens ]
    repos = [ t.repository for t in tokens ]
    for r in VCRepository.objects.all():
        if not r in repos:
            tokens.append( VCToken(repository = r, user = user) )
 
    class T_VCTOKEN(tables.Table):
        id = tables.Column(verbose_name = 'Job', empty_values = ())
        username = tables.Column(verbose_name = 'Registered username', empty_values = ())
        token = tables.Column(empty_values = ())
        rsa = tables.Column(empty_values = ())

        def render_id(self, record):
            if record.id:
                return format_html("<input type='hidden' name='token_ids' value='%s'><input type='checkbox' name='rm_token_ids' value='%s'> Delete" % (record.id, record.id))
            else:
                return format_html("<input type='checkbox' name='new_repository_ids' value='%s'> New" % (record.repository.id))

        def render_token(self, record):
            if record.id:
                return format_html("<input type='hidden' name='token_before-%d' value='%s'><input type='password' name='token_after-%d' value='%s'>" % (record.id, record.token, record.id, record.token))
            else:
                return format_html("<input type='password' name='token-%d' value='' placeholder=''>" % (record.repository.id))

        def render_rsa(self, record):
            if record.id:
                return format_html("<input type='hidden' name='rsa_before-%d' value='%s'><input type='text' name='rsa_after-%d' value='%s'>" % (record.id, record.rsa, record.id, record.rsa))
            else:
                return format_html("<input type='text' name='rsa-%d' value='' placeholder='RSA private key'>" % (record.repository.id))

        def render_username(self, record):
            if record.id:
                return format_html("<input type='hidden' name='username_before-%d' value='%s'><input type='text' name='username_after-%d' value='%s'>" % (record.id, record.username, record.id, record.username))
            else:
                return format_html("<input type'text' name='username-%d' value='%s'>" % (record.repository.id, user.username))

        class Meta:
            model = VCToken
            orderable = False
            fields = ('id', 'repository', 'username', 'rsa', 'token', 'last_used', 'error_flag')
#            sequence = ('id', 'repository', 'projects')
            attrs = { "class": "table table-striped table-bordered", "thead": { "class": "thead-dark table-sm" }, "td": { "style": "padding:.5ex" } }

    return T_VCTOKEN(tokens)
