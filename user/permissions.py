from django.utils import timezone
from rest_framework.permissions import BasePermission

from core import choices
from user.models import ResourcePermission, RolePermission, UserRole


def role_has_permission(role, permission_code):
    return RolePermission.objects.filter(
        role=role,
        permission__code=permission_code,
        object_status=choices.ObjectStatusChoices.ACTIVE,
    ).exists()


def _active_user_roles(user, scope_type=None, scope_id=None):
    qs = UserRole.objects.filter(
        user=user,
        is_active=True,
        object_status=choices.ObjectStatusChoices.ACTIVE,
    )
    if scope_type:
        qs = qs.filter(scope_type=scope_type)
    if scope_id:
        qs = qs.filter(scope_id=scope_id)
    return [role for role in qs.select_related("role") if role.is_currently_valid]


def user_has_permission(
    user,
    permission_code,
    company_id=None,
    branch_id=None,
    resource_type=None,
    resource_id=None,
    owner_user_id=None,
):
    if not user or not user.is_authenticated:
        return False

    for user_role in _active_user_roles(user, choices.RoleScopeTypeChoices.PLATFORM):
        if role_has_permission(user_role.role, permission_code):
            return True

    if owner_user_id and str(user.id) == str(owner_user_id):
        return True

    if company_id:
        for user_role in _active_user_roles(
            user, choices.RoleScopeTypeChoices.COMPANY, company_id
        ):
            if role_has_permission(user_role.role, permission_code):
                return True

    if branch_id:
        for user_role in _active_user_roles(
            user, choices.RoleScopeTypeChoices.BRANCH, branch_id
        ):
            if role_has_permission(user_role.role, permission_code):
                return True

    if resource_type and resource_id:
        grant = (
            ResourcePermission.objects.filter(
                user=user,
                resource_type=resource_type,
                resource_id=resource_id,
                object_status=choices.ObjectStatusChoices.ACTIVE,
            )
            .order_by("-granted_at")
            .first()
        )
        if grant and grant.is_currently_valid:
            return True

    return False


class HasCompanyPermission(BasePermission):
    required_permission_code = None

    def has_permission(self, request, view):
        permission_code = (
            getattr(view, "required_permission_code", None)
            or self.required_permission_code
        )
        if not permission_code:
            return False

        company_id = view.kwargs.get("company_id") or request.data.get("company_id")
        branch_id = view.kwargs.get("branch_id") or request.data.get("branch_id")
        return user_has_permission(
            request.user,
            permission_code,
            company_id=company_id,
            branch_id=branch_id,
            owner_user_id=getattr(view, "owner_user_id", None),
        )
