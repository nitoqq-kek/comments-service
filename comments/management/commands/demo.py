from django.contrib.auth.models import User
from django.core.management import BaseCommand

from comments.models import Post, Comment

import logging

log = logging.getLogger(__name__)

class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            User.objects.get(username='admin')
        except User.DoesNotExist:
            user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='qq'
            )

            p = Post.objects.create(text='post 1')
            for i in range(10):
                c = Comment.objects.create(user=user, text=f'Comment number {i}', content_object=p)
                Comment.objects.create(user=user, text=f'Child comment number {i}', content_object=p, parent=c)
            log.info('Demo data created')

