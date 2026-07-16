import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding,NoEncryption,PrivateFormat,PublicFormat
from django.core.management.base import BaseCommand
class Command(BaseCommand):
    help="Generate a VAPID key pair without changing configuration"
    def handle(self,*args,**options):
        key=ec.generate_private_key(ec.SECP256R1());private=key.private_bytes(Encoding.DER,PrivateFormat.PKCS8,NoEncryption());public=key.public_key().public_bytes(Encoding.X962,PublicFormat.UncompressedPoint);encode=lambda x:base64.urlsafe_b64encode(x).rstrip(b"=").decode()
        self.stdout.write("VAPID_PUBLIC_KEY (safe for browsers): "+encode(public));self.stdout.write("VAPID_PRIVATE_KEY (server secret; never expose): "+encode(private));self.stdout.write("Changing keys requires browser subscriptions to be recreated.")
