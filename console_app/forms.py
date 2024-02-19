from django import forms
from django.contrib.auth.forms import UserCreationForm

from console_app import models
from console_app.models import CustomUser


class CustomUserForm(UserCreationForm):
    first_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'name', 'placeholder': 'Enter your first name'}))
    last_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'name', 'placeholder': 'Enter your last name'}))
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'username', 'placeholder': 'Enter your username'}))
    business_name = forms.CharField(widget=forms.TextInput(
        attrs={'class': 'form-control', 'id': 'business', 'placeholder': 'Enter your business name'}))
    email = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'email', 'placeholder': 'Enter your email'}))
    phone = forms.CharField(widget=forms.NumberInput(
        attrs={'class': 'form-control', 'id': 'phone', 'placeholder': 'Enter your phone number'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'id': 'password',
                                                                  'placeholder': '&#xb7;&#xb7;&#xb7;&#xb7;&#xb7;&#xb7;&#xb7;&#xb7;&#xb7;&#xb7;&#xb7;&#xb7;'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'id': 'password',
                                                                  'placeholder': '&#xb7;&#xb7;&#xb7;&#xb7;&#xb7;&#xb7;&#xb7;&#xb7;&#xb7;&#xb7;&#xb7;&#xb7;'}))

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'username', 'business_name', 'email', 'phone', 'password1', 'password2']


class CreditingForm(forms.ModelForm):
    user = forms.ModelChoiceField(queryset=models.CustomUser.objects.filter(), empty_label=None,
                                  widget=forms.Select(attrs={"class": "form-control"}))
    credit_amount = forms.FloatField(widget=forms.NumberInput(attrs={"class": "form-control"}))

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     for visible in self.visible_fields():
    #         visible.field.widget.attrs['class'] = 'form-control'
    #         visible.field.widget.attrs['placeholder'] = visible.field.label
    #
    class Meta:
        model = models.CreditingHistory
        fields = ['user', 'credit_amount']
