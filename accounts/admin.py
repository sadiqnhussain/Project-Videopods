from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ("email", "name", "is_google_account", "is_staff", "is_active")
    ordering = ("email",)
    fieldsets = UserAdmin.fieldsets + (
        ("Videopods", {"fields": ("name", "is_google_account")}),
    )
