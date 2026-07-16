import json
from functools import wraps
from pathlib import Path
from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import transaction
from django.db.models import F, Q
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from accounts.models import User, Profile
from publishing.models import Post, Category, Comment
from interactions.models import PostLike, PostBookmark, CommentLike, Notification
from interactions.services import actor_kwargs, set_reaction, record_view, record_share
from interactions.notifications import notify_new_post, notify_post_comment, notify_comment_reply, notify_comment_like, notify_post_share

IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE = 5 * 1024 * 1024

def payload(request):
    if request.content_type and request.content_type.startswith("multipart/form-data"):
        return request.POST
    try: return json.loads(request.body or "{}")
    except json.JSONDecodeError: return {}

def error(message, status=400, field=None, code="request_failed", request=None):
    data={"code":code,"message":message}
    if field: data["field"]=field
    if request is not None and getattr(request,"request_id",None): data["request_id"]=request.request_id
    return JsonResponse({"error":data},status=status)

def api_login_required(view):
    @wraps(view)
    def wrapped(request,*args,**kwargs):
        if not request.user.is_authenticated:return error("Authentication required",401,code="authentication_required",request=request)
        return view(request,*args,**kwargs)
    return wrapped

def api_staff_required(view):
    @wraps(view)
    def wrapped(request,*args,**kwargs):
        if not request.user.is_authenticated:return error("Authentication required",401,code="authentication_required",request=request)
        if not (request.user.is_staff or request.user.is_superuser):return error("Only staff members can publish posts.",403,code="staff_only",request=request)
        return view(request,*args,**kwargs)
    return wrapped

def csrf_failure(request,reason=""): return error("Security token expired. Please retry.",403,code="csrf_failed",request=request)

def media_url(value): return value.url if value else None

def user_json(u):
    try: p=u.profile
    except Profile.DoesNotExist: p=None
    can_publish=bool(u.is_staff or u.is_superuser)
    return {"id":str(u.public_id),"username":u.username,"display_name":u.display_name or u.username,"avatar":media_url(p.avatar) if p else None,"verified":bool(p and p.verified),"is_staff":bool(u.is_staff),"is_superuser":bool(u.is_superuser),"can_publish":can_publish}

def post_json(p,request,full=False,viewer=None):
    actor=actor_kwargs(request)
    liked = p.pk in viewer[0] if viewer else PostLike.objects.filter(post=p,**actor).exists()
    bookmarked = p.pk in viewer[1] if viewer else PostBookmark.objects.filter(post=p,**actor).exists()
    return {"id":str(p.pk),"type":p.post_type,"title":p.title,"body":p.body if full else p.body[:640],"excerpt":p.excerpt,"status":p.status,"author":user_json(p.author),"category":{"id":p.category_id,"name":p.category.name,"slug":p.category.slug} if p.category else None,"cover_image":media_url(p.cover_image),"pinned":p.pinned,"featured":p.featured,"published_at":(p.published_at or p.created_at).isoformat(),"counts":{"views":p.view_count,"likes":p.like_count,"comments":p.comment_count,"bookmarks":p.bookmark_count,"shares":p.share_count},"viewer_state":{"liked":liked,"bookmarked":bookmarked,"can_edit":bool(request.user.is_authenticated and request.user.is_staff)},"thread_root":str(p.thread_root_id) if p.thread_root_id else None,"thread_position":p.thread_position}

def serialize_posts(rows,request,full=False):
    ids=[x.pk for x in rows]; actor=actor_kwargs(request)
    liked=set(PostLike.objects.filter(post_id__in=ids,**actor).values_list("post_id",flat=True))
    bookmarked=set(PostBookmark.objects.filter(post_id__in=ids,**actor).values_list("post_id",flat=True))
    return [post_json(x,request,full,(liked,bookmarked)) for x in rows]

