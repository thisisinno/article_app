from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand,CommandError
from interactions.push import send_subscription
class Command(BaseCommand):
    help="Send one safe Push smoke test"
    def add_arguments(self,parser):parser.add_argument("username")
    def handle(self,*args,**options):
        user=get_user_model().objects.filter(username=options["username"]).first()
        subscription=user and user.push_subscriptions.filter(active=True).first()
        if not subscription:raise CommandError("No active subscription for that user.")
        send_subscription(subscription,{"title":"Jesca Social Work","body":"Push notifications are working.","icon":"/icon-192.png","badge":"/notification-badge.png","tag":"jesca:test","url":"/notifications","kind":"test"})
        self.stdout.write(self.style.SUCCESS("Test Push sent successfully."))
