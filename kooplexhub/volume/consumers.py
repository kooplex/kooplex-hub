import logging
import json
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string

from hub.util import AsyncSkeleton
from asgiref.sync import sync_to_async

from .models import Volume, UserVolumeBinding
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class VolumeConfigHandler:
    def __init__(self, instance, user):
        self.instance = instance
        self.user = user
        self.attribute_handlers = {
            'description': (False, self.handle_description_update),
            'scope': (False, self.handle_scope_update),
        }

    def handle_attribute(self, attribute_name, new_value):
        pass_attribute, handler = self.attribute_handlers.get(attribute_name)
        if handler and pass_attribute:
            return handler(attribute_name, new_value)
        elif handler:
            return handler(new_value)
        else:
            logger.critical(f"No handler for container configuration attribute: {attribute_name}")

    def handle_description_update(self, new_value):
        from .templatetags.volume_tags import render_description
        old_value = self.instance.description
        self.instance.description = new_value
        try:
            self.instance.full_clean()
            self.instance.save()
            return f"description changed from {old_value} to {new_value}", {f"[data-name=description][data-pk={self.instance.pk}][data-model=volume]": render_description(self.instance, self.user)}
        except ValidationError as e:
            self.instance.description = old_value
            return str(e), {f"[data-name=description][data-pk={self.instance.pk}][data-model=volume]": render_description(self.instance, self.user)}

    def handle_scope_update(self, new_value):
        from .templatetags.volume_tags import render_scope
        old_value = self.instance.scope
        self.instance.scope = new_value
        self.instance._user=self.user
        self.instance.save()
        return f"scope changed from {old_value} to {new_value}", {f"[data-name=scope][data-pk={self.instance.pk}][data-model=volume]": render_scope(self.instance, self.user)}


class VolumeConfigConsumer(AsyncSkeleton):
    identifier_ = "volume"

    async def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.critical(self.identifier)
        logger.debug(parsed)
        pk=parsed.get('pk')
        uid=parsed.get('userid')
        changes=parsed.get('changes')
        assert parsed.get('request')=='configure-volume' and uid==self.userid
        _f = await sync_to_async(Volume.objects.filter)(pk=pk, userbindings__user__pk=uid, userbindings__role__in=[UserVolumeBinding.Role.OWNER, UserVolumeBinding.Role.ADMIN])
        volume = await sync_to_async(_f.first)()
        user=await sync_to_async(User.objects.get)(pk=self.userid)
        configurator = await sync_to_async(VolumeConfigHandler)(volume, user)
        widgets={}
        messages=[]
        for field, new_value in changes.items():
            m, w = await sync_to_async(configurator.handle_attribute)(field, new_value)
            messages.append(m)
            widgets.update(w)
        if messages:
            await self.send(text_data=json.dumps({
                'feedback': f"Volume {volume.folder} is configured: " + ",".join(messages) + ".",
                'replace_widgets': widgets,
            }))

