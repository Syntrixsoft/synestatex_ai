from django.contrib import admin

from .models import Configuration, Contact, NewsletterSubscriber


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "mobile", "company", "created_at")
    search_fields = ("name", "email", "company", "message")
    readonly_fields = ("created_at", "modified_at")


admin.site.register(Configuration)
admin.site.register(NewsletterSubscriber)