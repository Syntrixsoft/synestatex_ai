from django.db import models
from django.conf import settings
from django.contrib import auth
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import AbstractUser
from . import utils
from core import models as core_models
from core import choices
import random
import requests
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.hashers import make_password
from django.core.exceptions import PermissionDenied
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


# Create your models here.
class User(core_models.BaseModel,AbstractBaseUser, PermissionsMixin):
    """
    An abstract base class implementing a fully featured User model with
    admin-compliant permissions.

    email and password are required. Other fields are optional.
    """

    name = models.CharField(_("name"), max_length=150, blank=True)
    email = models.EmailField(_("email address"),unique=True)
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
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)
    profile = models.ImageField(
        upload_to=utils.profile_directory, null=True, blank=True, max_length=250
    )
    
    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]
    
    objects = UserManager()
    
    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        swappable = "AUTH_USER_MODEL"
        
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
        if not self.profile:
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
        self.profile.save(
            "syntrixsoft-{}.jpg".format(str(self.id)[:10]), File(img_temp), save=True
        )