import json
from functools import wraps
from pathlib import Path
from django.contrib.auth import authenticate, login, logout
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import transaction
from django.db.models import F, Q
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from PIL import Image, UnidentifiedImageError
from accounts.models import User, Profile
from publishing.models import Post, Category, Comment, Media
from interactions.models import PostLike, PostBookmark, CommentLike, Notification, WebPushSubscription
from interactions.services import actor_kwargs, set_reaction, record_view, record_share
from interactions.notifications import notify_new_post, notify_post_comment, notify_comment_reply, notify_comment_like, notify_post_share

IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE = 5 * 1024 * 1024
MAX_IMAGES = 10
MAX_TOTAL_IMAGES = 40 * 1024 * 1024

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

def can_manage_post(user, post):
    return bool(user.is_authenticated and (user.is_superuser or post.author_id == user.id))

def post_json(p,request,full=False,viewer=None):
    actor=actor_kwargs(request)
    liked = p.pk in viewer[0] if viewer else PostLike.objects.filter(post=p,**actor).exists()
    bookmarked = p.pk in viewer[1] if viewer else PostBookmark.objects.filter(post=p,**actor).exists()
    manageable=can_manage_post(request.user,p)
    items=list(p.media.all())
    media=[{"id":str(x.pk),"type":x.media_type,"url":media_url(x.file),"alt_text":x.alt_text,"width":x.width,"height":x.height,"sort_order":x.sort_order} for x in sorted(items,key=lambda x:(x.sort_order,x.pk))]
    cover=media_url(p.cover_image)
    if not media and cover:media=[{"id":f"cover:{p.pk}","type":"image","url":cover,"alt_text":"","width":None,"height":None,"sort_order":0}]
    return {"id":str(p.pk),"type":p.post_type,"title":p.title,"body":p.body if full else p.body[:640],"excerpt":p.excerpt,"status":p.status,"author":user_json(p.author),"category":{"id":p.category_id,"name":p.category.name,"slug":p.category.slug} if p.category else None,"cover_image":cover,"media":media,"pinned":p.pinned,"featured":p.featured,"published_at":(p.published_at or p.created_at).isoformat(),"counts":{"views":p.view_count,"likes":p.like_count,"comments":p.comment_count,"bookmarks":p.bookmark_count,"shares":p.share_count},"viewer_state":{"liked":liked,"bookmarked":bookmarked,"can_edit":manageable,"can_delete":manageable},"thread_root":str(p.thread_root_id) if p.thread_root_id else None,"thread_position":p.thread_position}

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

def paginated_newest(qs,request,limit=20):
    """Stable descending cursor ordered by timestamp and UUID."""
    cursor=request.GET.get("cursor")
    if cursor:
        try:
            created_at,pk=cursor.rsplit("|",1)
            qs=qs.filter(Q(created_at__lt=created_at)|Q(created_at=created_at,pk__lt=pk))
        except (ValueError,ValidationError):
            return [],None
    rows=list(qs.order_by("-created_at","-id")[:limit+1]);more=len(rows)>limit;rows=rows[:limit]
    next_cursor=f"{rows[-1].created_at.isoformat()}|{rows[-1].pk}" if more and rows else None
    return rows,next_cursor

def validate_image(upload):
    if not upload:return
    if upload.content_type not in IMAGE_TYPES: raise ValidationError("Use a JPEG, PNG, WebP, or GIF image.")
    if upload.size>MAX_IMAGE: raise ValidationError("Each image must be 5 MB or smaller.")
    try:
        upload.seek(0)
        with Image.open(upload) as image:
            if image.format not in {"JPEG","PNG","WEBP","GIF"}:raise ValidationError("One of the selected images is invalid.")
            image.verify()
        upload.seek(0)
        with Image.open(upload) as image:width,height=image.size
        if width<100 or height<100 or width>12000 or height>12000:raise ValidationError("Images must be between 100×100 and 12000×12000 pixels.")
        upload.seek(0)
        return width,height
    except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError):
        upload.seek(0)
        raise ValidationError("One of the selected images is invalid.")

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

