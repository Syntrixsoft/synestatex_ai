from core import choices
from core.utils import get_unique_filename
from django.db import models

def profile_directory(instance,filename):
    filename = get_unique_filename(instance.pk,filename)
    return 'user/profile/{}'.format(filename)
