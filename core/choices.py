from django.db import models


class ObjectStatusChoices(models.IntegerChoices):
    DELETED = 0, "Deleted"
    ACTIVE = 1, "Active"


class PublishStatusChoices(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"


class AccountTypeChoices(models.TextChoices):
    INDIVIDUAL = "INDIVIDUAL", "Individual"
    BUSINESS = "BUSINESS", "Business"
    STAFF = "STAFF", "Staff"


class AccountStatusChoices(models.TextChoices):
    PENDING_VERIFICATION = "PENDING_VERIFICATION", "Pending verification"
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"
    BLOCKED = "BLOCKED", "Blocked"


class AddressTypeChoices(models.TextChoices):
    HOME = "HOME", "Home"
    OFFICE = "OFFICE", "Office"
    SITE = "SITE", "Site"
    BILLING = "BILLING", "Billing"


class AgentSpecializationChoices(models.TextChoices):
    SALE = "SALE", "Sale"
    RENT = "RENT", "Rent"
    BOTH = "BOTH", "Both"
    COMMERCIAL = "COMMERCIAL", "Commercial"


class CompanyTypeChoices(models.TextChoices):
    DEVELOPER = "DEVELOPER", "Developer"
    BUILDER = "BUILDER", "Builder"
    AGENCY = "AGENCY", "Agency"
    PROPERTY_MANAGER = "PROPERTY_MANAGER", "Property manager"


class BranchTypeChoices(models.TextChoices):
    HEAD_OFFICE = "HEAD_OFFICE", "Head office"
    SALES_OFFICE = "SALES_OFFICE", "Sales office"
    SITE_OFFICE = "SITE_OFFICE", "Site office"


class DesignationChoices(models.TextChoices):
    SALES_AGENT = "SALES_AGENT", "Sales agent"
    SR_AGENT = "SR_AGENT", "Senior agent"
    BRANCH_MANAGER = "BRANCH_MANAGER", "Branch manager"
    RELATIONSHIP_MANAGER = "RELATIONSHIP_MANAGER", "Relationship manager"
    CRM_EXECUTIVE = "CRM_EXECUTIVE", "CRM executive"
    COMPANY_ADMIN = "COMPANY_ADMIN", "Company admin"


class EmploymentTypeChoices(models.TextChoices):
    EMPLOYEE = "EMPLOYEE", "Employee"
    FREELANCE = "FREELANCE", "Freelance"
    CHANNEL_PARTNER = "CHANNEL_PARTNER", "Channel partner"


class RoleScopeTypeChoices(models.TextChoices):
    PLATFORM = "PLATFORM", "Platform"
    COMPANY = "COMPANY", "Company"
    BRANCH = "BRANCH", "Branch"
    SELF = "SELF", "Self"


class ResourcePermissionLevelChoices(models.TextChoices):
    VIEW = "VIEW", "View"
    EDIT = "EDIT", "Edit"
    MANAGE = "MANAGE", "Manage"


class OtpPurposeChoices(models.TextChoices):
    SIGNUP = "SIGNUP", "Signup"
    LOGIN = "LOGIN", "Login"
    EMAIL_VERIFY = "EMAIL_VERIFY", "Email verify"
    PHONE_VERIFY = "PHONE_VERIFY", "Phone verify"
    PASSWORD_RESET = "PASSWORD_RESET", "Password reset"


class OtpChannelChoices(models.TextChoices):
    EMAIL = "EMAIL", "Email"
    SMS = "SMS", "SMS"


class OtpStatusChoices(models.TextChoices):
    PENDING = "PENDING", "Pending"
    VERIFIED = "VERIFIED", "Verified"
    EXPIRED = "EXPIRED", "Expired"
    INVALIDATED = "INVALIDATED", "Invalidated"
    FAILED = "FAILED", "Failed"


class CommunicationChannelChoices(models.TextChoices):
    EMAIL = "EMAIL", "Email"
    SMS = "SMS", "SMS"
    WHATSAPP = "WHATSAPP", "WhatsApp"


class CommunicationLogStatusChoices(models.TextChoices):
    SUCCESS = "SUCCESS", "Success"
    FAILED = "FAILED", "Failed"
    PENDING = "PENDING", "Pending"


class SignupSourceChoices(models.TextChoices):
    PHONE_OTP = "PHONE_OTP", "Phone OTP"
    EMAIL_OTP = "EMAIL_OTP", "Email OTP"
    EMAIL_PASSWORD = "EMAIL_PASSWORD", "Email Password"
    GOOGLE = "GOOGLE", "Google"


class InviteStatusChoices(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACCEPTED = "ACCEPTED", "Accepted"
    EXPIRED = "EXPIRED", "Expired"
    REVOKED = "REVOKED", "Revoked"
