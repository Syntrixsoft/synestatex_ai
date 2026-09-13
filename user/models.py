from django.db import models
from django.contrib import auth
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from . import utils
from core import models as core_models
from core import choices
import random
import requests
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import PermissionsMixin
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user_object(self,email, password, **extra_fields):
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.password = make_password(password)
        return user

    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given username, email, and password.
        """
        user = self._create_user_object(email, password, **extra_fields)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user( email, password, **extra_fields)

    create_user.alters_data = True


    def create_superuser(self,email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_platform_staff", True)
        extra_fields.setdefault("account_type", choices.AccountTypeChoices.STAFF)
        extra_fields.setdefault("status", choices.AccountStatusChoices.ACTIVE)
        extra_fields.setdefault("email_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user( email, password, **extra_fields)

    create_superuser.alters_data = True

    def with_perm(
        self, perm, is_active=True, include_superusers=True, backend=None, obj=None
    ):
        if backend is None:
            backends = auth._get_backends(return_tuples=True)
            if len(backends) == 1:
                backend, _ = backends[0]
            else:
                raise ValueError(
                    "You have multiple authentication backends configured and "
                    "therefore must provide the `backend` argument."
                )
        elif not isinstance(backend, str):
            raise TypeError(
                "backend must be a dotted import path string (got %r)." % backend
            )
        else:
            backend = auth.load_backend(backend)
        if hasattr(backend, "with_perm"):
            return backend.with_perm(
                perm,
                is_active=is_active,
                include_superusers=include_superusers,
                obj=obj,
            )
        return self.none()
    
    def get_queryset(self):
        return core_models.SoftDeletionQuerySet(self.model).filter(
            object_status=choices.ObjectStatusChoices.ACTIVE
        )

    def complete(self):
        return super().get_queryset()


class User(core_models.BaseModel,AbstractBaseUser, PermissionsMixin):
    """
    An abstract base class implementing a fully featured User model with
    admin-compliant permissions.

    email and password are required. Other fields are optional.
    """

    name = models.CharField(_("name"), max_length=150, blank=True)
    email = models.EmailField(_("email address"), unique=True)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    account_type = models.CharField(
        max_length=20,
        choices=choices.AccountTypeChoices.choices,
        default=choices.AccountTypeChoices.INDIVIDUAL,
    )
    status = models.CharField(
        max_length=25,
        choices=choices.AccountStatusChoices.choices,
        default=choices.AccountStatusChoices.PENDING_VERIFICATION,
        db_index=True,
    )
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    is_platform_staff = models.BooleanField(default=False)
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)
    addresses = GenericRelation("core.Address")
    
    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]
    
    objects = UserManager()
    
    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        swappable = "AUTH_USER_MODEL"
        indexes = [
            models.Index(fields=["phone"]),
            models.Index(fields=["status"]),
        ]
        
    def __str__(self):
        return f"{self.name} - {self.email}" 
    
    def save(self, *args, **kwargs):
        orig_obj = User.objects.filter(pk=self.id).first()
        self.handle_pre_save(orig_obj)
        super().save(*args, **kwargs)
        self.handle_post_save(orig_obj)

    @property
    def username(self):
        return self.name
    
    def handle_pre_save(self,orig_obj):
        pass  

    def handle_post_save(self, orig_obj):
        profile, _ = Profile.objects.get_or_create(
            user=self,
            defaults={"first_name": self.name or ""},
        )
        if not profile.avatar:
            self.fetch_avatar()

    def fetch_avatar(self):
        colors_lst =  [
            "00AA55", "1BA39C", "03A678", "00AA00", "26A65B", "00A566", "4183D7", "3477DB", "007FAA", "3455DB",
            "0000E0", "0000B5", "E26A6A", "B381B3", "BF6EE0", "BF55EC", "D252B2", "9370DB", "D25299", "D25852",
            "D2527F", "E73C70", "F62459", "E000E0", "AA8F00", "D47500", "FF4500", "E63022", "E76E3C", "EF4836",
            "FF0000", "DC143C", "FF5733", "FFC300", "900C3F", "581845", "C70039", "28B463", "1F618D", "8E44AD",
            "5DADE2", "48C9B0", "52BE80", "F39C12", "E67E22", "EC7063", "BB8FCE", "2ECC71", "3498DB", "A569BD",
            "1ABC9C", "2E86C1", "117A65", "5B2C6F", "784212", "7B241C", "6E2C00", "4A235A", "148F77", "117864",
            "239B56", "B03A2E", "943126", "78281F", "512E5F", "1C2833", "212F3C", "17202A"
        ]
        url = "https://ui-avatars.com/api/?name={}&background={}&color=FFF&font-size=0.55&bold=True&size=256".format(
            self.name, random.choice(colors_lst)
        )
        r = requests.get(url, timeout=5)
        img_temp = NamedTemporaryFile()
        img_temp.write(r.content)
        img_temp.flush()
        self.profile.avatar.save(
            "synestatex_ai-{}.jpg".format(str(self.id)[:10]), File(img_temp), save=True
        )

class Profile(core_models.BaseModel):
    user = models.OneToOneField(
        "user.User", on_delete=models.CASCADE, related_name="profile"
    )
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    display_name = models.CharField(max_length=200, blank=True)
    avatar = models.ImageField(
        upload_to=utils.profile_image_directory, null=True, blank=True, max_length=250
    )
    bio = models.TextField(blank=True)
    profile_completion = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return self.display_name or self.first_name or str(self.user.email)


class Role(core_models.BaseModel):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_system_role = models.BooleanField(default=True)
    owning_company = models.ForeignKey(
        "organization.Company",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="roles",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(is_system_role=True, owning_company__isnull=True)
                    | models.Q(is_system_role=False, owning_company__isnull=False)
                ),
                name="system_role_has_no_owner",
            )
        ]

    def delete(self, hard_delete=False):
        if self.is_system_role:
            raise ValidationError("System roles cannot be deleted")
        super().delete(hard_delete=hard_delete)

    def __str__(self):
        return self.name


class Permission(core_models.BaseModel):
    code = models.CharField(max_length=100, unique=True)
    resource = models.CharField(max_length=50)
    action = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["resource", "action"],
                name="unique_resource_action",
            )
        ]

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = "{}.{}".format(self.resource, self.action)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code


class RolePermission(core_models.BaseModel):
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name="role_permissions"
    )
    permission = models.ForeignKey(
        Permission, on_delete=models.CASCADE, related_name="role_permissions"
    )
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"],
                name="unique_role_permission",
            )
        ]

    def __str__(self):
        return "{} - {}".format(self.role, self.permission)


class UserRole(core_models.BaseModel):
    user = models.ForeignKey(
        "user.User", on_delete=models.CASCADE, related_name="user_roles"
    )
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name="user_roles"
    )
    scope_type = models.CharField(
        max_length=10,
        choices=choices.RoleScopeTypeChoices.choices,
        default=choices.RoleScopeTypeChoices.COMPANY,
    )
    scope_id = models.UUIDField(null=True, blank=True)
    granted_by = models.ForeignKey(
        "user.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        scope_type__in=[
                            choices.RoleScopeTypeChoices.COMPANY,
                            choices.RoleScopeTypeChoices.BRANCH,
                        ],
                        scope_id__isnull=False,
                    )
                    | models.Q(
                        scope_type__in=[
                            choices.RoleScopeTypeChoices.PLATFORM,
                            choices.RoleScopeTypeChoices.SELF,
                        ],
                        scope_id__isnull=True,
                    )
                ),
                name="scope_id_matches_scope_type",
            ),
            models.UniqueConstraint(
                fields=["user", "role", "scope_type", "scope_id"],
                name="unique_user_role_scope",
                nulls_distinct=False,
            ),
        ]
        indexes = [
            models.Index(fields=["user", "scope_type", "scope_id"]),
        ]

    def clean(self):
        needs_scope = self.scope_type in (
            choices.RoleScopeTypeChoices.COMPANY,
            choices.RoleScopeTypeChoices.BRANCH,
        )
        if needs_scope and not self.scope_id:
            raise ValidationError(
                "{} scope requires scope_id".format(self.scope_type)
            )
        if not needs_scope and self.scope_id:
            raise ValidationError(
                "{} scope must have empty scope_id".format(self.scope_type)
            )

    @property
    def is_currently_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at <= timezone.now():
            return False
        return True

    def __str__(self):
        return "{} - {} ({})".format(self.user, self.role, self.scope_type)


class ResourcePermission(core_models.BaseModel):
    user = models.ForeignKey(
        "user.User", on_delete=models.CASCADE, related_name="resource_permissions"
    )
    resource_type = models.CharField(max_length=50)
    resource_id = models.UUIDField()
    permission_level = models.CharField(
        max_length=10, choices=choices.ResourcePermissionLevelChoices.choices
    )
    granted_by = models.ForeignKey(
        "user.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "resource_type", "resource_id"],
                name="unique_resource_grant",
            )
        ]
        indexes = [
            models.Index(fields=["resource_type", "resource_id"]),
        ]

    @property
    def is_currently_valid(self):
        return self.expires_at is None or self.expires_at > timezone.now()

    def __str__(self):
        return "{} {} {}".format(self.user, self.permission_level, self.resource_type)
