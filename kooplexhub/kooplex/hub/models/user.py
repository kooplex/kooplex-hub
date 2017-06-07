from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    id = models.IntegerField(null=True)

    def update_id(self, id):
        self.id = id
