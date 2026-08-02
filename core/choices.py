from django.db import models
            
class ObjectStatusChoices(models.IntegerChoices):
    DELETED = 0, "Deleted"
    ACTIVE = 1, "Active"
    
class PublishStatusChoices(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    


