from django.utils.text import slugify
from typing import Type, Union, TYPE_CHECKING
from django.db.models import Model
from django.urls import reverse
import string
import random


if TYPE_CHECKING:
    from django.utils.safestring import SafeText

def get_unique_filename(instance_id,filename,length=16):
    ext = filename.split('.')[-1]
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    filename = 'syntrixsoft-{}.{}'.format(random_suffix,ext)
    return filename

def generate_unique_slug(
    instance: Type[Model],
    slugable_value: str,
    slug_field_name: str = "slug",
) -> str:
    """Create unique slug for model instance.

    The function uses `django.utils.text.slugify` to generate a slug from
    the `slugable_value` of model field. If the slug already exists it adds
    a numeric suffix and increments it until a unique value is found.

    Args:
        instance: model instance for which slug is created
        slugable_value: value used to create slug
        slug_field_name: name of slug field in instance model

    """
    slug = slugify(slugable_value, allow_unicode=True)
    unique_slug: Union["SafeText", str] = slug

    ModelClass = instance.__class__
    extension = 1

    search_field = f"{slug_field_name}__iregex"
    pattern = rf"{slug}-\d+$|{slug}$"
    slug_values = (
        ModelClass._default_manager.complete().filter(**{search_field: pattern})  # type: ignore
        .exclude(pk=instance.pk)
        .values_list(slug_field_name, flat=True)
    )

    while unique_slug in slug_values:
        extension += 1
        unique_slug = f"{slug}-{extension}"

    return unique_slug


