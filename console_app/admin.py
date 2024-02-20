from django.contrib import admin

from console_app import models


class NewTransactionAdmin(admin.ModelAdmin):
    list_per_page = 800
    list_display = ["user", "receiver", "reference", "bundle_amount", "transaction_date",
                    "transaction_status"]
    search_fields = ["receiver", 'reference', "bundle_amount"]


# Register your models here.
admin.site.register(models.CustomUser)
admin.site.register(models.UserProfile)
admin.site.register(models.NewTransaction, NewTransactionAdmin)
admin.site.register(models.CreditingHistory)
