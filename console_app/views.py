import calendar
import random
import string
from datetime import datetime, timedelta

from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.db.models import Sum, Max
from django.http import HttpResponse
from django.shortcuts import render

# Create your views here.
import secrets

import requests
from decouple import config

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.safestring import mark_safe
from django.urls import reverse_lazy
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response

from console_app import models, helper, forms
from console_app.forms import CustomUserForm


# Create your views here.
@login_required(login_url='login')
def home(request):
    user_profile_data = models.UserProfile.objects.filter(user=request.user).first()
    print(user_profile_data.bundle_balance)
    current_month = datetime.now().month
    current_month_text = datetime.now().strftime('%B')
    most_recent_credit_history = models.CreditingHistory.objects.filter(user=request.user).order_by('-date').first()
    current_year = datetime.now().year
    transactions_count = models.NewTransaction.objects.filter(user=request.user).count()
    total_bundle_volume = models.NewTransaction.objects.filter(transaction_date__year=current_year,
                                                               transaction_date__month=current_month, user=request.user) \
        .aggregate(total_bundle_volume=Sum('bundle_amount')) \
        .get('total_bundle_volume', 0)
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    most_recent_5_txns = models.NewTransaction.objects.filter(user=request.user).order_by('-transaction_date')[:5]

    daily_totals = models.NewTransaction.objects.filter(transaction_date__gte=thirty_days_ago, user=request.user) \
        .values('transaction_date__date') \
        .annotate(total_bundle=Sum('bundle_amount'))

    # Organize the data for plotting
    dates = [daily_total['transaction_date__date'] for daily_total in daily_totals]
    formatted_dates = [date.strftime('%d %b') for date in dates]
    totals = [daily_total['total_bundle'] for daily_total in daily_totals]
    context = {
        'data': user_profile_data,
        'count': transactions_count,
        'total_for_month': total_bundle_volume,
        'month': current_month_text,
        'year': current_year,
        'recent_credit': most_recent_credit_history,
        'dates': formatted_dates,
        'totals': totals,
        'txns': most_recent_5_txns,
        'balance': user_profile_data.bundle_balance / 1000
    }
    return render(request, 'layouts/index.html', context=context)


@login_required(login_url='login')
def user_profile(request):
    if request.method == "POST":
        business_name = request.POST.get("business")
        phone = request.POST.get("phoneNumber")
        sms_api = request.POST.get("sms")
        email = request.POST.get("email")

        updated_user = models.UserProfile.objects.filter(user=request.user).first()
        updated_user.business_name = business_name
        updated_user.phone = phone
        updated_user.sms_api = sms_api

        user = models.CustomUser.objects.filter(id=request.user.id).first()
        user.email = email

        updated_user.save()
        user.save()
        messages.success(request, "Profile Updated Successfully")
    user_profile_details = models.UserProfile.objects.filter(user=request.user).first()
    user = request.user
    context = {'data': user_profile_details, 'user': user}
    return render(request, 'layouts/account_details.html', context=context)


