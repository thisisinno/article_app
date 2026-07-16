from django.apps import AppConfig
class PublishingConfig(AppConfig):
    name = "publishing"
    def ready(self):
        from . import signals  # noqa: F401