@require_http_methods(["GET"])
def feed(request):
    qs=Post.objects.filter(status="published",published_at__lte=timezone.now(),thread_root__isnull=True).select_related("author","author__profile","category").prefetch_related("media")
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
    images=request.FILES.getlist("images")
    if not images and request.FILES.get("cover_image"):images=[request.FILES["cover_image"]]
    if len(images)>MAX_IMAGES:return error("Select no more than 10 images.",field="images",code="too_many_images")
    if sum(x.size for x in images)>MAX_TOTAL_IMAGES:return error("Selected images must total 40 MB or less.",field="images",code="request_too_large")
    if len({(x.name,x.size) for x in images})!=len(images):return error("Remove duplicate images before publishing.",field="images",code="duplicate_image")
    try:dimensions=[validate_image(image) for image in images]
    except ValidationError as exc:return error(exc.message,field="images",code="invalid_image")
    saved=[]
    try:
        with transaction.atomic():
            p=Post.objects.create(author=request.user,post_type=typ,title=title[:240],body=body,excerpt=d.get("excerpt","")[:400],category=category,status=Post.Status.PUBLISHED,published_at=timezone.now())
            alts=d.getlist("image_alt_texts") if hasattr(d,"getlist") else []
            for index,(image,(width,height)) in enumerate(zip(images,dimensions)):
                item=Media.objects.create(post=p,file=image,media_type="image",alt_text=(alts[index] if index<len(alts) else "")[:300],width=width,height=height,sort_order=index);saved.append(item.file.name)
            transaction.on_commit(lambda:notify_new_post(p))
    except Exception:
        for name in saved:Media._meta.get_field("file").storage.delete(name)
        raise
    return JsonResponse(post_json(p,request,True),status=201)

@require_http_methods(["GET","PATCH","DELETE"])
def post_detail(request,post_id):
    p=get_object_or_404(Post.objects.select_related("author","author__profile","category").prefetch_related("media"),pk=post_id)
    if request.method=="GET":
        if p.status!="published":return error("Post unavailable.",404,code="not_found")
        data=post_json(p,request,True);thread_rows=list(p.thread_entries.filter(status="published").select_related("author","author__profile","category").prefetch_related("media"));data["thread"]=serialize_posts(thread_rows,request,True);return JsonResponse(data)
    if not request.user.is_authenticated:return error("Authentication required",401,code="authentication_required")
    if not can_manage_post(request.user,p):return error("You cannot manage this post.",403,code="forbidden")
    if request.method=="DELETE":p.status="removed";p.removed_at=timezone.now();p.save(update_fields=("status","removed_at"));return JsonResponse({"deleted":True,"post_id":str(p.pk),"redirect":"/"})
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
    channel=payload(request).get("channel","copy")
    if channel not in {"whatsapp","facebook","x","instagram_native","copy","native"}:return error("Unsupported share channel.",field="channel",code="validation_error")
    post=get_object_or_404(Post,pk=post_id,status="published");count=record_share(request,post,channel);transaction.on_commit(lambda:notify_post_share(post,request.user if request.user.is_authenticated else None,getattr(request,"visitor",None)));return JsonResponse({"count":count})

def comment_json(c,request,liked_ids=None,reply_previews=None):
    liked=(c.pk in liked_ids) if liked_ids is not None else CommentLike.objects.filter(comment=c,**actor_kwargs(request)).exists()
    previews=(reply_previews or {}).get(c.pk,[])
    visitor_id=getattr(getattr(request,"visitor",None),"id",None)
    return {"id":str(c.pk),"body":c.body,"author":user_json(c.author) if c.author else {"id":"guest","username":None,"display_name":c.guest_name,"avatar":None,"verified":False,"is_staff":False,"is_superuser":False,"can_publish":False},"created_at":c.created_at.isoformat(),"counts":{"likes":c.like_count,"replies":c.reply_count},"reply_count":c.reply_count,"has_more_replies":c.reply_count>len(previews),"viewer_state":{"liked":liked},"can_delete":bool(request.user.is_staff or (request.user.is_authenticated and c.author==request.user) or (not request.user.is_authenticated and c.visitor_id==visitor_id)),"replies":[comment_json(x,request,liked_ids,{}) for x in previews]}

@require_http_methods(["GET"])
def comment_context(request,comment_id):
    comment=get_object_or_404(Comment.objects.select_related("post","author","author__profile","parent","parent__author","parent__author__profile"),pk=comment_id,status="published",post__status="published")
    root=comment.parent or comment
    replies=list(root.replies.filter(status="published").select_related("author","author__profile"))
    return JsonResponse({"comment":comment_json(comment,request),"root_comment_id":str(root.pk),"post_id":str(comment.post_id),"parent_id":str(comment.parent_id) if comment.parent_id else None,"reply":bool(comment.parent_id),"context":{"root":comment_json(root,request),"replies":serialized_comments(replies,request)}})

