from django.db import transaction
from rest_framework.exceptions import ValidationError

from agent.utils import ensure_agent_profile
from core import choices
from organization.models import Company, CompanyBranch, CompanyMember
from user.models import Role, UserRole


def create_company_member(
    agent_profile,
    company,
    branch=None,
    designation=choices.DesignationChoices.SALES_AGENT,
    employment_type=choices.EmploymentTypeChoices.EMPLOYEE,
):
    has_existing_primary = CompanyMember.objects.filter(
        agent=agent_profile,
        is_primary=True,
        is_active=True,
    ).exists()

    return CompanyMember.objects.create(
        agent=agent_profile,
        company=company,
        branch=branch,
        designation=designation,
        employment_type=employment_type,
        is_primary=not has_existing_primary,
    )


@transaction.atomic
def register_company(user, legal_name, company_type, brand_name=""):
    agent_profile = ensure_agent_profile(user)
    company = Company.objects.create(
        legal_name=legal_name,
        brand_name=brand_name,
        company_type=company_type,
    )
    create_company_member(
        agent_profile,
        company,
        designation=choices.DesignationChoices.COMPANY_ADMIN,
    )
    role, _ = Role.objects.get_or_create(
        code="COMPANY_ADMIN",
        defaults={
            "name": "Company Admin",
            "is_system_role": True,
        },
    )
    UserRole.objects.get_or_create(
        user=user,
        role=role,
        scope_type=choices.RoleScopeTypeChoices.COMPANY,
        scope_id=company.id,
        defaults={"granted_by": user},
    )
    return company


def submit_company_verification(company, rera_number="", gst_number="", documents=None):
    if rera_number:
        company.rera_number = rera_number
    if gst_number:
        company.gst_number = gst_number
    company.is_verified = False
    company.save(update_fields=["rera_number", "gst_number", "is_verified"])
    return {
        "status": "pending_review",
        "rera_number": company.rera_number,
        "gst_number": company.gst_number,
        "documents": documents or [],
    }


def get_company_verification_status(company):
    pending = []
    if not company.rera_number:
        pending.append("rera_number")
    if not company.gst_number:
        pending.append("gst_number")
    return {
        "is_verified": company.is_verified,
        "status": "verified" if company.is_verified else "pending_review",
        "pending": pending,
    }


def create_branch(company, name, city, branch_type=None, floor_number=""):
    return CompanyBranch.objects.create(
        company=company,
        name=name,
        city=city,
        branch_type=branch_type or choices.BranchTypeChoices.SALES_OFFICE,
        floor_number=floor_number,
    )


def list_branches(company):
    return CompanyBranch.objects.filter(company=company, is_active=True)


def get_company(company_id):
    company = Company.objects.filter(pk=company_id).first()
    if company is None:
        raise ValidationError({"detail": "Company not found"})
    return company
