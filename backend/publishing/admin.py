from django.contrib import admin
from .models import Category, Tag, Post, Media, Comment
class MediaInline(admin.TabularInline): model = Media; extra = 0
@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display=("__str__","author","post_type","category","status","published_at","featured","pinned","view_count","like_count")
    list_filter=("post_type","status","category","featured","pinned"); search_fields=("title","body","author__username")
    readonly_fields=("view_count","like_count","comment_count","repost_count","bookmark_count","share_count")
    inlines=(MediaInline,); actions=("publish","archive","feature","pin")
    @admin.action(description="Publish selected")
    def publish(self, request, qs): qs.update(status="published")
    @admin.action(description="Archive selected")
    def archive(self, request, qs): qs.update(status="archived")
    @admin.action(description="Feature selected")
    def feature(self, request, qs): qs.update(featured=True)
    @admin.action(description="Pin selected")
    def pin(self, request, qs): qs.update(pinned=True)
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display=("guest_name","author","post","status","created_at"); list_filter=("status",); search_fields=("body","guest_name","author__username")
admin.site.register([Category, Tag])
