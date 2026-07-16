import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

class ActorModel(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
    visitor = models.ForeignKey("accounts.AnonymousVisitor", null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: abstract=True

class PostLike(ActorModel):
    post=models.ForeignKey("publishing.Post",on_delete=models.CASCADE,related_name="likes")
    class Meta: constraints=[models.UniqueConstraint(fields=("post","user"),condition=Q(user__isnull=False),name="unique_user_post_like"),models.UniqueConstraint(fields=("post","visitor"),condition=Q(visitor__isnull=False),name="unique_visitor_post_like"),models.CheckConstraint(check=Q(user__isnull=False,visitor__isnull=True)|Q(user__isnull=True,visitor__isnull=False),name="post_like_one_actor")]
class PostBookmark(ActorModel):
    post=models.ForeignKey("publishing.Post",on_delete=models.CASCADE,related_name="bookmarks")
    class Meta: constraints=[models.UniqueConstraint(fields=("post","user"),condition=Q(user__isnull=False),name="unique_user_bookmark"),models.UniqueConstraint(fields=("post","visitor"),condition=Q(visitor__isnull=False),name="unique_visitor_bookmark")]
class PostView(ActorModel):
    post=models.ForeignKey("publishing.Post",on_delete=models.CASCADE,related_name="views"); window_key=models.DateField()
    class Meta: constraints=[models.UniqueConstraint(fields=("post","user","window_key"),condition=Q(user__isnull=False),name="unique_user_view_window"),models.UniqueConstraint(fields=("post","visitor","window_key"),condition=Q(visitor__isnull=False),name="unique_visitor_view_window")]
class PostShare(ActorModel):
    post=models.ForeignKey("publishing.Post",on_delete=models.CASCADE,related_name="shares"); channel=models.CharField(max_length=20,default="copy")
class Repost(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE); post=models.ForeignKey("publishing.Post",on_delete=models.CASCADE,related_name="reposts"); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: constraints=[models.UniqueConstraint(fields=("user","post"),name="unique_repost")]
class CommentLike(ActorModel):
    comment=models.ForeignKey("publishing.Comment",on_delete=models.CASCADE,related_name="likes")
    class Meta: constraints=[models.UniqueConstraint(fields=("comment","user"),condition=Q(user__isnull=False),name="unique_user_comment_like"),models.UniqueConstraint(fields=("comment","visitor"),condition=Q(visitor__isnull=False),name="unique_visitor_comment_like"),models.CheckConstraint(check=Q(user__isnull=False,visitor__isnull=True)|Q(user__isnull=True,visitor__isnull=False),name="comment_like_one_actor")]
class CategoryFollow(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE); category=models.ForeignKey("publishing.Category",on_delete=models.CASCADE,related_name="followers"); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: constraints=[models.UniqueConstraint(fields=("user","category"),name="unique_category_follow")]
class Notification(models.Model):
    class Kind(models.TextChoices):
        NEW_POST="new_post","New post"; POST_LIKE="post_like","Post like"; POST_COMMENT="post_comment","Post comment"; COMMENT_REPLY="comment_reply","Comment reply"; COMMENT_LIKE="comment_like","Comment like"; POST_SHARE="post_share","Post share"
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); recipient=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="notifications"); actor=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL); kind=models.CharField(max_length=20,choices=Kind.choices); post=models.ForeignKey("publishing.Post",null=True,blank=True,on_delete=models.CASCADE); comment=models.ForeignKey("publishing.Comment",null=True,blank=True,on_delete=models.CASCADE); text=models.CharField(max_length=240,blank=True); read_at=models.DateTimeField(null=True,blank=True); dedupe_key=models.CharField(max_length=180,null=True,blank=True,unique=True); created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=("-created_at",)
        indexes=[models.Index(fields=("recipient","read_at","created_at")),models.Index(fields=("recipient","created_at"))]
class ContentReport(ActorModel):
    post=models.ForeignKey("publishing.Post",null=True,blank=True,on_delete=models.CASCADE); comment=models.ForeignKey("publishing.Comment",null=True,blank=True,on_delete=models.CASCADE); reason=models.CharField(max_length=100); notes=models.TextField(blank=True); status=models.CharField(max_length=12,default="open")

class WebPushSubscription(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="push_subscriptions")
    endpoint=models.URLField(unique=True,max_length=1000);p256dh=models.TextField();auth=models.TextField()
    expiration_time=models.BigIntegerField(null=True,blank=True);user_agent=models.CharField(max_length=300,blank=True)
    active=models.BooleanField(default=True);failure_count=models.PositiveSmallIntegerField(default=0)
    last_success_at=models.DateTimeField(null=True,blank=True);last_failure_at=models.DateTimeField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True);updated_at=models.DateTimeField(auto_now=True)
    class Meta:indexes=[models.Index(fields=("user","active")),models.Index(fields=("updated_at",))]

class PushDelivery(models.Model):
    class Status(models.TextChoices):PENDING="pending","Pending";PROCESSING="processing","Processing";SENT="sent","Sent";FAILED="failed","Failed";DISCARDED="discarded","Discarded"
    notification=models.OneToOneField(Notification,on_delete=models.CASCADE,related_name="push_delivery")
    status=models.CharField(max_length=12,choices=Status.choices,default=Status.PENDING,db_index=True)
    attempts=models.PositiveSmallIntegerField(default=0);next_attempt_at=models.DateTimeField(default=timezone.now,db_index=True)
    sent_at=models.DateTimeField(null=True,blank=True);last_error_code=models.CharField(max_length=80,blank=True);created_at=models.DateTimeField(auto_now_add=True)
