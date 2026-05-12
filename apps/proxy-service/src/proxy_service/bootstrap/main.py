"""ASGI entrypoint for the proxy service."""

from proxy_service.bootstrap.app import create_app

app = create_app()