def paginated_rows(qs,request,limit=20):
    cursor=request.GET.get("cursor")
    if cursor: qs=qs.filter(created_at__lt=cursor)
    rows=list(qs[:limit+1]); more=len(rows)>limit; rows=rows[:limit]
    return rows, rows[-1].created_at.isoformat() if more and rows else None

def validate_image(upload):
    if not upload:return
    if upload.content_type not in IMAGE_TYPES: raise ValidationError("Use a JPEG, PNG, WebP, or GIF image.")
    if upload.size>MAX_IMAGE: raise ValidationError("Image files must be 5 MB or smaller.")

def health(request): return JsonResponse({"status":"ok"})
def csrf(request): return JsonResponse({"csrfToken":get_token(request)})
def me(request): return JsonResponse({"user":user_json(request.user) if request.user.is_authenticated else None})

@require_POST
def register(request):
    d=payload(request); username=d.get("username","").strip().lower(); email=d.get("email","").strip().lower()
    if len(username)<3 or User.objects.filter(Q(username=username)|Q(email=email)).exists(): return error("Account details are unavailable",409)
    u=User(username=username,email=email,display_name=d.get("display_name",username));u.set_password(d.get("password",""))
    try:u.full_clean();u.save();Profile.objects.create(user=u);login(request,u);return JsonResponse({"user":user_json(u)},status=201)
    except Exception:return error("Please check the account details",400)

@require_POST
def login_view(request):
    d=payload(request);u=authenticate(request,username=d.get("username",""),password=d.get("password",""))
    if not u:return error("Invalid credentials",401)
    login(request,u);return JsonResponse({"user":user_json(u)})

@require_POST
def logout_view(request):logout(request);return JsonResponse({"ok":True})

def feed(request):
    qs=Post.objects.filter(status="published",published_at__lte=timezone.now(),thread_root__isnull=True).select_related("author","author__profile","category")
    if request.GET.get("category"):qs=qs.filter(category__slug=request.GET["category"],category__is_active=True)
    rows,cursor=paginated_rows(qs,request)
    return JsonResponse({"results":serialize_posts(rows,request),"next_cursor":cursor})

@require_http_methods(["GET","POST"])
def posts(request):
    if request.method=="GET":return feed(request)
    return create_post(request)

@api_staff_required
@require_POST
def create_post(request):
    d=payload(request);typ=d.get("type","short");body=d.get("body","").strip();title=d.get("title","").strip()
    if typ not in Post.Type.values:return error("Invalid post type.",field="type",code="validation_error")
    if not body:return error("Body is required.",field="body",code="validation_error")
    if typ==Post.Type.ARTICLE and not title:return error("Article title is required.",field="title",code="validation_error")
    category=Category.objects.filter(slug=d.get("category",""),is_active=True).first()
    if not category:return error("Select a valid active category.",field="category",code="invalid_category")
    cover=request.FILES.get("cover_image")
    try:validate_image(cover)
    except ValidationError as exc:return error(exc.message,field="cover_image",code="invalid_image")
    with transaction.atomic():
        p=Post.objects.create(author=request.user,post_type=typ,title=title[:240],body=body,excerpt=d.get("excerpt","")[:400],category=category,cover_image=cover,status=Post.Status.PUBLISHED,published_at=timezone.now())
        transaction.on_commit(lambda:notify_new_post(p))
    return JsonResponse(post_json(p,request,True),status=201)

