from restapi.models import (User, Magnet, MagnetComponent,
                            Match, Action, Place)
from django.contrib import admin


admin.site.register(User)
admin.site.register(Magnet)
admin.site.register(MagnetComponent)
admin.site.register(Match)
admin.site.register(Action)
admin.site.register(Place)
