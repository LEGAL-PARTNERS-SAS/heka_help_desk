from django.contrib import admin
from .models import Ticket, TicketCategory, TicketComment, TicketAttachment, TicketStatusHistory

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display  = ('ticketNumber', 'title', 'status', 'priority', 'createdBy', 'assignedTo', 'createdAt')
    list_filter   = ('status', 'priority', 'area')
    search_fields = ('ticketNumber', 'title')
    ordering      = ('-createdAt',)

admin.site.register(TicketCategory)
admin.site.register(TicketComment)
admin.site.register(TicketAttachment)
admin.site.register(TicketStatusHistory)
