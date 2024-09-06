from django.http import HttpResponse

def site_status(request):
    return HttpResponse("This site is working.")