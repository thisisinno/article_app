import json
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, Q
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from accounts.models import User,Profile,Follow
from publishing.models import Post,Category,Comment
from interactions.models import PostLike,PostBookmark,Repost,CategoryFollow,Notification
from interactions.services import actor_kwargs,set_reaction,record_view,record_share
from messaging.models import Conversation,Message

def payload(request):
    try: return json.loads(request.body or "{}")
    except json.JSONDecodeError: return {}
def error(message,status=400,field=None): return JsonResponse({"error":{"message":message,"field":field}},status=status)
def user_json(u):
    p=Profile.objects.filter(user=u).first()
    return {"id":str(u.public_id),"username":u.username,"display_name":u.display_name or u.username,"avatar":p.avatar.url if p and p.avatar else None,"verified":bool(p and p.verified)}
def post_json(p,request,full=False):
    actor=actor_kwargs(request)
    return {"id":str(p.pk),"type":p.post_type,"title":p.title,"body":p.body if full else p.body[:640],"excerpt":p.excerpt,"status":p.status,"author":user_json(p.author),"category":{"name":p.category.name,"slug":p.category.slug} if p.category else None,"cover_image":p.cover_image.url if p.cover_image else None,"pinned":p.pinned,"featured":p.featured,"published_at":(p.published_at or p.created_at).isoformat(),"counts":{"views":p.view_count,"likes":p.like_count,"comments":p.comment_count,"reposts":p.repost_count,"bookmarks":p.bookmark_count,"shares":p.share_count},"viewer_state":{"liked":PostLike.objects.filter(post=p,**actor).exists(),"bookmarked":PostBookmark.objects.filter(post=p,**actor).exists(),"reposted":request.user.is_authenticated and Repost.objects.filter(post=p,user=request.user).exists(),"following_author":request.user.is_authenticated and Follow.objects.filter(follower=request.user,following=p.author).exists(),"can_edit":request.user==p.author or request.user.is_staff},"thread_root":str(p.thread_root_id) if p.thread_root_id else None,"thread_position":p.thread_position}
def page(qs,request,serializer,limit=20):
    cursor=request.GET.get("cursor"); qs=qs.filter(created_at__lt=cursor) if cursor else qs
    rows=list(qs[:limit+1]); more=len(rows)>limit; rows=rows[:limit]
    return {"results":[serializer(x) for x in rows],"next_cursor":rows[-1].created_at.isoformat() if more and rows else None}

def health(request): return JsonResponse({"status":"ok"})
def csrf(request): return JsonResponse({"csrfToken":get_token(request)})
def me(request): return JsonResponse({"user":user_json(request.user) if request.user.is_authenticated else None})
@require_POST
def register(request):
    d=payload(request); username=d.get("username","").strip().lower(); email=d.get("email","").strip().lower()
    if len(username)<3 or User.objects.filter(Q(username=username)|Q(email=email)).exists(): return error("Account details are unavailable",409)
    u=User(username=username,email=email,display_name=d.get("display_name",username)); u.set_password(d.get("password",""))
    try: u.full_clean(); u.save(); Profile.objects.create(user=u); login(request,u); return JsonResponse({"user":user_json(u)},status=201)
    except Exception: return error("Please check the account details",400)
@require_POST
def login_view(request):
    d=payload(request); u=authenticate(request,username=d.get("username",""),password=d.get("password",""))
    if not u: return error("Invalid credentials",401)
    login(request,u); return JsonResponse({"user":user_json(u)})
@require_POST
def logout_view(request): logout(request); return JsonResponse({"ok":True})

def feed(request):
    qs=Post.objects.filter(status="published",published_at__lte=timezone.now(),thread_root__isnull=True).select_related("author","category")
    if request.GET.get("mode")=="following":
        if not request.user.is_authenticated: return JsonResponse({"results":[],"next_cursor":None})
        qs=qs.filter(author__follower_links__follower=request.user)
    if request.GET.get("category"): qs=qs.filter(category__slug=request.GET["category"])
    return JsonResponse(page(qs,request,lambda p:post_json(p,request)))
@require_http_methods(["GET","POST"])
def posts(request):
    if request.method=="GET": return feed(request)
    if not request.user.is_authenticated: return error("Authentication required",401)
    d=payload(request); typ=d.get("type","short")
    if not d.get("body","").strip() or (typ=="article" and not d.get("title","").strip()): return error("Body and article title are required")
    cat=Category.objects.filter(slug=d.get("category")).first()
    p=Post.objects.create(author=request.user,post_type=typ,title=d.get("title","")[:240],body=d["body"],excerpt=d.get("excerpt","")[:400],category=cat,status=d.get("status","published"),published_at=timezone.now())
    return JsonResponse(post_json(p,request,True),status=201)