@require_http_methods(["GET","PATCH","DELETE"])
def post_detail(request,post_id):
    p=get_object_or_404(Post.objects.select_related("author","author__profile","category"),pk=post_id)
    if request.method=="GET":
        if p.status!="published" and not (request.user.is_authenticated and request.user.is_staff):return error("Not found",404,code="not_found")
        data=post_json(p,request,True);thread_rows=list(p.thread_entries.filter(status="published").select_related("author","author__profile","category"));data["thread"]=serialize_posts(thread_rows,request,True);return JsonResponse(data)
    if not request.user.is_authenticated:return error("Authentication required",401,code="authentication_required")
    if not request.user.is_staff:return error("Only staff members can publish posts.",403,code="staff_only")
    if request.method=="DELETE":p.status="removed";p.removed_at=timezone.now();p.save(update_fields=("status","removed_at"));return JsonResponse({},status=204)
    d=payload(request)
    for key in ("title","body","excerpt"):
        if key in d:setattr(p,key,d[key])
    if "category" in d:
        category=Category.objects.filter(slug=d["category"],is_active=True).first()
        if not category:return error("Select a valid active category.",field="category",code="invalid_category")
        p.category=category
    p.save();return JsonResponse(post_json(p,request,True))

@api_staff_required
@require_POST
def thread(request,post_id):
    root=get_object_or_404(Post,pk=post_id,thread_root__isnull=True)
    d=payload(request);body=d.get("body","").strip()
    if not body:return error("Body is required.",field="body",code="validation_error")
    pos=(root.thread_entries.order_by("-thread_position").values_list("thread_position",flat=True).first() or 0)+1
    p=Post.objects.create(author=request.user,body=body[:30000],category=root.category,status="published",published_at=timezone.now(),thread_root=root,thread_position=pos)
    return JsonResponse(post_json(p,request,True),status=201)

@require_http_methods(["POST","DELETE"])
def reaction(request,post_id,kind):
    p=get_object_or_404(Post,pk=post_id,status="published");model,counter=(PostLike,"like_count") if kind=="like" else (PostBookmark,"bookmark_count")
    count,active=set_reaction(request,p,model,counter,request.method=="POST");return JsonResponse({"active":active,"count":count})

@require_POST
def view(request,post_id):return JsonResponse({"count":record_view(request,get_object_or_404(Post,pk=post_id,status="published"))})
@require_POST
def share(request,post_id):
    post=get_object_or_404(Post,pk=post_id,status="published");count=record_share(request,post,payload(request).get("channel","copy"));transaction.on_commit(lambda:notify_post_share(post,request.user if request.user.is_authenticated else None,getattr(request,"visitor",None)));return JsonResponse({"count":count})

def comment_json(c,request):
    actor=actor_kwargs(request);liked=CommentLike.objects.filter(comment=c,**actor).exists()
    return {"id":str(c.pk),"body":c.body,"author":user_json(c.author) if c.author else {"id":"guest","username":None,"display_name":c.guest_name,"avatar":None,"verified":False,"is_staff":False,"is_superuser":False,"can_publish":False},"created_at":c.created_at.isoformat(),"counts":{"likes":c.like_count,"replies":c.reply_count},"viewer_state":{"liked":liked},"can_delete":bool(request.user.is_staff or (request.user.is_authenticated and c.author==request.user) or (not request.user.is_authenticated and c.visitor_id==request.visitor.id)),"replies":[comment_json(x,request) for x in c.replies.filter(status="published").select_related("author","author__profile")[:20]]}

def validate_comment(request,d):
    body=d.get("body","").strip()
    if d.get("website") or not body or len(body)>2000 or body.count("http")>3:return None,error("Comment is invalid",field="body",code="validation_error")
    if not request.user.is_authenticated and not d.get("guest_name","").strip():return None,error("Guest display name is required",field="guest_name",code="validation_error")
    return body,None

@require_http_methods(["GET","POST"])
def comments(request,post_id):
    post=get_object_or_404(Post.objects.select_related("author"),pk=post_id,status="published")
    if request.method=="GET":
        rows,cursor=paginated_rows(post.comments.filter(status="published",parent__isnull=True).select_related("author","author__profile").prefetch_related("replies__author__profile"),request)
        return JsonResponse({"results":[comment_json(c,request) for c in rows],"next_cursor":cursor})
    d=payload(request);body,problem=validate_comment(request,d)
    if problem:return problem
    c=Comment.objects.create(post=post,author=request.user if request.user.is_authenticated else None,visitor=None if request.user.is_authenticated else request.visitor,guest_name=d.get("guest_name","")[:80],body=body);Post.objects.filter(pk=post.pk).update(comment_count=F("comment_count")+1);transaction.on_commit(lambda:notify_post_comment(c));return JsonResponse(comment_json(c,request),status=201)

