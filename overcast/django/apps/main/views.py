from django.shortcuts import render

def index(request):
    if request.user.is_authenticated():
        return render(request, 'dashboard.html', {})
    else:
        return render(request, 'front.html', {})


