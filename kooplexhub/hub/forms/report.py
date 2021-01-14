from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.db import models

from hub.models import Report, Image, Report

class FormReport(forms.Form):
    name = forms.CharField(help_text = _('Report name should be unique.'), required = True)
    description = forms.CharField(max_length = 100, help_text = _('It is always a good idea to have a short memo of your report.'), widget = forms.Textarea, required = True)
    image = forms.ModelChoiceField(queryset = Image.objects.filter(~models.Q(imagetype = Image.TP_PROJECT)), help_text = _('Please select an image to serve your report.'), required = True)
    password = forms.CharField(help_text = _('Leave it empty for the public.'), required = False)
    scope = forms.ChoiceField(choices = Report.SC_LOOKUP.items(), help_text = _('Select the scope of the project'), required = True)

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
                    indices += f'<div class="p-2 bg-light border">{r}{icon_index}{i}</div>'
                sub_folders += f"""
<div class="p-1 bg-light border">
  <button class="btn btn-secondary-light btn-sm" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-{p.id}-{f}" aria-expanded="false" aria-controls="collapse-{p.id}-{f}">
    {icon_folder} {f}
  </button>
  <div class="collapse" id="collapse-{p.id}-{f}">
    <div class="d-grid">
      {indices}
    </div>
  </div>
</div>
                """
            tree += f"""
<div class="p-1 bg-light border">
  <button class="btn btn-secondary-light btn-sm" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-{p.id}" aria-expanded="false" aria-controls="collapse-{p.id}">
    {icon_project} {p.name}
  </button><br>
  <div class="collapse" id="collapse-{p.id}">
    <div class="d-grid">
      {sub_folders}
    </div>
  </div>
</div>
            """
        html = f'<tr><td style="vertical-align: top;"><b>Select index:</b></td><td><div id="indextree" class="bstreeview">{tree}</div></td></tr>'
        return format_html(html)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(FormReport, self).__init__(*args, **kwargs)
        self.fields['description'].widget.attrs.update({ 'rows': 3, 'cols': 30 })
        self.tree = user.profile.files_reportprepare()
        for field in self.fields:
            help_text = self.fields[field].help_text
            self.fields[field].help_text = None
            self.fields[field].widget.attrs["class"] = "form-control"
            if help_text != '':
                extra = {
                    'data-toggle': 'tooltip', 
                    'title': help_text,
                    'data-placement': 'bottom',
                }
                self.fields[field].widget.attrs.update(extra)

