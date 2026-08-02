from django.http import HttpResponse

from .models import Contact, NewsletterSubscriber
import json


def subscribe(request):
    data = {"success": False, "message": "Please provide your email to subscribe."}
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip()
        if email:
            NewsletterSubscriber.objects.get_or_create(email=email)
            data["success"] = True
            data["message"] = "Thank you for subscribing!"
    return HttpResponse(json.dumps(data), content_type="application/json")


def submit_contact(request):
    data = {"success": False, "message": "Please fill all required fields."}

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        email = (request.POST.get("email") or "").strip()
        mobile_raw = (request.POST.get("mobile") or "").strip()
        company = (request.POST.get("company") or "").strip()
        message = (request.POST.get("message") or "").strip()

        if mobile_raw:
            mobile = "".join(char for char in mobile_raw if char.isdigit())[:10]
            if len(mobile) < 10:
                data["message"] = "Please enter a valid 10-digit phone number."
                return HttpResponse(json.dumps(data), content_type="application/json")
        else:
            mobile = "0000000000"

        if name and email and message:
            Contact.objects.create(
                name=name[:100],
                email=email[:100],
                mobile=mobile,
                company=company[:150],
                message=message,
            )
            data["success"] = True
            data["message"] = "Thank you! We received your message."
        else:
            data["message"] = "Name, email and message are required."

    return HttpResponse(json.dumps(data), content_type="application/json")
