import signal,time
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from interactions.models import PushDelivery
from interactions.push import deliver_notification

class Command(BaseCommand):
    help="Deliver queued Web Push notifications"
    def handle(self,*args,**options):
        self.running=True
        signal.signal(signal.SIGTERM,lambda *_:setattr(self,"running",False))
        while self.running:
            now=timezone.now()
            with transaction.atomic():
                batch=list(PushDelivery.objects.select_for_update(skip_locked=True).filter(status__in=("pending","failed"),next_attempt_at__lte=now).select_related("notification__recipient","notification__post","notification__comment")[:20])
                PushDelivery.objects.filter(pk__in=[x.pk for x in batch]).update(status="processing")
            for delivery in batch:
                if not PushDelivery.objects.filter(pk=delivery.pk,notification__isnull=False).exists():continue
                try:
                    code,sent=deliver_notification(delivery.notification);delivery.attempts+=1;delivery.last_error_code=code
                    delivery.status="sent" if sent else "discarded";delivery.sent_at=timezone.now() if sent else None
                except Exception as exc:
                    delivery.attempts+=1;delivery.last_error_code=type(exc).__name__[:80]
                    delivery.status="discarded" if delivery.attempts>=5 else "failed";delivery.next_attempt_at=timezone.now()+timedelta(seconds=min(300,2**delivery.attempts))
                    self.stderr.write("Push delivery failed; it will be retried when eligible.")
                delivery.save(update_fields=("status","attempts","next_attempt_at","sent_at","last_error_code"))
            if not batch:time.sleep(2)
