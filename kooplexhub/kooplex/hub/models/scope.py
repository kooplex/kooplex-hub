from django.db import models


class ScopeType(models.Model):
    id = models.AutoField(primary_key = True)
    name = models.CharField(max_length = 32)


def init_model():
    scopetypes = [ 'private', 'internal', 'public' ]
    for st in scopetypes:
        sti = ScopeType.objects.get(name = st)
        if sti is None:
            sti = ScopeType(name = rt)
            sti.save()

