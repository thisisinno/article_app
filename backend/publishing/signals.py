from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Post

@receiver(post_save, sender=Post)
def published_post_notifications(sender, instance, raw=False, **kwargs):
    if raw or instance.status != Post.Status.PUBLISHED or instance.published_notification_sent_at:
        return
    from interactions.notifications import notify_new_post
    transaction.on_commit(lambda: notify_new_post(instance))
