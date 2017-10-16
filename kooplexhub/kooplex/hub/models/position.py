from django.db import models

class Position(models.Model):
    id = models.AutoField(primary_key = True)
    label = models.CharField(max_length = 15)

    def __str__(self):
        return str(self.label)

