import json
from django.conf import settings
from django.utils import timezone
from pywebpush import WebPushException,webpush
from .models import WebPushSubscription

def notification_url(notification):
    if not notification.post_id:return "/notifications"
    if notification.comment_id:return f"/post/{notification.post_id}?comments=1&comment={notification.comment_id}"
    return f"/post/{notification.post_id}"

def payload_for(notification):
    bodies={"new_post":"A new post was published","post_comment":"Someone commented on your post","comment_reply":"Someone replied to your comment","comment_like":"Someone liked your comment","post_like":"Someone liked your post","post_share":"Someone shared your post"}
    return {"notification_id":str(notification.pk),"title":"Jesca Social Work","body":bodies.get(notification.kind,"You have a new notification"),"icon":"/icon-192.png","badge":"/icon-192.png","tag":f"notification:{notification.pk}","url":notification_url(notification),"kind":notification.kind}

def send_subscription(subscription,payload):
    return webpush(subscription_info={"endpoint":subscription.endpoint,"keys":{"p256dh":subscription.p256dh,"auth":subscription.auth}},data=json.dumps(payload,separators=(",",":")),vapid_private_key=settings.VAPID_PRIVATE_KEY,vapid_claims={"sub":settings.VAPID_SUBJECT},ttl=3600)

def deliver_notification(notification):
    if not settings.WEB_PUSH_ENABLED or not settings.VAPID_PRIVATE_KEY:return "disabled",False
    success=False
    for subscription in notification.recipient.push_subscriptions.filter(active=True):
        try:
            send_subscription(subscription,payload_for(notification));success=True
            WebPushSubscription.objects.filter(pk=subscription.pk).update(failure_count=0,last_success_at=timezone.now())
        except WebPushException as exc:
            status=getattr(getattr(exc,"response",None),"status_code",None)
            updates={"failure_count":subscription.failure_count+1,"last_failure_at":timezone.now()}
            if status in (404,410):updates["active"]=False
            WebPushSubscription.objects.filter(pk=subscription.pk).update(**updates)
            if status not in (400,404,410,413):raise
    return "sent" if success else "no_active_subscription",success
