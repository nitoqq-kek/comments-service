import enum
import uuid

from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import TemporaryUploadedFile
from django.db import models
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel
from rest_framework import serializers as rest_serializers

from comments.export import Format, iterdump
from core.utils import OverwriteStorage


class Comment(MPTTModel):
    user = models.ForeignKey(User, models.CASCADE, related_name='comments')
    text = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    parent = TreeForeignKey('self', on_delete=models.PROTECT, null=True, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    class MPTTMeta:
        order_insertion_by = ['created']

    def __str__(self):
        return f'{self.content_object} | {self.text}'


class Post(models.Model):
    text = models.TextField()
    comments = GenericRelation(Comment)


class HistoryExportSerializer(rest_serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = read_only_fields = ('id', 'user', 'text', 'created', 'parent', 'content_type', 'object_id', 'level')


class Status(enum.IntEnum):
    new = 1
    pending = 2
    success = 3
    error = 4


class CommentsHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to='export', storage=OverwriteStorage())
    status = models.PositiveIntegerField(choices=[(i.value, i) for i in Status], default=Status.new, db_index=True)
    user = models.ForeignKey(User, models.CASCADE, related_name='history_files')
    created = models.DateTimeField(auto_now_add=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    date_from = models.DateTimeField(null=True, blank=True)
    date_to = models.DateTimeField(null=True, blank=True)
    format = models.CharField(max_length=10, choices=[(i.value, i) for i in Format])

    def get_comments(self):
        comments = Comment.objects.filter(user=self.user, content_type=self.content_type, object_id=self.object_id)
        if self.date_from:
            comments = comments.filter(created__gte=self.date_from)
        if self.date_to:
            comments = comments.filter(created__lte=self.date_to)
        return comments

    def serialized_comments(self):
        for c in self.get_comments():
            yield HistoryExportSerializer(c).data

    def export(self):
        self.status = Status.pending
        self.save()
        try:
            with TemporaryUploadedFile(f'{self.id}.{self.format}',
                                       content_type=f'application/{self.format}',
                                       size=0, charset='utf-8') as tmp:
                iterdump(self.format, tmp, self.serialized_comments())
                self.file = tmp
                self.status = Status.success
                self.save()
        except Exception:
            self.status = Status.error
            self.save()
            raise
