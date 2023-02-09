from django import forms

from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from ..models import Report, ReportType
from container.models import Image
from project.models import UserProjectBinding
from django.contrib.auth.models import User
from taggit.models import Tag
from hub.models import Thumbnail

from ..filesystem import dir_reportcandidate
from kooplexhub.common import tooltip_attrs


class FormReport(forms.ModelForm):
    class Meta:
        model = Report
        fields = [ 'name', 'description', 'scope', 'reporttype','image', 'indexfile' ]

    user_id = forms.CharField(widget = forms.HiddenInput(), required = True)
    report_id = forms.CharField(widget = forms.HiddenInput(), required = False)
    name = forms.CharField(
        label = _("Report name"),
        max_length = 200, required = True, 
        widget = forms.TextInput(attrs = tooltip_attrs({ 'title': _('Name your report. No worries later you can rename it.') })),
    )
    indexfile = forms.ChoiceField(
        label = _("Report file"), required = True,
        widget = forms.Select(attrs = tooltip_attrs({
            'title': _('This is the entry of your report.'), 
        })),
    )
    description = forms.CharField(
        max_length = 300, required = True,
        widget = forms.Textarea(attrs = tooltip_attrs({
            'rows': 3, 
            'title': _('It is always a good idea to have a short but straight to the point abstract of your report.'), 
        })),
    )
    scope = forms.ChoiceField(
        choices = Report.SCOPE_LOOKUP.items(), required = True,
        widget = forms.Select(attrs = tooltip_attrs({ 'title': _('Select the scope of the report.') }))
    )
    reporttype = forms.ModelChoiceField(
        queryset = ReportType.objects.all(), required = True,
        widget = forms.Select(attrs = tooltip_attrs({ 'title': _('Select the report type.') }))
    )
    image = forms.ModelChoiceField(
        label = _('Image'),
        queryset = Image.objects.filter(imagetype = Image.TP_REPORT, present = True), 
        required = False, empty_label = 'Select image...',
        widget = forms.Select(attrs = tooltip_attrs({ 'title': _('Select an image if you prefer an environment to be created.') })),
    )
    thumbnail = forms.FileField(
        widget = forms.ClearableFileInput(attrs = tooltip_attrs({ 'title': _('Select and upload a thumbnail image to catch eye to your report.') })),
    )
    def descriptions(self):
        hidden = lambda i: f"""
<input type="hidden" id="image-description-{i.id}" value="{i.description}">
<input type="hidden" id="image-thumbnail-{i.id}" value="{i.thumbnail.img_src}">
        """
        return format_html("".join(list(map(hidden, self.fields['image'].queryset))))

    #tags = forms.ModelChoiceField(
    #    required=False, empty_label = _('Add some tags...'),
    #    queryset = Tag.objects.all(),
    #    widget = forms.Select(attrs = tooltip_attrs({ 
    #        'class': "form-select mytag", 'multiple': True, 
    #        'data-allow-new': "true", 'data-separator': " |,|\t", 
    #    }))
    #)

    def __init__(self, *args, **kwargs):
        user = kwargs['initial'].get('user')
        super(FormReport, self).__init__(*args, **kwargs)
        report = kwargs.get('instance', Report())
        qs = []
        if report.id:
            for folder in dir_reportcandidate(report.project):
                if folder.startswith(report.folder):
                    qs.append((f'{report.project.id}-{folder}', f'{report.project.name}: {folder}'))
            #FIXME: select the former indexfile
            #FIXME: frissítésnél ne legyen required True
            self.fields['thumbnail'].required = False
        else:
            for upb in UserProjectBinding.objects.filter(user = user):
                for folder in dir_reportcandidate(upb.project):
                    qs.append((f'{upb.project.id}-{folder}', f'{upb.project.name}: {folder}'))
        self.fields["user_id"].widget.attrs['value'] = user.id
        self.fields["report_id"].widget.attrs['value'] = report.id
        self.fields["indexfile"].choices = qs
        #self.fields["tags"].widget.attrs.update({"data-role" : "tagsinput"})
        self.okay = len(qs) > 0

    def clean(self):
        cleaned_data = super().clean()
        user_id = cleaned_data.pop('user_id')
        reportname = cleaned_data.get('name')
        project_id, rest = cleaned_data['indexfile'].split('-', 1)
        folder, index = rest.split('/', 1)
        upb = UserProjectBinding.objects.filter(user__id = user_id, project__id = project_id)
        # FIXME: ellenőrizni a létezést
        ve = []
        if not reportname:
            ve.append( forms.ValidationError(_(f'Report name cannot be empty'), code = 'invalid projectname') )
        if not len(upb) == 1:
            ve.append( forms.ValidationError(_(f'User is not authorized to access this project'), code = 'access denied') )
        if ve:
            raise forms.ValidationError(ve)
        cleaned_data['indexfile'] = index
        cleaned_data['folder'] = folder
        cleaned_data['project'] = upb[0].project
        cleaned_data['report_id'] = None if cleaned_data['report_id'] == 'None' else cleaned_data['report_id']
        cleaned_data['creator'] = User.objects.get(id = user_id)
        tn = cleaned_data.pop('thumbnail')
        if hasattr(tn, 'chunks'):
            cleaned_data['thumbnail'] = Thumbnail.objects.create(name = f'tn-{reportname}-{tn.name}', imagecode = b''.join([ c for c in tn.chunks() ]))
        return cleaned_data