def serialized_comments(rows,request,include_previews=False):
    ids=[c.pk for c in rows];liked=set(CommentLike.objects.filter(comment_id__in=ids,**actor_kwargs(request)).values_list("comment_id",flat=True))
    previews={}
    if include_previews:
        # Fetch in one query, then retain at most two previews for each root.
        for reply in Comment.objects.filter(parent_id__in=ids,status="published").select_related("author","author__profile").order_by("created_at","id"):
            bucket=previews.setdefault(reply.parent_id,[])
            if len(bucket)<2:bucket.append(reply)
        preview_ids=[x.pk for values in previews.values() for x in values]
        liked.update(CommentLike.objects.filter(comment_id__in=preview_ids,**actor_kwargs(request)).values_list("comment_id",flat=True))
    return [comment_json(c,request,liked,previews) for c in rows]

def validate_comment(request,d):
    body=d.get("body","").strip()
    if d.get("website") or not body or len(body)>2000 or body.count("http")>3:return None,error("Comment is invalid",field="body",code="validation_error")
    if not request.user.is_authenticated and not d.get("guest_name","").strip():return None,error("Guest display name is required",field="guest_name",code="validation_error")
    return body,None

@require_http_methods(["GET","POST"])
def comments(request,post_id):
    post=get_object_or_404(Post.objects.select_related("author"),pk=post_id,status="published")
    if request.method=="GET":
        roots=post.comments.filter(status="published",parent__isnull=True).select_related("author","author__profile")
        total=roots.count();rows,cursor=paginated_newest(roots,request)
        return JsonResponse({"results":serialized_comments(rows,request,True),"next_cursor":cursor,"total_count":total})
    d=payload(request);body,problem=validate_comment(request,d)
    if problem:return problem
    c=Comment.objects.create(post=post,author=request.user if request.user.is_authenticated else None,visitor=None if request.user.is_authenticated else request.visitor,guest_name=d.get("guest_name","")[:80],body=body);Post.objects.filter(pk=post.pk).update(comment_count=F("comment_count")+1);post.refresh_from_db(fields=("comment_count",));transaction.on_commit(lambda:notify_post_comment(c));return JsonResponse({"comment":comment_json(c,request),"post_comment_count":post.comment_count},status=201)

@require_http_methods(["PATCH","DELETE"])
def comment_detail(request,comment_id):
    c=get_object_or_404(Comment,pk=comment_id);own=(request.user.is_authenticated and c.author==request.user) or (not request.user.is_authenticated and c.visitor_id==request.visitor.id)
    if not own and not request.user.is_staff:return error("Forbidden",403,code="forbidden")
    if request.method=="DELETE":
        if c.status=="published":
            c.status="removed";c.removed_at=timezone.now();c.save(update_fields=("status","removed_at"));Post.objects.filter(pk=c.post_id).update(comment_count=F("comment_count")-1)
            if c.parent_id:Comment.objects.filter(pk=c.parent_id).update(reply_count=F("reply_count")-1)
        count=Post.objects.values_list("comment_count",flat=True).get(pk=c.post_id)
        return JsonResponse({"deleted":True,"post_comment_count":count})
    c.body=payload(request).get("body",c.body)[:2000];c.save(update_fields=("body","updated_at"));return JsonResponse(comment_json(c,request))

@require_http_methods(["GET","POST"])
def comment_reply(request,comment_id):
    parent=get_object_or_404(Comment.objects.select_related("post__author","author"),pk=comment_id,status="published");d=payload(request);body,problem=validate_comment(request,d)
    if request.method=="GET":
        qs=parent.replies.filter(status="published").select_related("author","author__profile");total=qs.count();rows,cursor=paginated_newest(qs,request)
        return JsonResponse({"results":serialized_comments(rows,request),"next_cursor":cursor,"total_count":total})
    if problem:return problem
    c=Comment.objects.create(post=parent.post,parent=parent,author=request.user if request.user.is_authenticated else None,visitor=None if request.user.is_authenticated else request.visitor,guest_name=d.get("guest_name","")[:80],body=body);Comment.objects.filter(pk=parent.pk).update(reply_count=F("reply_count")+1);Post.objects.filter(pk=parent.post_id).update(comment_count=F("comment_count")+1);parent.refresh_from_db(fields=("reply_count",));parent.post.refresh_from_db(fields=("comment_count",));transaction.on_commit(lambda:notify_comment_reply(c));return JsonResponse({"comment":comment_json(c,request),"parent_reply_count":parent.reply_count,"post_comment_count":parent.post.comment_count},status=201)

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
    q=request.GET.get("q","").strip();typ=request.GET.get("type","top");qs=Post.objects.filter(status="published",published_at__lte=timezone.now()).select_related("author","author__profile","category").prefetch_related("media")
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
    qs=qs.select_related("author","author__profile","category").prefetch_related("media");rows,cursor=paginated_rows(qs,request);return JsonResponse({"results":serialize_posts(rows,request),"next_cursor":cursor})

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
    parent_id=n.comment.parent_id if n.comment else None
    open_comments=n.kind in (Notification.Kind.POST_COMMENT,Notification.Kind.COMMENT_REPLY,Notification.Kind.COMMENT_LIKE)
    return {"id":str(n.pk),"kind":n.kind,"actor":user_json(n.actor) if n.actor else None,"text":n.text,"post":{"id":str(n.post_id),"title":n.post.title,"preview":preview} if n.post else None,"comment_id":str(n.comment_id) if n.comment_id else None,"comment_parent_id":str(parent_id) if parent_id else None,"root_comment_id":str(parent_id or n.comment_id) if n.comment_id else None,"open_comments":open_comments,"read":bool(n.read_at),"created_at":n.created_at.isoformat()}

