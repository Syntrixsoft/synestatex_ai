from django.contrib import admin

from .models import (
    Permission,
    Profile,
    ResourcePermission,
    Role,
    RolePermission,
    User,
    UserRole,
)

admin.site.register(User)
admin.site.register(Profile)
admin.site.register(Role)
admin.site.register(Permission)
admin.site.register(RolePermission)
admin.site.register(UserRole)
admin.site.register(ResourcePermission)
