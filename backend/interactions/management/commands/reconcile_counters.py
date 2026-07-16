from django.core.management.base import BaseCommand
from publishing.models import Post,Comment
class Command(BaseCommand):
    help="Rebuild canonical denormalized engagement counters"
    def handle(self,*args,**kwargs):
        for p in Post.objects.all():
            p.like_count=p.likes.count();p.bookmark_count=p.bookmarks.count();p.view_count=p.views.count();p.share_count=p.shares.count();p.repost_count=p.reposts.count();p.quote_count=p.quotes.filter(status="published").count();p.comment_count=p.comments.filter(status="published").count();p.save(update_fields=("like_count","bookmark_count","view_count","share_count","repost_count","quote_count","comment_count"))
        for c in Comment.objects.all(): c.like_count=c.likes.count();c.reply_count=c.replies.filter(status="published").count();c.save(update_fields=("like_count","reply_count"))
        self.stdout.write(self.style.SUCCESS("Counters reconciled"))
