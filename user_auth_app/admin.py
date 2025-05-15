from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Profile model.
    """
    list_display = ('username', 'type', 'email', 'is_guest', 'created_at')
    list_filter = ('type', 'is_guest', 'created_at')
    search_fields = ('user__username', 'user__email', 'location')
    readonly_fields = ('created_at',)
    
    def username(self, obj):
        return obj.user.username
    
    def email(self, obj):
        return obj.user.email