@require_http_methods(["PATCH","DELETE"])
def comment_detail(request,comment_id):
    c=get_object_or_404(Comment,pk=comment_id);own=(request.user.is_authenticated and c.author==request.user) or (not request.user.is_authenticated and c.visitor_id==request.visitor.id)
    if not own and not request.user.is_staff:return error("Forbidden",403,code="forbidden")
    if request.method=="DELETE":c.status="removed";c.removed_at=timezone.now();c.save(update_fields=("status","removed_at"));return JsonResponse({},status=204)
    c.body=payload(request).get("body",c.body)[:2000];c.save(update_fields=("body","updated_at"));return JsonResponse(comment_json(c,request))

@require_POST
def comment_reply(request,comment_id):
    parent=get_object_or_404(Comment.objects.select_related("post__author","author"),pk=comment_id,status="published");d=payload(request);body,problem=validate_comment(request,d)
    if problem:return problem
    c=Comment.objects.create(post=parent.post,parent=parent,author=request.user if request.user.is_authenticated else None,visitor=None if request.user.is_authenticated else request.visitor,guest_name=d.get("guest_name","")[:80],body=body);Comment.objects.filter(pk=parent.pk).update(reply_count=F("reply_count")+1);Post.objects.filter(pk=parent.post_id).update(comment_count=F("comment_count")+1);transaction.on_commit(lambda:notify_comment_reply(c));return JsonResponse(comment_json(c,request),status=201)

@require_http_methods(["POST","DELETE"])
def comment_like(request,comment_id):
    c=get_object_or_404(Comment.objects.select_related("author","post"),pk=comment_id,status="published");filters={"comment":c,**actor_kwargs(request)}
    if request.method=="POST":_,changed=CommentLike.objects.get_or_create(**filters);delta=1 if changed else 0;active=True
    else:changed,_=CommentLike.objects.filter(**filters).delete();delta=-1 if changed else 0;active=False
    if delta:Comment.objects.filter(pk=c.pk).update(like_count=F("like_count")+delta)
    c.refresh_from_db(fields=("like_count",))
    if request.method=="POST" and changed:transaction.on_commit(lambda:notify_comment_like(c,request.user if request.user.is_authenticated else None,getattr(request,"visitor",None)))
    return JsonResponse({"active":active,"count":c.like_count})

def categories(request):return JsonResponse({"results":[{"id":c.pk,"name":c.name,"slug":c.slug,"description":c.description} for c in Category.objects.filter(is_active=True).order_by("sort_order","name")]})

def search(request):
    q=request.GET.get("q","").strip();typ=request.GET.get("type","top");qs=Post.objects.filter(status="published",published_at__lte=timezone.now()).select_related("author","author__profile","category")
    if q:qs=qs.filter(Q(title__icontains=q)|Q(body__icontains=q)|Q(category__name__icontains=q))
    if request.GET.get("category"):qs=qs.filter(category__slug=request.GET["category"])
    if typ=="articles":qs=qs.filter(post_type="article")
    if typ=="posts":qs=qs.filter(post_type="short")
    if typ=="latest":qs=qs.order_by("-published_at")
    rows=list(qs[:20]);return JsonResponse({"posts":serialize_posts(rows,request),"categories":[{"id":c.pk,"name":c.name,"slug":c.slug,"description":c.description} for c in Category.objects.filter(is_active=True).order_by("sort_order","name")]})

