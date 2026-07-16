from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from publishing.models import Media
class Command(BaseCommand):
    help="Report or delete orphaned files under posts/media only"
    def add_arguments(self,parser):parser.add_argument("--delete",action="store_true")
    def handle(self,*args,**options):
        root=Path(settings.MEDIA_ROOT)/"posts"/"media";active={Path(x).as_posix() for x in Media.objects.values_list("file",flat=True)};orphans=[]
        if root.exists():
            for path in root.rglob("*"):
                relative=path.relative_to(settings.MEDIA_ROOT).as_posix()
                if path.is_file() and relative not in active:orphans.append(path)
        for path in orphans:
            self.stdout.write(f"orphan: {path.relative_to(settings.MEDIA_ROOT)}")
            if options["delete"]:path.unlink()
        self.stdout.write(f"{'Deleted' if options['delete'] else 'Found'} {len(orphans)} orphan Post media file(s).")
