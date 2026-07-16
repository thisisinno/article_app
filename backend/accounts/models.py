import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import F, Q

class User(AbstractUser):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=80)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    avatar = models.ImageField(upload_to="avatars/", blank=True)
    cover_image = models.ImageField(upload_to="covers/", blank=True)
    bio = models.CharField(max_length=300, blank=True)
    website = models.URLField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    verified = models.BooleanField(default=False)

class AnonymousVisitor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name="following_links")
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name="follower_links")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=("follower", "following"), name="unique_follow"), models.CheckConstraint(check=~Q(follower=F("following")), name="no_self_follow")]
