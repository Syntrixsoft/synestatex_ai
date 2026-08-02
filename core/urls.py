from django.urls import path

from . import views

app_name="core"
urlpatterns = [
    path('subscribe/',views.subscribe,name='subscribe'),
    path('contact-submit/', views.submit_contact, name='contact_submit'),
]
