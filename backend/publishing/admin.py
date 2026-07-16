from django.contrib import admin
from django.db.models import Count
from django.utils import timezone
from django.utils.html import format_html
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError
from .models import Category, Tag, Post, Media, Comment
from interactions.notifications import notify_new_post

class MediaInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if sum(1 for form in self.forms if form.cleaned_data and not form.cleaned_data.get("DELETE",False))>10:raise ValidationError("A post can contain at most 10 media items.")
class MediaInline(admin.TabularInline):
    model=Media;extra=0;formset=MediaInlineFormSet;fields=("preview","file","sort_order","alt_text","width","height");readonly_fields=("preview","width","height");ordering=("sort_order","id");verbose_name_plural="Media (maximum 10; lower sort order appears first)"
    @admin.display(description="Preview")
    def preview(self,obj):return format_html('<img src="{}" style="width:90px;height:72px;object-fit:cover;border-radius:6px">',obj.file.url) if obj.pk and obj.file else "—"

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display=("name","slug","is_active","sort_order","post_count")
    list_editable=("is_active","sort_order");list_filter=("is_active",);search_fields=("name","slug","description");ordering=("sort_order","name");prepopulated_fields={"slug":("name",)}
    def get_queryset(self,request):return super().get_queryset(request).annotate(_post_count=Count("posts"))
    @admin.display(ordering="_post_count",description="Posts")
    def post_count(self,obj):return obj._post_count
    def has_add_permission(self,request):return request.user.is_superuser
    def has_change_permission(self,request,obj=None):return request.user.is_superuser
    def has_delete_permission(self,request,obj=None):return request.user.is_superuser

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display=("__str__","author","post_type","category","status","published_at","pinned","featured","view_count","like_count","comment_count","share_count")
    list_filter=("post_type","status","category","featured","pinned");search_fields=("title","body","author__username");autocomplete_fields=("category",)
    readonly_fields=("view_count","like_count","comment_count","repost_count","bookmark_count","share_count","published_notification_sent_at")
    inlines=(MediaInline,);actions=("publish","archive","pin","unpin","feature","unfeature")
    def save_model(self,request,obj,form,change):
        if obj.status==Post.Status.PUBLISHED:
            if not obj.category_id:raise ValueError("Published posts require a category.")
            obj.published_at=obj.published_at or timezone.now()
        super().save_model(request,obj,form,change)
        if obj.status==Post.Status.PUBLISHED:notify_new_post(obj)
    @admin.action(description="Publish selected")
    def publish(self,request,qs):
        for post in qs:
            if not post.category_id:continue
            post.status=Post.Status.PUBLISHED;post.published_at=post.published_at or timezone.now();post.save(update_fields=("status","published_at"));notify_new_post(post)
    @admin.action(description="Archive selected")
    def archive(self,request,qs):qs.update(status=Post.Status.ARCHIVED)
    @admin.action(description="Pin selected")
    def pin(self,request,qs):qs.update(pinned=True)
    @admin.action(description="Unpin selected")
    def unpin(self,request,qs):qs.update(pinned=False)
    @admin.action(description="Feature selected")
    def feature(self,request,qs):qs.update(featured=True)
    @admin.action(description="Unfeature selected")
    def unfeature(self,request,qs):qs.update(featured=False)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):list_display=("guest_name","author","post","status","created_at");list_filter=("status",);search_fields=("body","guest_name","author__username")
admin.site.register(Tag)
