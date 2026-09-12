from django.contrib import admin

from .models import Company, CompanyBranch, CompanyMember

admin.site.register(Company)
admin.site.register(CompanyBranch)
admin.site.register(CompanyMember)
