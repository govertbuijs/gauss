# Create your views here.

from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse

def index(request):
    t = get_template('index.html')
    return HttpResponse( t.render(Context({})) )
