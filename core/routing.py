from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.conf.urls import url

from comments.consumers import ObjectUpdateConsumer
from core.channels_token_auth import TokenAuthMiddlewareStack

application = ProtocolTypeRouter({
    "websocket": AuthMiddlewareStack(TokenAuthMiddlewareStack(
        URLRouter([
            url(r"^object_updates$", ObjectUpdateConsumer),
        ])
    ))
})