@api_login_required
def notifications(request):
    qs=request.user.notifications.select_related("actor","actor__profile","post","comment");rows,cursor=paginated_rows(qs,request);return JsonResponse({"results":[notification_json(n) for n in rows],"next_cursor":cursor,"unread_count":request.user.notifications.filter(read_at__isnull=True).count()})
@api_login_required
def notification_unread_count(request):return JsonResponse({"count":request.user.notifications.filter(read_at__isnull=True).count()})
@api_login_required
@require_POST
def notification_read(request,notification_id):
    with transaction.atomic():
        n=get_object_or_404(request.user.notifications.select_for_update().select_related("actor","actor__profile","post","comment"),pk=notification_id)
        if n.read_at is None:n.read_at=timezone.now();n.save(update_fields=("read_at",))
        unread=request.user.notifications.filter(read_at__isnull=True).count()
    return JsonResponse({"notification":notification_json(n),"unread_count":unread})
@api_login_required
@require_POST
def notifications_read_all(request):updated=request.user.notifications.filter(read_at__isnull=True).update(read_at=timezone.now());return JsonResponse({"updated":updated,"unread_count":0})
@api_login_required
@require_http_methods(["DELETE"])
def notification_delete(request,notification_id):
    with transaction.atomic():
        get_object_or_404(request.user.notifications.select_for_update(),pk=notification_id).delete();unread=request.user.notifications.filter(read_at__isnull=True).count()
    return JsonResponse({"deleted":True,"unread_count":unread})
@api_login_required
@require_http_methods(["DELETE"])
def notifications_clear(request):deleted,_=request.user.notifications.all().delete();return JsonResponse({"deleted":deleted,"unread_count":0})

def push_public_key(request):
    if not settings.WEB_PUSH_ENABLED or not settings.VAPID_PUBLIC_KEY:return error("Web Push is not configured.",503,code="push_not_configured")
    return JsonResponse({"public_key":settings.VAPID_PUBLIC_KEY})

@api_login_required
def push_status(request):
    endpoint=request.GET.get("endpoint","")
    return JsonResponse({"subscribed":bool(endpoint and request.user.push_subscriptions.filter(endpoint=endpoint,active=True).exists()),"permission_required":True})

@api_login_required
@require_http_methods(["POST","DELETE"])
def push_subscribe(request):
    d=payload(request);endpoint=d.get("endpoint","")
    if not isinstance(endpoint,str) or not endpoint.startswith("https://") or len(endpoint)>1000:return error("Enter a valid Push endpoint.",field="endpoint",code="invalid_subscription")
    if request.method=="DELETE":
        updated=request.user.push_subscriptions.filter(endpoint=endpoint).update(active=False)
        return JsonResponse({"subscribed":False,"removed":bool(updated)})
    keys=d.get("keys") or {};p256dh=keys.get("p256dh","");auth=keys.get("auth","")
    if not isinstance(p256dh,str) or len(p256dh)<40 or not isinstance(auth,str) or len(auth)<8:return error("Push subscription keys are invalid.",field="keys",code="invalid_subscription")
    if not request.user.push_subscriptions.filter(active=True).filter(~Q(endpoint=endpoint)).count()<10:return error("Too many active devices.",409,code="subscription_limit")
    WebPushSubscription.objects.update_or_create(endpoint=endpoint,defaults={"user":request.user,"p256dh":p256dh,"auth":auth,"expiration_time":d.get("expirationTime"),"user_agent":request.headers.get("User-Agent","")[:300],"active":True,"failure_count":0})
    return JsonResponse({"subscribed":True})
