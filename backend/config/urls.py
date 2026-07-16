from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import api
urlpatterns=[
 path("admin/",admin.site.urls),path("health/",api.health),path("api/v1/auth/csrf/",api.csrf),path("api/v1/auth/me/",api.me),path("api/v1/auth/register/",api.register),path("api/v1/auth/login/",api.login_view),path("api/v1/auth/logout/",api.logout_view),
 path("api/v1/feed/",api.feed),path("api/v1/posts/",api.posts),path("api/v1/posts/<uuid:post_id>/",api.post_detail),path("api/v1/posts/<uuid:post_id>/thread/",api.thread),path("api/v1/posts/<uuid:post_id>/like/",api.reaction,{"kind":"like"}),path("api/v1/posts/<uuid:post_id>/bookmark/",api.reaction,{"kind":"bookmark"}),path("api/v1/posts/<uuid:post_id>/view/",api.view),path("api/v1/posts/<uuid:post_id>/share/",api.share),
 path("api/v1/posts/<uuid:post_id>/comments/",api.comments),path("api/v1/comments/<uuid:comment_id>/",api.comment_detail),path("api/v1/comments/<uuid:comment_id>/context/",api.comment_context),path("api/v1/comments/<uuid:comment_id>/replies/",api.comment_reply),path("api/v1/comments/<uuid:comment_id>/like/",api.comment_like),
 path("api/v1/categories/",api.categories),path("api/v1/search/",api.search),path("api/v1/profiles/me/",api.profile_me),path("api/v1/profiles/<str:username>/",api.profile),path("api/v1/profiles/<str:username>/posts/",api.profile_posts),
 path("api/v1/notifications/",api.notifications),path("api/v1/notifications/unread-count/",api.notification_unread_count),path("api/v1/notifications/read-all/",api.notifications_read_all),path("api/v1/notifications/clear/",api.notifications_clear),path("api/v1/notifications/<uuid:notification_id>/read/",api.notification_read),path("api/v1/notifications/<uuid:notification_id>/",api.notification_delete),
]+static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