def profile(request,username):
    u=get_object_or_404(User.objects.select_related("profile"),username=username);p,_=Profile.objects.get_or_create(user=u)
    return JsonResponse({**user_json(u),"bio":p.bio,"website":p.website,"location":p.location,"cover_image":media_url(p.cover_image),"joined_at":u.date_joined.isoformat(),"is_me":request.user==u})

def profile_posts(request,username):
    u=get_object_or_404(User,username=username);tab=request.GET.get("tab","posts")
    if tab=="bookmarks":
        if request.user!=u:return error("Not found",404,code="not_found")
        qs=Post.objects.filter(bookmarks__user=u,status="published")
    elif tab=="replies":qs=Post.objects.filter(comments__author=u,status="published").distinct()
    elif tab=="likes":qs=Post.objects.filter(likes__user=u,status="published")
    else:
        qs=Post.objects.filter(author=u,status="published")
        if tab=="articles":qs=qs.filter(post_type="article")
        elif tab=="posts":qs=qs.filter(post_type="short")
    qs=qs.select_related("author","author__profile","category");rows,cursor=paginated_rows(qs,request);return JsonResponse({"results":serialize_posts(rows,request),"next_cursor":cursor})

@api_login_required
@require_http_methods(["PATCH"])
def profile_me(request):
    d=payload(request);p,_=Profile.objects.get_or_create(user=request.user);display=d.get("display_name",request.user.display_name).strip()
    if not display:return error("Display name is required.",field="display_name",code="validation_error")
    bio=d.get("bio",p.bio)
    if len(bio)>300:return error("Bio must be 300 characters or fewer.",field="bio",code="validation_error")
    website=d.get("website",p.website).strip()
    if website:
        try:URLValidator()(website)
        except ValidationError:return error("Enter a valid website URL.",field="website",code="validation_error")
    for name in ("avatar","cover_image"):
        upload=request.FILES.get(name)
        try:validate_image(upload)
        except ValidationError as exc:return error(exc.message,field=name,code="invalid_image")
        if upload:setattr(p,name,upload)
        if d.get(f"remove_{name}") in ("true","1",True):setattr(p,name,None)
    request.user.display_name=display;request.user.save(update_fields=("display_name",));p.bio=bio;p.website=website;p.location=d.get("location",p.location)[:100];p.save();return profile(request,request.user.username)

def notification_json(n):
    preview=(n.post.title or n.post.body[:120]) if n.post else ""
    return {"id":str(n.pk),"kind":n.kind,"actor":user_json(n.actor) if n.actor else None,"text":n.text,"post":{"id":str(n.post_id),"title":n.post.title,"preview":preview} if n.post else None,"comment_id":str(n.comment_id) if n.comment_id else None,"read":bool(n.read_at),"created_at":n.created_at.isoformat()}

@api_login_required
def notifications(request):
    qs=request.user.notifications.select_related("actor","actor__profile","post","comment");rows,cursor=paginated_rows(qs,request);return JsonResponse({"results":[notification_json(n) for n in rows],"next_cursor":cursor,"unread_count":request.user.notifications.filter(read_at__isnull=True).count()})
@api_login_required
def notification_unread_count(request):return JsonResponse({"count":request.user.notifications.filter(read_at__isnull=True).count()})
@api_login_required
@require_POST
def notification_read(request,notification_id):
    n=get_object_or_404(request.user.notifications,pk=notification_id);n.read_at=n.read_at or timezone.now();n.save(update_fields=("read_at",));return JsonResponse(notification_json(n))
@api_login_required
@require_POST
def notifications_read_all(request):request.user.notifications.filter(read_at__isnull=True).update(read_at=timezone.now());return JsonResponse({"ok":True,"unread_count":0})
@api_login_required
@require_http_methods(["DELETE"])
def notification_delete(request,notification_id):get_object_or_404(request.user.notifications,pk=notification_id).delete();return JsonResponse({},status=204)
@api_login_required
@require_http_methods(["DELETE"])
def notifications_clear(request):request.user.notifications.all().delete();return JsonResponse({},status=204)
