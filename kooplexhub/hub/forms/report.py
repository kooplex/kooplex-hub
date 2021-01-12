from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from hub.models import Report

class FormReport(forms.ModelForm):
    password = forms.CharField(required = False)

    class Meta:
        model = Report
        fields = [ 'name', 'description', 'image', 'scope', 'password', ]
        ##attrs = { "class": "form-control" }
        labels = {
            'name': _('The name of your report'),
            'description': _('A short description'),
        }
        help_texts = {
            'name': _('Report name should be unique.'),
            'description': _('It is always a good idea to have a short memo.'),
            'index': _('The name of the file the report service lands on. (Bokeh does not require it.)'),
            'password': _('Leave it empty for the public.'),
        }

    def r_tree(self):
        tree = ""
        icon_index = '<i class="fa fa-globe-europe fa-fw"></i>'
        icon_folder = '<i class="fa fa-folder-open fa-fw"></i>'
        icon_project = '<i class="fa fa-project-diagram fa-fw"></i>'
        for p, s in self.tree.items():
            sub_folders = ""
            for f, ixs in s.items():
                indices = ""
                for i in ixs:
                    r = f'<input type="radio" name="index_selector" value="({p.id},{f},{i})">'
                    indices += f'<div role="treeitem" class="list-group-item">{r}{icon_index}{i}</div>'
                div_indices = f'<div role="group" class="list-group collapse" id="{p.id}-{f}">{indices}</div>'
                sub_folders += f'<div role="treeitem" class="list-group-item" data-toggle="collapse" data-target="#{p.id}-{f}" id="f-{p.id}-{f}" aria-expanded="true" aria-controls="c-{p.id}">{icon_folder}{f}{div_indices}</div>'
            div_folders = f'<div role="group" class="list-group collapse" id="{p.id}">{sub_folders}</div>'
            tree += f'<div role="treeitem" class="list-group-item" data-toggle="collapse" data-target="#{p.id}" id="c-{p.id}">{icon_project}{p.name}{div_folders}</div>'
        html = f'<tr><td style="vertical-align: top;"><b>Select index:</b></td><td><div id="indextree" class="bstreeview">{tree}</div></td></tr>'
        return format_html(html)


    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(FormReport, self).__init__(*args, **kwargs)
        self.fields['image'].empty_label = None
        self.fields["description"].widget.attrs["rows"] = 3
        self.fields["description"].widget.attrs["cols"] = 20
        self.tree = user.profile.files_reportprepare()
        for field in self.fields.keys():
            self.fields[field].widget.attrs["class"] = "form-control"

        for field in self.fields:
            help_text = self.fields[field].help_text
            self.fields[field].help_text = None
            if help_text != '':
                extra = {
                    'data-toggle': 'tooltip', 
                    'title': help_text,
                    'data-placement': 'bottom',
                }
                self.fields[field].widget.attrs.update(extra)

