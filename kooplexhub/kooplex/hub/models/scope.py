from django.db import models

class ScopeType(models.Model):
    id = models.AutoField(primary_key = True)
    name = models.CharField(max_length = 32)

    def __str__(self):
        return self.name
        
def init_model():
    scopetypes = [ 'private', 'internal', 'public' ]
    for st in scopetypes:
        try:
            ScopeType.objects.get(name = st)
        except ScopeType.DoesNotExist:
            ScopeType(name = st).save()

