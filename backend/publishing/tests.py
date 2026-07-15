from django.test import TestCase,Client
from django.utils import timezone
from accounts.models import User
from .models import Post,Comment

class PublishingTests(TestCase):
    def setUp(self): self.user=User.objects.create_user("writer","w@example.com","password123",display_name="Writer");self.post=Post.objects.create(author=self.user,body="Published",status="published",published_at=timezone.now())
    def test_feed_public_only(self):
        Post.objects.create(author=self.user,body="Draft",status="draft")
        data=self.client.get("/api/v1/feed/").json();self.assertEqual([x["body"] for x in data["results"]],["Published"])
    def test_owner_permissions(self):
        other=User.objects.create_user("other","o@example.com","password123",display_name="Other");self.client.force_login(other);self.assertEqual(self.client.patch(f"/api/v1/posts/{self.post.id}/",data='{"body":"no"}',content_type="application/json").status_code,403)
    def test_guest_comment_validation(self): self.assertEqual(self.client.post(f"/api/v1/posts/{self.post.id}/comments/",data='{"body":"hello"}',content_type="application/json").status_code,400)

class CounterTests(TestCase):
    def setUp(self): self.u=User.objects.create_user("u","u@example.com","password123",display_name="U");self.p=Post.objects.create(author=self.u,body="x",status="published",published_at=timezone.now())
    def test_anonymous_like_idempotent(self):
        url=f"/api/v1/posts/{self.p.id}/like/";self.client.post(url);self.client.post(url);self.p.refresh_from_db();self.assertEqual(self.p.like_count,1);self.client.delete(url);self.client.delete(url);self.p.refresh_from_db();self.assertEqual(self.p.like_count,0)
    def test_view_once_per_window(self):
        url=f"/api/v1/posts/{self.p.id}/view/";self.client.post(url);self.client.post(url);self.p.refresh_from_db();self.assertEqual(self.p.view_count,1)
