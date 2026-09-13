from django.contrib import admin

from .models import Company, CompanyBranch, CompanyInvite, CompanyMember

admin.site.register(Company)
admin.site.register(CompanyBranch)
admin.site.register(CompanyMember)
admin.site.register(CompanyInvite)
