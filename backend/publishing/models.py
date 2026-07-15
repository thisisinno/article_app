import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q

class Category(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(unique=True)
    description = models.CharField(max_length=240, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    def __str__(self): return self.name

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    def __str__(self): return self.name

class Post(models.Model):
    class Type(models.TextChoices): SHORT="short", "Short"; ARTICLE="article", "Article"
    class Status(models.TextChoices): DRAFT="draft", "Draft"; SCHEDULED="scheduled", "Scheduled"; PUBLISHED="published", "Published"; ARCHIVED="archived", "Archived"; REMOVED="removed", "Removed"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts")
    post_type = models.CharField(max_length=10, choices=Type.choices, default=Type.SHORT)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PUBLISHED, db_index=True)
    title = models.CharField(max_length=240, blank=True)
    body = models.TextField(max_length=30000)
    excerpt = models.CharField(max_length=400, blank=True)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="posts")
    tags = models.ManyToManyField(Tag, blank=True)
    cover_image = models.ImageField(upload_to="posts/", blank=True)
    allow_comments = models.BooleanField(default=True)
    sensitive = models.BooleanField(default=False)
    pinned = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)
    quoted_post = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="quotes")
    repost_source = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="repost_posts")
    thread_root = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="thread_entries")
    thread_position = models.PositiveSmallIntegerField(null=True, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    removed_at = models.DateTimeField(null=True, blank=True)
    view_count = models.PositiveIntegerField(default=0); like_count = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0); repost_count = models.PositiveIntegerField(default=0)
    bookmark_count = models.PositiveIntegerField(default=0); share_count = models.PositiveIntegerField(default=0)
    class Meta:
        ordering = ("-pinned", "-published_at", "-created_at")
        indexes = [models.Index(fields=("status", "published_at")), models.Index(fields=("category", "published_at")), models.Index(fields=("author", "published_at")), models.Index(fields=("thread_root", "thread_position"))]
        constraints = [models.CheckConstraint(condition=Q(post_type="short") | ~Q(title=""), name="article_requires_title")]
    def __str__(self): return self.title or self.body[:60]

class Media(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="media")
    file = models.FileField(upload_to="posts/media/")
    media_type = models.CharField(max_length=16, default="image")
    alt_text = models.CharField(max_length=300, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True); height = models.PositiveIntegerField(null=True, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

class Comment(models.Model):
    class Status(models.TextChoices): PUBLISHED="published", "Published"; PENDING="pending", "Pending"; HIDDEN="hidden", "Hidden"; REMOVED="removed", "Removed"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="comments")
    visitor = models.ForeignKey("accounts.AnonymousVisitor", null=True, blank=True, on_delete=models.SET_NULL, related_name="comments")
    guest_name = models.CharField(max_length=80, blank=True)
    guest_email = models.EmailField(blank=True)
    body = models.TextField(max_length=2000)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PUBLISHED)
    created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)
    removed_at = models.DateTimeField(null=True, blank=True)
    like_count = models.PositiveIntegerField(default=0); reply_count = models.PositiveIntegerField(default=0)
    class Meta:
        ordering = ("created_at",)
        constraints = [models.CheckConstraint(condition=(Q(author__isnull=False, visitor__isnull=True) | Q(author__isnull=True, visitor__isnull=False)), name="comment_exactly_one_actor")]
        indexes = [models.Index(fields=("post", "parent", "created_at"))]
