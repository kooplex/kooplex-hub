from django.db import models


class NoteQuerySet(models.QuerySet):
    def active(self):
        return self.filter(
            expired=False
        )

    def visible_to(self, user):
        qs = self.active()

        if (
            user is not None
            and user.is_authenticated
        ):
            return qs

        return qs.filter(
            is_public=True
        )


class Note(models.Model):
    message = models.TextField(max_length = 1024, null = False)
    created_at = models.DateTimeField(auto_now_add = True)
    is_public = models.BooleanField(default = True)
    expired = models.BooleanField(default = False)

    objects = NoteQuerySet.as_manager()

    class Meta:
        ordering = (
            "-created_at",
            "-pk",
        )

