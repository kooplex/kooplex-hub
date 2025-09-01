import logging
import json
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string

from channels.generic.websocket import WebsocketConsumer

from hub.util import Config
from .models import Volume, UserVolumeBinding

logger = logging.getLogger(__name__)


class SyncConsumer(WebsocketConsumer):
    def connect(self):
        if not self.scope['user'].is_authenticated:
            return
        self.accept()
        self.userid = int(self.scope["url_route"]["kwargs"].get('userid'))
        assert self.scope['user'].id == self.userid, "not authorized"

    def disconnect(self, close_code):
        pass


class VolumeConfigConsumer(SyncConsumer, Config):
    template='volume/card.html'
    instance_reference='volume'

    def receive(self, text_data):
        from kooplexhub.lib.libbase import standardize_str
        parsed = json.loads(text_data)
        logger.debug(parsed)
        pk=parsed.get('pk')
        attr=parsed.get('name')
        value=parsed.get('value')
        uid=parsed.get('userId')
        if parsed.get('request')=='config-volume' and uid==self.userid:
            volume = Volume.objects.filter(pk=pk, userbindings__user__pk=uid, userbindings__role__in=[UserVolumeBinding.Role.OWNER, UserVolumeBinding.Role.ADMIN]).first()
            if volume and hasattr(volume, attr) and value:
                old=getattr(volume, attr)
                setattr(volume, attr, value)
                try: 
                    volume.full_clean(validate_unique=True)
                    self._msg(volume, f"Volume attribute {attr} changed from {old} to {value}")
                    volume.save()
                except ValidationError as e:
                    logger.error(e)
                    self._msg(volume, f"Problem configuring volume {volume.folder}", errors={'attr': {'error': str(e), 'value': old }})


