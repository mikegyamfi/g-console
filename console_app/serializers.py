from rest_framework.serializers import ModelSerializer
from .models import CustomUser, NewTransaction


class UserSerializer(ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'username']


class TransactionSerializer(ModelSerializer):
    class Meta:
        model = NewTransaction
        fields = ["id", 'account_number', 'reference', 'bundle_amount']

