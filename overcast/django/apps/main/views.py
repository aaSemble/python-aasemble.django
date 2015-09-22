from django.shortcuts import render

def index(request):
    if request.user.is_authenticated():
        return render(request, 'overcast/dashboard.html', {})
    else:
        return render(request, 'overcast/front.html', {})


