from core import choices


OTP_PURPOSE_CONTENT = {
    choices.OtpPurposeChoices.SIGNUP: {
        "label": "account signup",
        "email_subject": "Verify your signup",
        "email_heading": "Complete your signup",
        "email_message": "Use the code below to verify your signup and continue creating your SynEstateX account.",
        "sms_message": "Your SynEstateX signup OTP is {otp_code}. Use it to complete your registration. Valid for {expiry_minutes} min. Do not share.",
    },
    choices.OtpPurposeChoices.LOGIN: {
        "label": "login",
        "email_subject": "Your login code",
        "email_heading": "Login to your account",
        "email_message": "Use the code below to securely log in to your SynEstateX account.",
        "sms_message": "Your SynEstateX login OTP is {otp_code}. Use it to sign in to your account. Valid for {expiry_minutes} min. Do not share.",
    },
    choices.OtpPurposeChoices.EMAIL_VERIFY: {
        "label": "email verification",
        "email_subject": "Verify your email address",
        "email_heading": "Verify your email",
        "email_message": "Use the code below to verify your email address on SynEstateX.",
        "sms_message": "Your SynEstateX email verification OTP is {otp_code}. Use it to verify your email. Valid for {expiry_minutes} min. Do not share.",
    },
    choices.OtpPurposeChoices.PHONE_VERIFY: {
        "label": "phone verification",
        "email_subject": "Verify your phone number",
        "email_heading": "Verify your phone number",
        "email_message": "Use the code below to verify your phone number on SynEstateX.",
        "sms_message": "Your SynEstateX phone verification OTP is {otp_code}. Use it to verify your mobile number. Valid for {expiry_minutes} min. Do not share.",
    },
    choices.OtpPurposeChoices.PASSWORD_RESET: {
        "label": "password reset",
        "email_subject": "Reset your password",
        "email_heading": "Reset your password",
        "email_message": "Use the code below to reset your SynEstateX account password.",
        "sms_message": "Your SynEstateX password reset OTP is {otp_code}. Use it to reset your password. Valid for {expiry_minutes} min. Do not share.",
    },
}


def get_otp_purpose_content(purpose, otp_code, expiry_minutes):
    content = OTP_PURPOSE_CONTENT.get(
        purpose,
        {
            "label": "verification",
            "email_subject": "Your verification code",
            "email_heading": "Verification required",
            "email_message": "Use the code below to complete your verification on SynEstateX.",
            "sms_message": "Your SynEstateX verification OTP is {otp_code}. Valid for {expiry_minutes} min. Do not share.",
        },
    )
    return {
        "purpose": purpose,
        "purpose_label": content["label"],
        "email_subject": content["email_subject"],
        "email_heading": content["email_heading"],
        "email_message": content["email_message"],
        "sms_message": content["sms_message"].format(
            otp_code=otp_code,
            expiry_minutes=expiry_minutes,
        ),
    }
