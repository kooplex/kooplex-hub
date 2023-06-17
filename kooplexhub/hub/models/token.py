import logging
import unidecode

from django.db import models
#from django.contrib.auth.models import User
#from hub.models.service import Service

logger = logging.getLogger(__name__)

class Token(models.Model):  
    #user = models.ForeignKey(User, on_delete = models.CASCADE)
    #name = models.CharField(max_length = 64, null = True) # unique?
    #type = models.ForeignKey(Service, on_delete = models.CASCADE)
    value = models.CharField(max_length = 512, null = True)















