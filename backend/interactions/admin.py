from django.contrib import admin
from .models import PostLike,PostBookmark,PostView,PostShare,Repost,CommentLike,CategoryFollow,Notification,ContentReport
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display=("recipient","actor","kind","post","is_read","created_at");list_filter=("kind","read_at","created_at");search_fields=("recipient__username","actor__username","text","post__title");readonly_fields=("dedupe_key",)
    @admin.display(boolean=True)
    def is_read(self,obj):return bool(obj.read_at)
admin.site.register([PostLike,PostBookmark,PostView,PostShare,Repost,CommentLike,CategoryFollow,ContentReport])
