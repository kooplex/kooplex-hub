from django.utils.html import format_html
import django_tables2 as tables
from django.db.models import Exists, OuterRef, Q

from hub.templatetags.extras import render_user as ru
from hub.models import Profile
from .models import Volume, UserVolumeBinding

from kooplexhub.common import table_attributes


class TableVolume(tables.Table):
    button = tables.TemplateColumn(
        template_name="tables/volume_attach_toggle.html",
        verbose_name="Attach",
        orderable=False,
        extra_context={"size": "small"}, 
    )

    folder = tables.Column(
        verbose_name="Volume",
        orderable=False,
    )

    description = tables.Column(
        verbose_name="Description",
        orderable=False,
    )

    scope = tables.TemplateColumn(
        template_name="widgets/volume_scope.html",
        verbose_name="Scope",
        orderable=False,
    )

    class Meta:
        model = Volume
        fields = ('scope', 'folder', 'description')
        sequence = ('button', 'scope', 'folder', 'description')
        attrs = table_attributes

    # ---- Factory
    @classmethod
    def for_user(cls, user, **kwargs):
        bindings = UserVolumeBinding.objects.filter(
            user=user, volume=OuterRef("pk")
        )
        qs = (
            Volume.objects
            .annotate(has_binding=Exists(bindings))
            .filter(Q(has_binding=True) | Q(scope__in=[Volume.Scope.PUBLIC, Volume.Scope.ATTACHMENT]))
            # Optional: show user-bound volumes first
            .order_by("-has_binding", "folder")
        )
        return cls(qs, **kwargs)



























class TableVolumeShare(tables.Table):
    user = tables.Column(verbose_name = "Collaborators", order_by = ('user__first_name', 'user__last_name'), orderable = False)

    class Meta:
        model = UserVolumeBinding
        fields = ('user',)
        attrs = table_attributes

    def render_user(self, record):
        user = record.user
        prefix = "" if self.is_collaborator_table else "U"
        hidden = f"""
<input type="hidden" name="uservolumebinding_id" value="{record.id}">
        """ if record.id else f"""
<input type="hidden" name="user_id" value="{record.user.id}">
        """
        dhidden = "me-2" if self.is_collaborator_table else 'class="me-2 d-none"'
        chk = "checked" if self.is_collaborator_table and record.role == record.Role.ADMIN else ""
        o_adm = "opacity-75" if self.is_collaborator_table and record.role == record.Role.ADMIN else ""
        o_nadm = "" if self.is_collaborator_table and record.role == record.Role.ADMIN else "opacity-75"
        return format_html(f"""
<span id="admintoggler-{user.id}" {dhidden}><input id="admin-{user.id}" data-size="small"
  type="checkbox" data-toggle="toggle" name="{prefix}admin_id"
  data-on="<span class='oi oi-lock-unlocked'></span>"
  data-off="<span class='oi oi-lock-locked'></span>"
  data-onstyle="success {o_adm}" data-offstyle="danger {o_nadm}" {chk} value="{user.id}"></span>
{ru(user)}
<input type="hidden" id="{prefix}collaborator-search-{user.id}" value="{user.profile.search}">
<input type="hidden" id="{prefix}collaborator-match-{user.id}" value=true>
<input type="hidden" id="{prefix}collaborator-isshown-{user.id}" value=true>
{hidden}
        """)


    def __init__(self, volume, user, collaborator_table):
        collaborators = UserVolumeBinding.objects.filter(volume = volume)
        self.is_collaborator_table = collaborator_table
        if collaborator_table:
            bindings = collaborators.exclude(user = user)
        else:
            profiles = user.profile.everybodyelse.exclude(user__in = [ b.user for b in collaborators ])
            bindings = [ UserVolumeBinding(user = p.user, volume = volume) for p in profiles ]
        self.Meta.attrs["id"] = "collaborators" if collaborator_table else "users"
        super().__init__(bindings)

