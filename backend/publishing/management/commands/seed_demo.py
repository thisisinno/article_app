from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User,Profile,Follow
from publishing.models import Category,Post,Comment
from messaging.models import Conversation,Message
import uuid

class Command(BaseCommand):
    help="Create repeatable editorial demo data"
    def handle(self,*args,**kwargs):
        cats=[]
        descriptions={"Technology":"Software, hardware, and computing in everyday life.","Business":"Ideas shaping organizations and independent work.","Culture":"Books, media, communities, and the public sphere.","Design":"Intentional systems, spaces, and visual communication.","Science":"Research, discovery, and the natural world.","Lifestyle":"Thoughtful practices for daily life."}
        for i,(name,desc) in enumerate(descriptions.items()):
            c,_=Category.objects.update_or_create(slug=name.lower(),defaults={"name":name,"description":desc,"sort_order":i});cats.append(c)
        users=[]
        for username,name,bio in [("admin","Alex Rivera","Editor in chief at Insight."),("eleanor","Eleanor Vance","Editorial designer exploring technology and culture."),("marcus","Marcus Wright","Writer on computing and public life."),("sarah","Sarah Chen","Design researcher and independent publisher.")]:
            u,_=User.objects.get_or_create(username=username,defaults={"email":f"{username}@example.com","display_name":name,"is_staff":username=="admin","is_superuser":username=="admin"});u.display_name=name;u.set_password("InsightDemo123!");u.save();Profile.objects.update_or_create(user=u,defaults={"bio":bio,"location":"New York"});users.append(u)
        admin,eleanor,marcus,sarah=users
        Follow.objects.get_or_create(follower=admin,following=eleanor);Follow.objects.get_or_create(follower=eleanor,following=marcus)
        samples=[
            (eleanor,"article","The Architecture of Silence: Designing for Focus in a Noisy Web","The strongest interfaces are often the ones that know when to recede. Intentional design is not the absence of character; it is the discipline of giving each idea enough room to become legible.\n\nA calm system still needs hierarchy, motion, and moments of surprise. The work is deciding which moments earn attention.",cats[3]),
            (marcus,"short","","We keep describing ambient computing as a future state, yet it is already present in the small negotiations between our attention and the objects around us.",cats[0]),
            (sarah,"article","Reading Rooms for the Digital Age","What would publishing look like if the primary metric were understanding rather than time on page? This essay considers quieter measures of participation and care.",cats[2]),
            (admin,"short","","Welcome to Insight. Share work that teaches, questions, or helps somebody see a familiar subject differently.",cats[1]),
        ]
        made=[]
        for author,typ,title,body,cat in samples:
            p,_=Post.objects.get_or_create(author=author,title=title,body=body,defaults={"post_type":typ,"category":cat,"status":"published","published_at":timezone.now(),"excerpt":body[:180],"featured":typ=="article"});made.append(p)
        root=made[1];Post.objects.get_or_create(author=marcus,thread_root=root,thread_position=1,defaults={"body":"The useful question is not whether technology disappears, but whether its demands become proportional to its value.","category":cats[0],"status":"published","published_at":timezone.now()})
        Comment.objects.get_or_create(post=made[0],author=marcus,body="A useful distinction: quiet design can still make a strong argument.")
        conv,_=Conversation.objects.get_or_create();conv.participants.set([eleanor,marcus]);Message.objects.get_or_create(conversation=conv,sender=eleanor,client_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),defaults={"body":"That essay on intentional design was beautifully framed."})
        self.stdout.write(self.style.SUCCESS("Demo ready: admin / InsightDemo123! (all demo users use the same password)"))
