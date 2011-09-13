from gauss.chat.models import Room, ChatMessage
from django.contrib import admin


class RoomAdmin(admin.ModelAdmin):
    pass
    #readonly_fields = ('created')


class ChatMessageAdmin(admin.ModelAdmin):
    pass


admin.site.register(Room, RoomAdmin)
admin.site.register(ChatMessage, ChatMessageAdmin)

