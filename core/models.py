from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.query import QuerySet
from django.core.validators import MaxLengthValidator
from django.db.models.signals import post_delete
import uuid
from core import choices
from . import utils

# Create your models here.
class SoftDeletionQuerySet(QuerySet):
    def delete(self):
        # Updating Status or all related model's objects
        for obj in self:
            try:
                for related_object in obj._meta.related_objects:
                    try:
                        if isinstance(related_object, models.OneToOneRel):
                            related_name = related_object.get_accessor_name()
                            related_instance = getattr(obj, related_name)
                            if related_instance and hasattr(related_instance,"object_status"):
                                related_instance.object_status = (
                                    choices.ObjectStatusChoices.DELETED
                                )
                                related_instance.save()
                            elif related_instance:
                                related_instance.delete()
                        elif isinstance(
                            related_object,
                            (models.ManyToOneRel, models.ManyToManyRel),
                        ):
                            related_name = related_object.get_accessor_name()
                            related_queryset = getattr(obj, related_name).all()
                            for related_instance in related_queryset:
                                if hasattr(related_instance,"object_status"):
                                        related_instance.object_status = (
                                            choices.ObjectStatusChoices.DELETED
                                        )
                                        related_instance.save()
                                else:
                                    related_instance.delete()
                    except Exception as e: 
                        continue

            except Exception as e:
                print("$" * 30, e)
        return super(SoftDeletionQuerySet, self).update(
            object_status=choices.ObjectStatusChoices.DELETED
        )
    
    def hard_delete(self):
        return super(SoftDeletionQuerySet, self).delete()
    
    


class SoftDeletionManager(models.Manager):
    def get_queryset(self):
        from user.models import User
        if hasattr(self, 'instance') and self.instance is not None and isinstance(self.instance,User) and self.instance.object_status == choices.ObjectStatusChoices.DELETED:
            return SoftDeletionQuerySet(self.model)
        else:
            return SoftDeletionQuerySet(self.model).filter(
                object_status=choices.ObjectStatusChoices.ACTIVE
            )
    def complete(self):
        return super().get_queryset()


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,unique=True,editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    object_status = models.SmallIntegerField(
        choices=choices.ObjectStatusChoices.choices,
        default=choices.ObjectStatusChoices.ACTIVE,
    )

    objects = SoftDeletionManager()

    class Meta:
        abstract = True

    def delete(self, hard_delete=False):
        if not hard_delete:
            self.object_status = choices.ObjectStatusChoices.DELETED
            self.save()
            self.delete_related_objs()
        else:
            super().delete()
        # Trigger the post_delete signal to update the ES index
        # TODO: Check how it impacts fields in other indexes
        post_delete.send(sender=self.__class__, instance=self)
    
    def delete_related_objs(self):
        try:
            for related_object in self._meta.related_objects:
                try:
                    if isinstance(related_object, models.OneToOneRel):
                        related_name = related_object.get_accessor_name()
                        related_instance = getattr(self, related_name)
                        if related_instance and hasattr(related_instance,"object_status"):
                            related_instance.object_status = (
                                choices.ObjectStatusChoices.DELETED
                            )
                            related_instance.save()
                        elif related_instance:
                            related_instance.delete()
                        

                    elif isinstance(
                        related_object, (models.ManyToOneRel, models.ManyToManyRel)
                    ):
                        related_name = related_object.get_accessor_name()
                        related_queryset = getattr(self, related_name).all()
                        for related_instance in related_queryset:
                            if hasattr(related_instance,"object_status"):
                                related_instance.object_status = (
                                    choices.ObjectStatusChoices.DELETED
                                )
                                related_instance.save()
                            else:
                                related_instance.delete()

                except Exception as e:
                    continue

        except Exception as e:
            print("$" * 30, e)

    def __str__(self):
        value = self.name if hasattr(self, "name") else getattr(self, "id")
        return "{}".format(value)
    
class SeoModel(models.Model):
    seo_title = models.CharField(
        max_length=70, blank=True, null=True, validators=[MaxLengthValidator(70)]
    )
    seo_description = models.CharField(
        max_length=300, blank=True, null=True, validators=[MaxLengthValidator(300)]
    )

    class Meta:
        abstract = True
    
class PublishableModel(models.Model):
    publish_status = models.CharField(max_length=20,db_index=True,choices=choices.PublishStatusChoices.choices,default=choices.PublishStatusChoices.PUBLISHED)
    published_at = models.DateTimeField(null=True,blank=True)
    
    class Meta:
        abstract =True
        
class PriorityModel(models.Model):
    priority = models.PositiveSmallIntegerField(default=1,help_text="1 is higher than 2")
    
    class Meta:
        abstract =True    

class SlugModel(models.Model):
    slug = models.SlugField(
        max_length=255, db_index=True, unique=True, null=True, allow_unicode=True, blank=True
    )

    def get_slug_field(self):
        return "name"

    def save(self, *args, **kwargs):
        if self.slug == "" or self.slug is None:
            self.slug = utils.generate_unique_slug(self, getattr(self, self.get_slug_field()))
        super().save(*args, **kwargs)

    class Meta:
        abstract = True

    def __str__(self):
        return "{}".format(getattr(self, self.get_slug_field()))
    
class Configuration(BaseModel):
    key = models.CharField(max_length=120, unique=True)
    value = models.TextField(blank=True, default="")
    editable = models.BooleanField(default=True)

    def __str__(self):
        return "{}".format(self.key)

    @classmethod
    def get(cls, key, default="", editable=True):
        default_value = "" if default is None else str(default)
        c, created = Configuration.objects.get_or_create(
            key=key,
            defaults={"value": default_value, "editable": editable},
        )
        return c.value

    @classmethod
    def seed_page_seo(cls, prefix, defaults, overwrite=False):
        """Write {PREFIX}_PAGE_TITLE/DESCRIPTION/KEYWORDS into Configuration."""
        mapping = {
            f"{prefix}_PAGE_TITLE": defaults.get("title", ""),
            f"{prefix}_PAGE_DESCRIPTION": defaults.get("description", ""),
            f"{prefix}_PAGE_KEYWORDS": defaults.get("keywords", ""),
        }
        for key, value in mapping.items():
            if not value:
                continue
            value = str(value)
            if overwrite:
                cls.objects.update_or_create(
                    key=key,
                    defaults={"value": value, "editable": True},
                )
            else:
                cls.objects.get_or_create(
                    key=key,
                    defaults={"value": value, "editable": True},
                )
    
class Contact(BaseModel):
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=100)
    mobile = models.CharField(max_length=10)
    company = models.CharField(max_length=150, blank=True, default="")
    message = models.TextField()
    
    
class NewsletterSubscriber(BaseModel):
    email = models.CharField(max_length=200,unique=True)
    
class TextPlaceholder(BaseModel):
    key = models.CharField(max_length=120,unique=True)
    value = models.TextField()


    def __str__(self):
        return "{}".format(self.key)
    
    @classmethod
    def get(cls,key,default=0,editable=True):
        c,created=TextPlaceholder.objects.get_or_create(key=key,defaults={'value':default})
        return c.value


class Address(BaseModel):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    owner = GenericForeignKey("content_type", "object_id")
    address_type = models.CharField(
        max_length=20,
        choices=choices.AddressTypeChoices.choices,
        default=choices.AddressTypeChoices.HOME,
    )
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            Address.objects.filter(
                content_type=self.content_type,
                object_id=self.object_id,
                is_default=True,
            ).exclude(pk=self.pk).update(is_default=False)

    def __str__(self):
        return "{} - {}, {}".format(self.address_type, self.city, self.pincode)