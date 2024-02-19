from django.contrib import admin

from console_app import models

# Register your models here.
admin.site.register(models.CustomUser)
admin.site.register(models.UserProfile)
admin.site.register(models.NewTransaction)
admin.site.register(models.CreditingHistory)