from pwd import getpwnam
import logging
import unidecode


from django.db import models
from django.contrib.auth.models import User
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete = models.CASCADE)
    token = models.CharField(max_length = 64, null = True)
    can_createproject = models.BooleanField(default = True)
    can_createimage = models.BooleanField(default = False)
    can_createattachment = models.BooleanField(default = False)
    can_createcourse = models.BooleanField(default = False)
    can_runjob = models.BooleanField(default = False)
    can_choosenode = models.BooleanField(default = False)
    can_teleport = models.BooleanField(default = False)
    has_scratch = models.BooleanField(default = False)

    @property
    def userid(self):
        if hasattr(self.user, 'is_superuser') and (self.user.is_superuser == True):
            return None
        return getpwnam(self.username).pw_uid

    @property
    def search(self):
        return f"{self.user.username}{self.user.first_name}{self.user.last_name}{self.user.first_name}".lower().replace(' ', '')

    #FIXME: delete
    @property
    def name(self):
        return '{} {}'.format(self.user.first_name, self.user.last_name)

    @property
    def username(self):
        return self.user.username

    #FIXME: delete
    @property
    def name_and_username(self):
        return f'{self.name} ({self.username})'

    #FIXME: delete
    @property
    def safename(self):
        return "%s_%s" % (unidecode.unidecode(self.user.last_name), unidecode.unidecode(self.user.first_name).replace(' ', ''))

    @property
    def everybodyelse(self):
        return Profile.objects.filter(~models.Q(id = self.id) & ~models.Q(user__is_superuser = True))

    def everybodyelse_like(self, pattern):
        return Profile.objects.filter(~models.Q(id = self.id) & ~models.Q(user__is_superuser = True) & (models.Q(user__username__icontains = pattern) | models.Q(user__first_name__icontains = pattern) | models.Q(user__last_name__icontains = pattern)))

    #FIXME: return queryset?
    @property
    def projectbindings(self):
        from project.models import UserProjectBinding
        for binding in UserProjectBinding.objects.filter(user = self.user):
            yield binding

    @property
    def number_of_hidden_projects(self):
        return len(list(filter(lambda x: x.is_hidden, self.projectbindings)))

    #FIXME: return queryset?
    @property
    def containers(self):
        from .container import Container
        for svc in Container.objects.filter(user = self.user):
             yield svc

    @property
    def reports(self):
        from .report import Report
        from hub.forms import T_REPORTS, T_REPORTS_DEL
        reports_shown = set()
        for report in Report.objects.all():#FIXME: filter those you can see
             if report in reports_shown:
                 continue
             g = report.groupby()
             T = T_REPORTS_DEL(g) if self.user == report.creator else T_REPORTS(g)
             yield report.latest, T, report.subcategory_name
             reports_shown.update(set(g))

    #FIXME: delete?
    def usercoursebindings(self, **kw):
        from education.models import UserCourseBinding
        return UserCourseBinding.objects.filter(user = self.user, **kw)

    @property
    def is_teacher(self):
        return len(self.usercoursebindings(is_teacher = True)) > 0

    #FIXME: map()
    def courses_taught(self):
        return [ binding.course for binding in self.usercoursebindings(is_teacher = True) ]

    @property
    def is_student(self):
        return len(self.usercoursebindings(is_teacher = False)) > 0

    #FIXME: map()
    def courses_attend(self):
        return [ binding.course for binding in self.usercoursebindings(is_teacher = False) ]

    @property
    def _repr(self):
        return { self.user.pk: {
            'name_and_username': self.name_and_username,
            'search': self.search,
        } }


    #FIXME: return queryset?
    @property
    def vctokens(self):
        from .versioncontrol import VCToken
        for t in VCToken.objects.filter(user = self.user):
            yield t

    #FIXME: return queryset?
    @property
    def fstokens(self):
        from .filesync import FSToken
        for t in FSToken.objects.filter(user = self.user):
            yield t


    # rendering logic
    def render_html(self):
        return render_to_string("widgets/user.html", {"user": self.user})
