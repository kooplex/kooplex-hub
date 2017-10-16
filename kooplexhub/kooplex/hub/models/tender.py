from django.db import models
from .user import HubUser

class Tender(models.Model):
    id = models.AutoField(primary_key = True)
    label = models.CharField(max_length = 15)

    def __str__(self):
        return str(self.label)


class UserTenderBinding(models.Model):
    id = models.AutoField(primary_key = True)
    user = models.ForeignKey(HubUser, null = False)
    tender = models.ForeignKey(Tender, null = False)

    def __str__(self):
       return "%s@%s" % (self.user, self.tender)
    
