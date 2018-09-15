from channels.auth import AuthMiddlewareStack
from django.contrib.auth.models import AnonymousUser, User
from rest_framework_jwt.authentication import jwt_decode_handler


class TokenAuthMiddleware:

    def __init__(self, inner):
        self.inner = inner

    def __call__(self, scope):
        headers = dict(scope['headers'])
        if b'authorization' in headers:
            try:
                user = jwt_decode_handler(headers[b'authorization'].decode())
                scope['user'] = User.objects.get_by_natural_key(user['username'])
            except User.DoesNotExist:
                scope['user'] = AnonymousUser()
        return self.inner(scope)


TokenAuthMiddlewareStack = lambda inner: TokenAuthMiddleware(AuthMiddlewareStack(inner))
