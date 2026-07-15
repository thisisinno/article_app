from django.contrib import admin
from .models import PostLike,PostBookmark,PostView,PostShare,Repost,CommentLike,CategoryFollow,Notification,ContentReport
admin.site.register([PostLike,PostBookmark,PostView,PostShare,Repost,CommentLike,CategoryFollow,Notification,ContentReport])
