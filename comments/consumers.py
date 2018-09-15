from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from comments.models import Comment, Post


class CommonObjectSerializer(serializers.Serializer):
    SUBSCRIBE = 'subscribe'
    UNSUBSCRIBE = 'unsubscribe'

    content_type = serializers.ChoiceField([c.pk for c in ContentType.objects.filter(
        model__in=[Post._meta.model_name, User._meta.model_name, Comment._meta.model_name]
    )])
    object_id = serializers.IntegerField()
    action = serializers.ChoiceField([SUBSCRIBE, UNSUBSCRIBE])

    class Meta:
        fields = ('content_type', 'object_id')

    def validate(self, data):
        try:
            ct = ContentType.objects.get_for_id(data['content_type'])
            ct.get_object_for_this_type(pk=data['object_id'])
        except ObjectDoesNotExist as e:
            raise serializers.ValidationError(e)
        return data


class ObjectUpdateConsumer(JsonWebsocketConsumer):
    strict_ordering = True

    def websocket_connect(self, message, **kwargs):
        """
        Perform things on connection start
        """
        if self.scope["user"].is_anonymous:
            self.close()
        self.accept()

    def receive_json(self, content, **kwargs):
        """
        Called when a message is received with decoded JSON content
        """
        serializer = CommonObjectSerializer(data=content)
        if serializer.is_valid():
            ct, obj_id = serializer.data['content_type'], serializer.data['object_id']
            if serializer.data['action'] == serializer.SUBSCRIBE:
                action = async_to_sync(self.channel_layer.group_add)
            elif serializer.data['action'] == serializer.UNSUBSCRIBE:
                action = async_to_sync(self.channel_layer.group_discard)
            action(f'{ct}.{obj_id}', self.channel_name)
        else:
            self.send_json({'error': serializer.errors})

    def object_updated(self, event):
        self.send_json(event)