@login_required(login_url='login')
def send_bundle_page(request):
    if request.method == "POST":
        receiver = request.POST.get("receiver")
        amount = int(request.POST.get("volume"))

        print(receiver)
        print(amount)

        reference = f"{request.user.username}-{secrets.token_hex(3)}".upper()
        print(receiver)
        print(amount)

        current_user = models.UserProfile.objects.filter(user=request.user).first()

        if amount > int(current_user.bundle_balance):
            print("small")
            messages.error(request, "You do not have enough balance to perform this transaction")
            return redirect('send_bundle_page')
        else:
            send_bundle_response = helper.send_bundle(request.user, receiver, amount, reference)
            print(send_bundle_response)

            sms_headers = {
                'Authorization': 'Bearer 1136|LwSl79qyzTZ9kbcf9SpGGl1ThsY0Ujf7tcMxvPze',
                'Content-Type': 'application/json'
            }

            sms_url = 'https://webapp.usmsgh.com/api/sms/send'
            if send_bundle_response != "bad response":
                print("good response")
                if send_bundle_response["data"]["request_status_code"] == "200" or send_bundle_response[
                    "request_message"] == "Successful":
                    new_txn = models.NewTransaction.objects.create(
                        user=request.user,
                        account_number=receiver,
                        bundle_amount=amount,
                        reference=reference,
                        transaction_status="Completed",
                        mode="Console"
                    )
                    new_txn.save()
                    current_user.bundle_balance -= float(amount)
                    current_user.save()
                    receiver_message = f"Your bundle purchase has been completed successfully. {amount}MB has been credited to you by {current_user.phone}.\nReference: {reference}\n"
                    sms_message = f"Hello @{request.user.username}. Your bundle purchase has been completed successfully. {amount}MB has been credited to {receiver}.\nReference: {reference}\nCurrent Wallet Balance: {current_user.bundle_balance}\nThank you for using Geosams.\n\nGeosams"

                    try:
                        response1 = requests.get(
                            f"https://sms.arkesel.com/sms/api?action=send-sms&api_key={current_user.sms_api}&to=0{current_user.phone}&from={current_user.business_name}&sms={sms_message}")
                        print(response1.text)

                        response2 = requests.get(
                            f"https://sms.arkesel.com/sms/api?action=send-sms&api_key={current_user.sms_api}&to={receiver}&from={current_user.business_name}&sms={receiver_message}")
                        print(response2.text)
                    except:
                        messages.success(request, "Transaction was completed successfully")
                        return redirect(send_bundle_page)
                    messages.success(request, "Transaction was completed successfully")
                    return redirect(send_bundle_page)
                else:
                    new_txn = models.NewTransaction.objects.create(
                        user=request.user,
                        account_number=receiver,
                        bundle_amount=amount,
                        reference=reference,
                        transaction_status="Failed",
                        mode="Console"
                    )
                    new_txn.save()
                    messages.error(request, "Something went wrong on our end. Try again later")
                    return redirect(send_bundle_page)
            else:
                messages.error(request, "Something went wrong on our end. Try again later")
                return redirect(send_bundle_page)

    user_profile_data = models.UserProfile.objects.filter(user=request.user).first()
    context = {'data': user_profile_data}

    return render(request, 'layouts/send_bundle.html', context=context)


@login_required(login_url='login')
def transaction_history(request):
    transactions = models.NewTransaction.objects.filter(user=request.user).order_by('transaction_date').reverse()[:100]
    user_profile_data = models.UserProfile.objects.filter(user=request.user).first()
    context = {'txns': transactions, 'data': user_profile_data}
    return render(request, 'layouts/account_history.html', context=context)


def register(request):
    form = CustomUserForm()
    if request.method == 'POST':
        form = CustomUserForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get("username")
            phone_number = form.cleaned_data.get("phone")
            business_name = form.cleaned_data.get("business_name")
            user = models.CustomUser.objects.get(username=username)
            user.user_id = f"GS{secrets.token_hex(3)}".upper()
            user_profile_data = models.UserProfile.objects.create(
                user=user,
                phone=phone_number,
                business_name=business_name,
                bundle_balance=0
            )
            user.save()
            user_profile_data.save()
            messages.success(request, "Sign Up Successful. Your account creation has been submitted for approval.")
            return redirect('login')
    context = {'form': form}
    return render(request, 'auth/authentication-register.html', context=context)


def loginpage(request):
    if request.user.is_authenticated:
        messages.warning(request, "You are already logged in")
        return redirect('home')
    else:
        if request.method == 'POST':
            name = request.POST.get('username')
            password = request.POST.get('password')

            user = authenticate(request, username=name, password=password)
            if user:
                if user.account_approved:
                    login(request, user)
                    messages.success(request, 'Log in Successful')
                    return redirect('home')
                else:
                    messages.warning(request, "Account Approval Pending")
                    return redirect('login')
            else:
                messages.error(request, 'Invalid username or password')
                return redirect('login')
    return render(request, "auth/authentication-login.html")


@login_required(login_url='login')
def pending_approvals(request):
    if request.user.is_staff or request.user.is_superuser:
        approvals = models.CustomUser.objects.filter(account_approved=False).reverse()
        for approval in approvals:
            print(approval)
        profiles = [models.UserProfile.objects.get(user=approval) for approval in approvals]
        context = {'approvals': approvals, 'profiles': profiles}
        return render(request, "layouts/pending_approvals.html", context=context)
    else:
        messages.error(request, "Access Denied")
        return redirect('home')


