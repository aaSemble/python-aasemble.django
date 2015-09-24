from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def index(request):
    if request.user.is_authenticated():
        return render(request, 'overcast/dashboard.html', {})
    else:
        return render(request, 'overcast/front.html', {})

@login_required
def profile(request):
    return render(request, 'overcast/profile.html')
