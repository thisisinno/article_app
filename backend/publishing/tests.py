import json
from django.contrib.admin.sites import AdminSite
from django.test import TestCase,RequestFactory
from django.utils import timezone
from accounts.models import User,Profile
from interactions.models import Notification,CommentLike
from interactions.notifications import notify_new_post
from .admin import CategoryAdmin
from .models import Post,Category,Comment

class ApiTests(TestCase):
    def setUp(self):
        self.category=Category.objects.create(name="Community",slug="community",sort_order=2)
        self.staff=User.objects.create_user("staff","staff@example.com","password123",display_name="Staff",is_staff=True)
        self.normal=User.objects.create_user("reader","reader@example.com","password123",display_name="Reader")
        Profile.objects.create(user=self.staff);Profile.objects.create(user=self.normal)
    def post(self,user=None,data=None):
        if user:self.client.force_login(user)
        return self.client.post("/api/v1/posts/",data=json.dumps(data or {"body":"Hello","category":"community"}),content_type="application/json")
    def test_anonymous_cannot_publish(self):self.assertEqual(self.post().status_code,401)
    def test_normal_user_cannot_publish(self):
        r=self.post(self.normal);self.assertEqual(r.status_code,403);self.assertEqual(r.json()["error"]["code"],"staff_only")
    def test_staff_can_publish(self):self.assertEqual(self.post(self.staff).status_code,201)
    def test_superuser_can_publish(self):
        u=User.objects.create_superuser("root","root@example.com","password123",display_name="Root");self.assertEqual(self.post(u).status_code,201)
    def test_category_required_and_active(self):
        self.assertEqual(self.post(self.staff,{"body":"No category"}).status_code,400);self.category.is_active=False;self.category.save();self.assertEqual(self.post(self.staff).status_code,400)
    def test_category_order_and_inactive_filter(self):
        Category.objects.create(name="Alpha",slug="alpha",sort_order=1);Category.objects.create(name="Hidden",slug="hidden",is_active=False)
        self.assertEqual([x["slug"] for x in self.client.get("/api/v1/categories/").json()["results"]],["general","alpha","community"])
    def test_category_admin_is_superuser_only(self):
        admin=CategoryAdmin(Category,AdminSite());request=RequestFactory().get("/admin/");request.user=self.staff;self.assertFalse(admin.has_add_permission(request));request.user=User(is_superuser=True);self.assertTrue(admin.has_add_permission(request))
    def test_chat_routes_are_gone(self):
        self.assertEqual(self.client.get("/api/v1/conversations/").status_code,404);self.assertEqual(self.client.post("/api/v1/ws/ticket/").status_code,404)

class NotificationTests(TestCase):
    def setUp(self):
        self.category=Category.objects.get(slug="general");self.author=User.objects.create_user("author","author@example.com","password123",display_name="Author",is_staff=True);self.reader=User.objects.create_user("reader2","reader2@example.com","password123",display_name="Reader");Profile.objects.create(user=self.author);Profile.objects.create(user=self.reader);self.post=Post.objects.create(author=self.author,category=self.category,body="Post",status="published",published_at=timezone.now())
    def test_new_post_notification_is_idempotent_and_excludes_author(self):
        notify_new_post(self.post);notify_new_post(self.post);self.assertEqual(Notification.objects.filter(recipient=self.reader,kind="new_post").count(),1);self.assertFalse(Notification.objects.filter(recipient=self.author,kind="new_post").exists())
    def test_notification_mutations_are_recipient_scoped(self):
        n=Notification.objects.create(recipient=self.reader,kind="new_post",post=self.post);other=User.objects.create_user("other","other@example.com","password123",display_name="Other");self.client.force_login(other);self.assertEqual(self.client.delete(f"/api/v1/notifications/{n.id}/").status_code,404);self.client.force_login(self.reader);self.assertEqual(self.client.get("/api/v1/notifications/unread-count/").json()["count"],1);self.client.post(f"/api/v1/notifications/{n.id}/read/");self.assertEqual(self.client.get("/api/v1/notifications/unread-count/").json()["count"],0);response=self.client.delete(f"/api/v1/notifications/{n.id}/");self.assertEqual(response.status_code,200);self.assertTrue(response.json()["deleted"])
    def test_comment_like_is_idempotent(self):
        c=Comment.objects.create(post=self.post,author=self.reader,body="Reply");self.client.force_login(self.author);url=f"/api/v1/comments/{c.id}/like/";self.client.post(url);self.client.post(url);c.refresh_from_db();self.assertEqual(c.like_count,1);self.assertEqual(CommentLike.objects.filter(comment=c).count(),1)

class ProfileAndSessionTests(TestCase):
    def setUp(self):self.user=User.objects.create_user("profile","profile@example.com","password123",display_name="Profile");Profile.objects.create(user=self.user);self.client.force_login(self.user)
    def test_profile_update(self):
        r=self.client.patch("/api/v1/profiles/me/",data=json.dumps({"display_name":"Updated","bio":"Bio"}),content_type="application/json");self.assertEqual(r.status_code,200);self.user.refresh_from_db();self.assertEqual(self.user.display_name,"Updated")
    def test_logout_invalidates_session(self):
        self.client.post("/api/v1/auth/logout/");self.assertIsNone(self.client.get("/api/v1/auth/me/").json()["user"])

class CommentContractTests(TestCase):
    def setUp(self):
        self.category=Category.objects.get(slug="general");self.author=User.objects.create_user("comment-author","ca@example.com","password123",display_name="Author");Profile.objects.create(user=self.author);self.post=Post.objects.create(author=self.author,category=self.category,body="Post",status="published",published_at=timezone.now())
    def test_root_creation_and_deletion_return_canonical_count(self):
        self.client.force_login(self.author);created=self.client.post(f"/api/v1/posts/{self.post.id}/comments/",json.dumps({"body":"Root"}),content_type="application/json");self.assertEqual(created.status_code,201);self.assertEqual(created.json()["post_comment_count"],1);comment_id=created.json()["comment"]["id"];deleted=self.client.delete(f"/api/v1/comments/{comment_id}/");self.assertEqual(deleted.status_code,200);self.assertEqual(deleted.json()["post_comment_count"],0)
    def test_root_and_reply_pagination_contract(self):
        roots=[Comment.objects.create(post=self.post,author=self.author,body=f"Root {n}") for n in range(22)];response=self.client.get(f"/api/v1/posts/{self.post.id}/comments/");self.assertEqual(len(response.json()["results"]),20);self.assertTrue(response.json()["next_cursor"]);parent=roots[0];Comment.objects.create(post=self.post,parent=parent,author=self.author,body="Reply");parent.reply_count=1;parent.save(update_fields=("reply_count",));replies=self.client.get(f"/api/v1/comments/{parent.id}/replies/");self.assertEqual(replies.json()["total_count"],1)
    def test_reply_creation_returns_both_counts(self):
        parent=Comment.objects.create(post=self.post,author=self.author,body="Root");self.client.force_login(self.author);response=self.client.post(f"/api/v1/comments/{parent.id}/replies/",json.dumps({"body":"Nested"}),content_type="application/json");self.assertEqual(response.status_code,201);self.assertEqual(response.json()["parent_reply_count"],1);self.assertEqual(response.json()["post_comment_count"],1)
