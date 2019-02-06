from django.http import HttpResponse


def custom_submit_review(request):
    return HttpResponse("Hello from the custom submit review view.")