@require_http_methods(["GET","PATCH","DELETE"])
def post_detail(request,post_id):
    p=get_object_or_404(Post.objects.select_related("author","category"),pk=post_id)
    if request.method=="GET":
        if p.status!="published" and not (request.user==p.author or request.user.is_staff): return error("Not found",404)
        data=post_json(p,request,True); data["thread"]=[post_json(x,request,True) for x in p.thread_entries.filter(status="published").select_related("author","category")]; return JsonResponse(data)
    if not request.user.is_authenticated or (request.user!=p.author and not request.user.is_staff): return error("Forbidden",403)
    if request.method=="DELETE": p.status="removed"; p.removed_at=timezone.now(); p.save(update_fields=("status","removed_at")); return JsonResponse({},status=204)
    d=payload(request)
    for key in ("title","body","excerpt","status","pinned","featured"):
        if key in d and (key not in ("pinned","featured") or request.user.is_staff): setattr(p,key,d[key])
    p.save(); return JsonResponse(post_json(p,request,True))
@require_POST
def thread(request,post_id):
    if not request.user.is_authenticated: return error("Authentication required",401)
    root=get_object_or_404(Post,pk=post_id,thread_root__isnull=True)
    if root.author!=request.user: return error("Forbidden",403)
    d=payload(request); pos=(root.thread_entries.order_by("-thread_position").values_list("thread_position",flat=True).first() or 0)+1
    p=Post.objects.create(author=request.user,body=d.get("body","")[:30000],category=root.category,status="published",published_at=timezone.now(),thread_root=root,thread_position=pos)
    return JsonResponse(post_json(p,request,True),status=201)
@require_http_methods(["POST","DELETE"])
def reaction(request,post_id,kind):
    p=get_object_or_404(Post,pk=post_id,status="published")
    model,counter=(PostLike,"like_count") if kind=="like" else (PostBookmark,"bookmark_count")
    count,active=set_reaction(request,p,model,counter,request.method=="POST"); return JsonResponse({"active":active,"count":count})
@require_POST
def view(request,post_id): return JsonResponse({"count":record_view(request,get_object_or_404(Post,pk=post_id,status="published"))})
@require_POST
def share(request,post_id): return JsonResponse({"count":record_share(request,get_object_or_404(Post,pk=post_id,status="published"),payload(request).get("channel","copy"))})

@require_http_methods(["GET","POST"])
def comments(request,post_id):
    post=get_object_or_404(Post,pk=post_id,status="published")
    if request.method=="GET":
        qs=post.comments.filter(status="published",parent__isnull=True).select_related("author")
        def ser(c): return comment_json(c,request)
        return JsonResponse(page(qs,request,ser))
    d=payload(request)
    if d.get("website"): return error("Invalid submission")
    body=d.get("body","").strip()
    if not body or len(body)>2000 or body.count("http")>3: return error("Comment is invalid")
    if not request.user.is_authenticated and not d.get("guest_name","").strip(): return error("Guest display name is required")
    c=Comment.objects.create(post=post,author=request.user if request.user.is_authenticated else None,visitor=None if request.user.is_authenticated else request.visitor,guest_name=d.get("guest_name","")[:80],body=body)
    Post.objects.filter(pk=post.pk).update(comment_count=F("comment_count")+1)
    return JsonResponse(comment_json(c,request),status=201)
def comment_json(c,request):
    return {"id":str(c.pk),"body":c.body,"author":user_json(c.author) if c.author else {"username":None,"display_name":c.guest_name,"avatar":None,"verified":False},"created_at":c.created_at.isoformat(),"counts":{"likes":c.like_count,"replies":c.reply_count},"can_delete":request.user==c.author if c.author else c.visitor_id==request.visitor.id,"replies":[comment_json(x,request) for x in c.replies.filter(status="published")[:3]]}
@require_http_methods(["PATCH","DELETE"])
def comment_detail(request,comment_id):
    c=get_object_or_404(Comment,pk=comment_id)
    own=(request.user.is_authenticated and c.author==request.user) or (not request.user.is_authenticated and c.visitor_id==request.visitor.id)
    if not own and not request.user.is_staff: return error("Forbidden",403)
    if request.method=="DELETE": c.status="removed"; c.removed_at=timezone.now(); c.save(update_fields=("status","removed_at")); return JsonResponse({},status=204)
    c.body=payload(request).get("body",c.body)[:2000]; c.save(update_fields=("body","updated_at")); return JsonResponse(comment_json(c,request))
@require_POST
def comment_reply(request,comment_id):
    parent=get_object_or_404(Comment,pk=comment_id,status="published"); d=payload(request)
    if not request.user.is_authenticated and not d.get("guest_name"): return error("Guest display name is required")
    c=Comment.objects.create(post=parent.post,parent=parent,author=request.user if request.user.is_authenticated else None,visitor=None if request.user.is_authenticated else request.visitor,guest_name=d.get("guest_name","")[:80],body=d.get("body","")[:2000])
    Comment.objects.filter(pk=parent.pk).update(reply_count=F("reply_count")+1); Post.objects.filter(pk=parent.post_id).update(comment_count=F("comment_count")+1)
    return JsonResponse(comment_json(c,request),status=201)

