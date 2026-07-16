from django.db import transaction
from django.utils import timezone
from accounts.models import User
from publishing.models import Post
from .models import Notification,PushDelivery

TEXT = {
    "new_post": "published a new post",
    "post_like": "liked your post",
    "post_comment": "commented on your post",
    "comment_reply": "replied to your comment",
    "comment_like": "liked your comment",
    "post_share": "shared your post",
    "post_quote": "quoted your post",
}

def _create(recipient, kind, post, *, actor=None, comment=None, key):
    if actor and recipient.pk == actor.pk:
        return None
    item, created = Notification.objects.get_or_create(
        dedupe_key=key,
        defaults={"recipient": recipient, "actor": actor, "kind": kind, "post": post, "comment": comment, "text": TEXT[kind]},
    )
    if created:transaction.on_commit(lambda:PushDelivery.objects.get_or_create(notification=item))
    return item

@transaction.atomic
def notify_new_post(post):
    locked = Post.objects.select_for_update().get(pk=post.pk)
    if locked.status != Post.Status.PUBLISHED or locked.published_notification_sent_at:
        return 0
    recipients = User.objects.filter(is_active=True).exclude(pk=locked.author_id).values_list("pk", flat=True)
    rows = [Notification(recipient_id=pk, actor=locked.author, kind="new_post", post=locked, text=TEXT["new_post"], dedupe_key=f"new_post:{locked.pk}:{pk}") for pk in recipients]
    Notification.objects.bulk_create(rows, ignore_conflicts=True)
    ids=Notification.objects.filter(dedupe_key__in=[x.dedupe_key for x in rows]).values_list("id",flat=True)
    PushDelivery.objects.bulk_create([PushDelivery(notification_id=pk) for pk in ids],ignore_conflicts=True)
    locked.published_notification_sent_at = timezone.now()
    locked.save(update_fields=("published_notification_sent_at",))
    return len(rows)

def notify_post_like(post, actor_user=None, actor_visitor=None):
    return _create(post.author, "post_like", post, actor=actor_user, key=f"post_like:{post.pk}:{actor_user.pk if actor_user else 'reader'}")

def notify_post_comment(comment):
    return _create(comment.post.author, "post_comment", comment.post, actor=comment.author, comment=comment, key=f"post_comment:{comment.pk}:{comment.post.author_id}")

def notify_comment_reply(reply):
    recipients = []
    if reply.parent and reply.parent.author_id:
        recipients.append(reply.parent.author)
    if reply.post.author_id not in {u.pk for u in recipients}:
        recipients.append(reply.post.author)
    return [_create(u, "comment_reply", reply.post, actor=reply.author, comment=reply, key=f"comment_reply:{reply.pk}:{u.pk}") for u in recipients]

def notify_comment_like(comment, actor_user=None, actor_visitor=None):
    if not comment.author_id:
        return None
    return _create(comment.author, "comment_like", comment.post, actor=actor_user, comment=comment, key=f"comment_like:{comment.pk}:{actor_user.pk if actor_user else 'reader'}")

def notify_post_share(post, actor_user=None, actor_visitor=None):
    return _create(post.author, "post_share", post, actor=actor_user, key=f"post_share:{post.pk}:{actor_user.pk if actor_user else 'reader'}")

def notify_post_quote(original, quote):
    return _create(original.author,"post_quote",quote,actor=quote.author,key=f"post_quote:{quote.pk}:{original.author_id}")