def change_approval_status(request, approval_id, app_status):
    if request.user.is_staff:
        approval = models.CustomUser.objects.filter(account_approved=False, id=approval_id).first()
        if approval:
            current_user = models.UserProfile.objects.get(user=approval)
            approval.account_approved = True if app_status == "True" else False
            approval.approval_date = timezone.now()
            statuss = "approved" if app_status == "True" else "denied"
            approval.save()
            receiver_message = f"Account Creation.\n\nHello {approval.first_name},\nYour Geosams Console account has been {statuss}."

            response1 = requests.get(
                f"https://sms.arkesel.com/sms/api?action=send-sms&api_key=UnBzemdvanJyUGxhTlJzaVVQaHk&to=0{current_user.phone}&from=GEO_AT&sms={receiver_message}")
            print(response1.text)
        return redirect('pending_approvals')
    else:
        messages.error(request, "Access Denied")
        return redirect('login')


@login_required(login_url='login')
def logout_user(request):
    logout(request)
    messages.success(request, "Log out successful")
    return redirect('login')


def generate_tokenn(length):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


@login_required(login_url='login')
def api_page(request):
    if request.method == "POST":
        try:
            user = models.CustomUser.objects.get(id=request.user.id)
            try:
                token = Token.objects.get(user=user)
                token.delete()
            except Token.DoesNotExist:
                pass

            token_key = generate_tokenn(150)
            token = Token.objects.create(user=user, key=token_key)
            messages.success(request, "Token Generation Successful")
            return redirect('token_management')
        except:
            messages.error(request, "Something went wrong")
            return redirect('token_management')
    user_profile_data = models.CustomUser.objects.get(id=request.user.id)
    user = request.user
    try:
        user = models.CustomUser.objects.get(id=user.id)
        try:
            token = Token.objects.get(user=user)
            bearer = token.key
        except Token.DoesNotExist:
            token = None
    except models.CustomUser.DoesNotExist:
        messages.success(request, "Invalid Request")
        return redirect('login')
    context = {'data': user_profile_data, 'token': token}
    return render(request, "layouts/token_mgt.html", context=context)


@login_required(login_url='login')
def crediting_page(request):
    form = forms.CreditingForm()
    if request.user.is_staff or request.user.is_superuser:
        if request.method == "POST":
            form = forms.CreditingForm(request.POST)
            if form.is_valid():
                user = form.cleaned_data["user"]
                amount = form.cleaned_data["credit_amount"]
                user_credited = models.CustomUser.objects.get(id=user.id)
                print(user_credited.username)
                user_profile_credited = models.UserProfile.objects.get(user=user)
                previous_balance = user_profile_credited.bundle_balance
                user_profile_credited.bundle_balance += float(amount)
                user_profile_credited.save()
                new_credit = models.CreditingHistory(user=user_credited, amount_credited=amount)
                new_credit.save()
                receiver_message = f"Your GoeSams console account has been successfully credited with {amount}MB.\nPrev Balance: {previous_balance}MB\nNew Balance:{user_profile_credited.bundle_balance}MB"
                # quicksend_url = "https://uellosend.com/quicksend/"
                # data = {
                #     'api_key': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.=eyJkYXRhIjp7InVzZXJpZCI6MTU5MiwiYXBpU2VjcmV0IjoiaFY2YjNDcHR1PW9wQnB2IiwiaXNzdWVyIjoiVUVMTE9TRU5EIn19',
                #     'sender_id': "BESTPAY GH",
                #     'message': receiver_message,
                #     'recipient': f"0{user_profile_credited.phone}"
                # }

                # headers = {'Content-type': 'application/json'}
                #
                # response = requests.post(quicksend_url, headers=headers, json=data)
                # print(response.json())
                messages.success(request,
                                 f"{user_credited.username}'s account credited successfully with {amount}MB")
                return redirect("crediting")
        context = {"form": form}
        return render(request, "layouts/credit_account.html", context=context)
    else:
        messages.error(request, "Access Denied")
        return redirect('home')


@login_required(login_url='login')
def credit_history(request):
    credits_txn = models.CreditingHistory.objects.filter(user=request.user).order_by('date').reverse()
    user_profile_data = models.UserProfile.objects.filter(user=request.user).first()
    context = {'txns': credits_txn, 'data': user_profile_data}
    return render(request, 'layouts/credit_history.html', context=context)


