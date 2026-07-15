from django.db import transaction
from django.db.models import F
from django.utils import timezone
from publishing.models import Post
from .models import PostLike,PostBookmark,PostView,PostShare

def actor_kwargs(request): return {"user":request.user,"visitor":None} if request.user.is_authenticated else {"user":None,"visitor":request.visitor}
@transaction.atomic
def set_reaction(request,post,model,counter,active):
    filters={"post":post,**actor_kwargs(request)}
    if active: _,changed=model.objects.get_or_create(**filters); delta=1 if changed else 0
    else: changed,_=model.objects.filter(**filters).delete(); delta=-1 if changed else 0
    if delta: Post.objects.filter(pk=post.pk).update(**{counter:F(counter)+delta})
    post.refresh_from_db(fields=[counter]); return getattr(post,counter), active if changed else model.objects.filter(**filters).exists()
@transaction.atomic
def record_view(request,post):
    _,created=PostView.objects.get_or_create(post=post,window_key=timezone.localdate(),**actor_kwargs(request))
    if created: Post.objects.filter(pk=post.pk).update(view_count=F("view_count")+1)
    post.refresh_from_db(fields=["view_count"]); return post.view_count
@transaction.atomic
def record_share(request,post,channel):
    PostShare.objects.create(post=post,channel=channel[:20],**actor_kwargs(request)); Post.objects.filter(pk=post.pk).update(share_count=F("share_count")+1); post.refresh_from_db(fields=["share_count"]); return post.share_count
