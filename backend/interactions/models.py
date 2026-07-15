import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q

class ActorModel(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
    visitor = models.ForeignKey("accounts.AnonymousVisitor", null=True, blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: abstract=True

class PostLike(ActorModel):
    post=models.ForeignKey("publishing.Post",on_delete=models.CASCADE,related_name="likes")
    class Meta: constraints=[models.UniqueConstraint(fields=("post","user"),condition=Q(user__isnull=False),name="unique_user_post_like"),models.UniqueConstraint(fields=("post","visitor"),condition=Q(visitor__isnull=False),name="unique_visitor_post_like"),models.CheckConstraint(condition=Q(user__isnull=False,visitor__isnull=True)|Q(user__isnull=True,visitor__isnull=False),name="post_like_one_actor")]
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
class CategoryFollow(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE); category=models.ForeignKey("publishing.Category",on_delete=models.CASCADE,related_name="followers"); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: constraints=[models.UniqueConstraint(fields=("user","category"),name="unique_category_follow")]
class Notification(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False); recipient=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="notifications"); actor=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL); kind=models.CharField(max_length=20); post=models.ForeignKey("publishing.Post",null=True,blank=True,on_delete=models.CASCADE); text=models.CharField(max_length=240,blank=True); read_at=models.DateTimeField(null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True)
class ContentReport(ActorModel):
    post=models.ForeignKey("publishing.Post",null=True,blank=True,on_delete=models.CASCADE); comment=models.ForeignKey("publishing.Comment",null=True,blank=True,on_delete=models.CASCADE); reason=models.CharField(max_length=100); notes=models.TextField(blank=True); status=models.CharField(max_length=12,default="open")
