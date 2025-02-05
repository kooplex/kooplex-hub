import logging
import unidecode

from django.contrib.auth.models import User

from django.db import models

logger = logging.getLogger(__name__)

#TODO accommodate Canvas and other tokens as well

class TokenType(models.Model):  
    name = models.CharField(max_length = 64, null = False)
    description = models.CharField(max_length = 512, null = True)
    base_url = models.CharField(max_length = 64, null = False)
    #service = models.ForeignKey('Service', on_delete = models.CASCADE, null = False)

    def __str__(self):
        return self.name

class Token(models.Model):  
    user = models.ForeignKey(User, on_delete = models.CASCADE, null = False)
    #name = models.CharField(max_length = 64, null = True) # unique?
    type = models.ForeignKey(TokenType, on_delete = models.CASCADE)
    value = models.CharField(max_length = 1024, null = True)

    def __str__(self):
        return f"type: {self.type}, value: {self.value}"