def categories(request): return JsonResponse({"results":[{"name":c.name,"slug":c.slug,"description":c.description,"followers":c.followers.count(),"following":request.user.is_authenticated and c.followers.filter(user=request.user).exists()} for c in Category.objects.filter(is_active=True).order_by("sort_order")]})
def search(request):
    q=request.GET.get("q","").strip(); typ=request.GET.get("type","top")
    posts_qs=Post.objects.filter(status="published",published_at__lte=timezone.now()).select_related("author","category")
    if q: posts_qs=posts_qs.filter(Q(title__icontains=q)|Q(body__icontains=q)|Q(author__username__icontains=q)|Q(category__name__icontains=q))
    if request.GET.get("category"): posts_qs=posts_qs.filter(category__slug=request.GET["category"])
    if typ=="articles": posts_qs=posts_qs.filter(post_type="article")
    if typ=="posts": posts_qs=posts_qs.filter(post_type="short")
    people=User.objects.filter(Q(username__icontains=q)|Q(display_name__icontains=q))[:20] if q else User.objects.none()
    cats=Category.objects.filter(Q(name__icontains=q)|Q(description__icontains=q))[:20] if q else Category.objects.all()[:20]
    return JsonResponse({"posts":[post_json(p,request) for p in posts_qs[:20]],"people":[user_json(u) for u in people],"categories":[{"name":c.name,"slug":c.slug,"description":c.description} for c in cats]})
def profile(request,username):
    u=get_object_or_404(User,username=username); p,_=Profile.objects.get_or_create(user=u)
    return JsonResponse({**user_json(u),"bio":p.bio,"website":p.website,"location":p.location,"cover_image":p.cover_image.url if p.cover_image else None,"joined_at":u.date_joined.isoformat(),"following_count":u.following_links.count(),"follower_count":u.follower_links.count(),"is_following":request.user.is_authenticated and Follow.objects.filter(follower=request.user,following=u).exists(),"is_me":request.user==u})
def profile_posts(request,username):
    u=get_object_or_404(User,username=username); tab=request.GET.get("tab","posts"); qs=Post.objects.filter(author=u,status="published").select_related("author","category")
    if tab=="articles": qs=qs.filter(post_type="article")
    if tab=="bookmarks" and request.user==u: qs=Post.objects.filter(bookmarks__user=u,status="published").select_related("author","category")
    return JsonResponse(page(qs,request,lambda p:post_json(p,request)))
@require_http_methods(["POST","DELETE"])
def follow(request,username):
    if not request.user.is_authenticated: return error("Authentication required",401)
    target=get_object_or_404(User,username=username)
    if target==request.user:return error("You cannot follow yourself")
    if request.method=="POST": Follow.objects.get_or_create(follower=request.user,following=target); active=True
    else: Follow.objects.filter(follower=request.user,following=target).delete(); active=False
    return JsonResponse({"active":active,"count":target.follower_links.count()})

@login_required
def conversations(request):
    qs=request.user.conversations.prefetch_related("participants").order_by("-updated_at")
    return JsonResponse({"results":[{"id":str(c.id),"participants":[user_json(u) for u in c.participants.all() if u!=request.user],"last_message":c.messages.last().body if c.messages.exists() else "","updated_at":c.updated_at.isoformat()} for c in qs]})
@login_required
@require_http_methods(["GET","POST"])
def messages(request,conversation_id):
    c=get_object_or_404(Conversation,pk=conversation_id,participants=request.user)
    if request.method=="GET": return JsonResponse({"results":[{"id":str(m.id),"client_id":str(m.client_id),"body":m.body,"sender":user_json(m.sender),"created_at":m.created_at.isoformat(),"read_at":m.read_at.isoformat() if m.read_at else None} for m in c.messages.select_related("sender")[:100]]})
    d=payload(request)
    try: m,_=Message.objects.get_or_create(sender=request.user,client_id=d["client_id"],defaults={"conversation":c,"body":d.get("body","")[:4000]})
    except Exception:return error("Invalid message")
    return JsonResponse({"id":str(m.id),"client_id":str(m.client_id),"body":m.body,"created_at":m.created_at.isoformat()},status=201)
@login_required
def notifications(request): return JsonResponse({"results":[{"id":str(n.id),"kind":n.kind,"text":n.text,"read":bool(n.read_at),"created_at":n.created_at.isoformat(),"post_id":str(n.post_id) if n.post_id else None} for n in request.user.notifications.order_by("-created_at")[:30]]})
