import logging

from django.utils.html import format_html

from django.db import models

logger = logging.getLogger(__name__)

class Thumbnail(models.Model):
    name = models.CharField(max_length = 64)
    imagecode = models.BinaryField(null=True, blank=True, editable=True)

    @property
    def img_src(self):
        import base64
        return f'data:image/png;base64,{base64.b64encode(self.imagecode).decode()}'

    @property
    def to_html(self):
        return format_html(f"<img alt='{self.name}' src='{self.img_src}'>")

    def __str__(self):
        return self.name