@login_required(login_url='login')
def query_transaction(request):
    if request.method == "POST":
        reference = request.POST.get("reference")
    #
    #     user = models.CustomUser.objects.get(id=request.user.id)
    #     print(user.username)
    #     headers = {
    #         "api-key": user.api_key,
    #         "api-secret": user.api_secret
    #     }
    #     # response = requests.get(url=f"https://console.bestpaygh.com/flexi/v1/transaction_detail/{reference.strip()}/", headers=headers)
    #     # data = response.json()
    #     # print(data)
    #     response = api_views.TransactionDetail().post(request, reference.strip()).data
    #     print("query response")
    #     print(response)
    #     if response["code"] == "0000":
    #         messages.info(request,
    #                       f"Message: {response['api_response']['message']} - {response['api_response']['recipient']} - {response['api_response']['shared_bundle']}MB")
    #     else:
    #         messages.info(request, f"Message: {response['message']}")
    #     return redirect("query_transaction")
    return render(request, "layouts/query_txn.html")


@login_required(login_url='login')
def all_transactions(request):
    all_users_transactions = models.NewTransaction.objects.all().order_by("transaction_date").reverse()
    context = {"txns": all_users_transactions}
    return render(request, "layouts/admin-all-txns.html", context=context)


def get_bundle_amount_by_user_for_month(year, month):
    start_date = datetime(year, month, 1)
    end_date = start_date + timedelta(days=30)
    bundle_amounts = models.NewTransaction.objects.filter(transaction_date__gte=start_date,
                                                          transaction_date__lt=end_date) \
        .values('user__username') \
        .annotate(total_bundle_amount=Sum('bundle_amount')) \
        .order_by('-total_bundle_amount')  # Order by total_bundle_amount descending

    # Get the user with the highest bundle amount
    user_with_highest_bundle_amount = bundle_amounts.first()

    # Get the highest bundle amount
    highest_bundle_amount = bundle_amounts.aggregate(highest_bundle_amount=Max('total_bundle_amount'))[
        'highest_bundle_amount']

    return bundle_amounts, user_with_highest_bundle_amount, highest_bundle_amount


@login_required(login_url='login')
def bundle_amount_graph(request):
    if request.user.is_staff or request.user.is_superuser:
        if request.method == 'POST':
            selected_month = int(request.POST['month'])
            selected_year = int(request.POST['year'])
        else:
            selected_month = datetime.now().month
            selected_year = datetime.now().year

        try:

            selected_month_name = calendar.month_name[selected_month]

            bundle_amounts, user_with_highest_bundle_amount, highest_bundle_amount = get_bundle_amount_by_user_for_month(selected_year, selected_month)

            # Format data for plotting
            usernames = [bundle['user__username'] for bundle in bundle_amounts]
            total_bundle_amounts = [bundle['total_bundle_amount'] for bundle in bundle_amounts]
            print(user_with_highest_bundle_amount)

            context = {
                'usernames': usernames,
                'total_bundle_amounts': total_bundle_amounts,
                'user_with_highest_bundle_amount': models.CustomUser.objects.get(username=user_with_highest_bundle_amount['user__username']),
                'highest_bundle_amount': highest_bundle_amount / 1000,
                'selected_month': selected_month,
                'selected_month_name': selected_month_name
            }
        except:
            messages.warning(request, 'No record Found')
            return redirect('bundle_amount_graph')
        return render(request, "layouts/bundle_amount_graph.html", context=context)
    else:
        messages.warning(request, "Access Denied")
        return redirect('home')


def password_reset_request(request):
    if request.method == "POST":
        password_reset_form = PasswordResetForm(request.POST)
        if password_reset_form.is_valid():
            data = password_reset_form.cleaned_data['email']
            user = models.CustomUser.objects.filter(email=data).first()
            current_user = models.UserProfile.objects.get(user=user)
            if user:
                subject = "Password Reset Requested"
                email_template_name = "password/password_reset_message.txt"
                c = {
                    "name": user.first_name,
                    "email": user.email,
                    'domain': 'localhost:8000',
                    'site_name': 'Geosams Console',
                    "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                    "user": user,
                    'token': default_token_generator.make_token(user),
                    'protocol': 'http',
                }
                email = render_to_string(email_template_name, c)
                requests.get(
                    f"https://sms.arkesel.com/sms/api?action=send-sms&api_key=UnBzemdvanJyUGxhTlJzaVVQaHk&to=0{current_user.phone}&from=GEO_AT&sms={email}")
                return redirect("/password_reset/done/")
    password_reset_form = PasswordResetForm()
    return render(request=request, template_name="password/password_reset.html",
                  context={"password_reset_form": password_reset_form})
