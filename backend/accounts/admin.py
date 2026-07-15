from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Profile, Follow, AnonymousVisitor
admin.site.register(User, UserAdmin)
admin.site.register([Profile, Follow, AnonymousVisitor])
