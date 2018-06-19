#FIXME: enum
from django.db import models

class ScopeType(models.Model):
    name = models.CharField(max_length = 32)

    def __str__(self):
        return self.name
        
def get_scope(scope):
    try:
        return ScopeType.objects.get(name = scope)
    except ScopeType.DoesNotExist:
        return ScopeType.objects.create(name = scope)

