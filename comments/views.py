import django_filters
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models
from rest_framework import mixins, routers, serializers, viewsets
from rest_framework.viewsets import GenericViewSet

from comments.models import Comment, CommentsHistory, Post
from comments.tasks import export_comments_history

router = routers.DefaultRouter()
channel_layer = get_channel_layer()

_HTML_CUTOFF_TEXT = 'Limited records number are shown. You can use this form only for demo purpose.'


class UpdateModelMixin(mixins.UpdateModelMixin):
    def perform_update(self, serializer):
        super().perform_update(serializer)
        instance = serializer.instance
        ct = ContentType.objects.get_for_model(instance.__class__)
        async_to_sync(channel_layer.group_send)(f"{ct.pk}.{instance.pk}", {
            "type": "object.updated",
            "content_type": ct.pk,
            "object_id": instance.pk,
            "data": serializer.data
        })


class ContentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentType
        fields = ('id', 'url', 'app_label', 'model')


class ContentTypeFilter(django_filters.FilterSet):
    class Meta:
        model = ContentType
        fields = ('id', 'app_label', 'model')


class ContentTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ContentType.objects.filter(model__in=[Post._meta.model_name, User._meta.model_name])
    serializer_class = ContentTypeSerializer
    filter_class = ContentTypeFilter


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'url', 'username',)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class CommentSerializer(serializers.ModelSerializer):
    content_type = serializers.PrimaryKeyRelatedField(queryset=ContentTypeViewSet.queryset)
    parent = serializers.PrimaryKeyRelatedField(allow_null=True, queryset=Comment.objects.all(),
                                                html_cutoff_text=_HTML_CUTOFF_TEXT,
                                                html_cutoff=10)
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), html_cutoff_text=_HTML_CUTOFF_TEXT,
                                              html_cutoff=10)

    class Meta:
        model = Comment
        fields = ('id', 'url', 'user', 'text', 'created', 'parent', 'content_type', 'object_id', 'level')
        read_only_fields = ('created', 'level')

    def validate(self, data):
        """
        Check that the start is before the stop.
        """
        if data['parent']:
            if data['content_type'] != data['parent'].content_type:
                raise serializers.ValidationError({'content_type': 'Must be same with parent comment\'s content_type'})
            if data['object_id'] != data['parent'].object_id:
                raise serializers.ValidationError({'object_id': 'Must be same with parent comment\'s object_id'})
        model_cls: models.Model = data['content_type'].model_class()

        try:
            model_cls.objects.get(pk=data['object_id'])
        except model_cls.DoesNotExist as e:
            raise serializers.ValidationError({'object_id': f"Invalid pk \"{data['object_id']}\" - {e}"})

        return data


class CommentFilter(django_filters.FilterSet):
    is_root = django_filters.BooleanFilter(field_name='parent', lookup_expr='isnull', label='Is root')
    content_type = django_filters.ModelChoiceFilter(queryset=ContentTypeViewSet.queryset)
    parent = django_filters.NumberFilter()

    class Meta:
        model = Comment
        fields = ('content_type', 'parent', 'object_id', 'user', 'is_root')


class CommentViewSet(UpdateModelMixin, viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    filterset_class = CommentFilter

    def perform_destroy(self, instance):
        if instance.is_leaf_node():
            return super().perform_destroy(instance)
        raise serializers.ValidationError('Can not delete comment, comment has children.')

    def perform_update(self, serializer):
        if serializer.instance and serializer.instance.is_leaf_node():
            return super().perform_update(serializer)
        raise serializers.ValidationError('Can not update comment, comment has children.')


class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ('id', 'text', 'url')


class PostViewSet(UpdateModelMixin, viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer


class HistoryFileSerializer(serializers.ModelSerializer):
    content_type = serializers.PrimaryKeyRelatedField(queryset=ContentTypeViewSet.queryset)
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), html_cutoff_text=_HTML_CUTOFF_TEXT,
                                              html_cutoff=10)

    class Meta:
        model = CommentsHistory
        fields = ('id', 'url', 'user', 'created', 'content_type', 'object_id',
                  'date_from', 'date_to', 'format', 'file', 'status')
        read_only_fields = ('created', 'file', 'status')


class HistoryFileViewSet(mixins.CreateModelMixin,
                         mixins.RetrieveModelMixin,
                         GenericViewSet):
    queryset = CommentsHistory.objects.all()
    serializer_class = HistoryFileSerializer

    def perform_create(self, serializer: HistoryFileSerializer):
        instance = serializer.save()
        export_comments_history.delay(str(instance.id))


router.register(r'contenttypes', ContentTypeViewSet)
router.register(r'users', UserViewSet)
router.register(r'posts', PostViewSet)
router.register(r'comments', CommentViewSet)
router.register(r'comments_history', HistoryFileViewSet)
