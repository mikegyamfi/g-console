import json
import random
import string

import requests
from decouple import config
from django.db import IntegrityError
from django.http import JsonResponse
from django.utils.crypto import get_random_string
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.hashers import make_password
from rest_framework import status

from .. import models, helper
from ..models import CustomUser, NewTransaction
from ..serializers import TransactionSerializer


class BearerTokenAuthentication(TokenAuthentication):
    keyword = 'Bearer'


def generate_tokenn(length):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def generate_token(request):
    username = request.data.get('username')
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')
    email = request.data.get('email')
    if username and first_name and last_name and email:
        try:
            if models.CustomUser.objects.filter(username=username).exists():
                user = CustomUser.objects.get(username=username)
                token_key = generate_tokenn(150)
                token = Token.objects.create(user=user, key=token_key)
                return Response({'token': token.key, 'message': 'Token Generation Successful'},
                                status=status.HTTP_200_OK)
            user = models.CustomUser.objects.create_user(username=username, first_name=first_name, last_name=last_name, email=email,)
            token_key = generate_tokenn(150)
            token = Token.objects.create(user=user, key=token_key)
            return Response({'token': token.key, 'message': 'Token Generation Successful'}, status=status.HTTP_200_OK)
        except IntegrityError:
            return Response({'message': 'User already exists!'}, status=status.HTTP_409_CONFLICT)
    else:
        return Response({'message': 'Username and password are required.'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def regenerate_token(request):
    user_id = request.data.get('user_id')
    try:
        user = models.CustomUser.objects.get(user_id=user_id)
        try:
            token = Token.objects.get(user=user)
            token.delete()
        except Token.DoesNotExist:
            pass

        token_key = generate_tokenn(150)
        token = Token.objects.create(user=user, key=token_key)
        return Response({'user_id': user_id, 'token': token.key, 'message': 'Token Generation Successful'},
                        status=status.HTTP_200_OK)
    except models.CustomUser.DoesNotExist:
        return Response({'error': 'User does not exist.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(["GET"])
def transactions(request):
    all_transactions = NewTransaction.objects.all().order_by("transaction_date").reverse()
    serializer = TransactionSerializer(all_transactions, many=True)
    return JsonResponse({"transactions": serializer.data}, safe=True)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([BearerTokenAuthentication])
def new_transaction(request):
    authorization_header = request.headers.get('Authorization')
    if authorization_header:
        auth_type, token = authorization_header.split(' ')
        if auth_type == 'Bearer':
            try:
                token_obj = Token.objects.get(key=token)
                user = token_obj.user

                user_profile = models.UserProfile.objects.get(user=user)

                serializer = TransactionSerializer(data=request.data)
                if serializer.is_valid():
                    phone_number = serializer.validated_data.get('account_number')
                    reference = serializer.validated_data.get('reference')
                    bundle_volume = serializer.validated_data.get('bundle_amount')

                    if user_profile.bundle_balance < bundle_volume:
                        return Response(data={"status": "Failed", "error": "Insufficient Balance",
                                              "message": "You do not have enough balance to perform this transaction"},
                                        status=status.HTTP_400_BAD_REQUEST)

                    if models.NewTransaction.objects.filter(user=user, reference=reference).exists():
                        return Response(data={"status": "Failed", "error": "Duplicate Error",
                                              "message": "Transaction reference already exists"},
                                        status=status.HTTP_409_CONFLICT)
                    send_bundle_response = helper.send_bundle(request.user, phone_number, bundle_volume, reference)
                    print(send_bundle_response)

                    sms_headers = {
                        'Authorization': 'Bearer 1136|LwSl79qyzTZ9kbcf9SpGGl1ThsY0Ujf7tcMxvPze',
                        'Content-Type': 'application/json'
                    }

                    sms_url = 'https://webapp.usmsgh.com/api/sms/send'
                    if send_bundle_response != "bad response":
                        print("good response")
                        if send_bundle_response["data"]["request_status_code"] == "200" or send_bundle_response["request_message"] == "Successful":
                            new_txn = models.NewTransaction.objects.create(
                                user=request.user,
                                bundle_number=phone_number,
                                offer=f"{bundle_volume}MB",
                                reference=reference,
                                transaction_status="Completed"
                            )
                            new_txn.save()
                            user_profile.bundle_balance -= float(bundle_volume)
                            user.save()
                            receiver_message = f"Your bundle purchase has been completed successfully. {bundle_volume}MB has been credited to you by {request.user.phone}.\nReference: {reference}\n"
                            sms_message = f"Hello @{request.user.username}. Your bundle purchase has been completed successfully. {bundle_volume}MB has been credited to {phone_number}.\nReference: {reference}\nCurrent Wallet Balance: {user_profile.bundle_balance}\nThank you for using Geosams.\n\nGeosams"

                            response1 = requests.get(
                                f"https://sms.arkesel.com/sms/api?action=send-sms&api_key=UnBzemdvanJyUGxhTlJzaVVQaHk&to=0{request.user.phone}&from=GEO_AT&sms={sms_message}")
                            print(response1.text)

                            response2 = requests.get(
                                f"https://sms.arkesel.com/sms/api?action=send-sms&api_key=UnBzemdvanJyUGxhTlJzaVVQaHk&to={phone_number}&from=GEO_AT&sms={receiver_message}")
                            print(response2.text)
                            return Response(
                                data={"status": "Success",
                                      "message": "Transaction was completed successfully",
                                      "reference": reference},
                                status=status.HTTP_200_OK)
                        else:
                            new_txn = models.NewTransaction.objects.create(
                                user=request.user,
                                bundle_number=phone_number,
                                offer=f"{bundle_volume}MB",
                                reference=reference,
                                transaction_status="Failed"
                            )
                            new_txn.save()
                            return Response(
                                data={"status": "Incomplete",
                                      "message": "Something went wrong on our end. Try again later",
                                      "reference": reference},
                                status=status.HTTP_503_SERVICE_UNAVAILABLE)
                else:
                    return Response(
                        data={"code": "0001", "status": "Failed", "error": "Body error",
                              "message": "Body Parameters set not valid. Check and try again."},
                        status=status.HTTP_400_BAD_REQUEST)
            except Token.DoesNotExist:
                return Response({'error': 'Token does not exist.'}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({'error': 'Invalid Header Provided.'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([BearerTokenAuthentication])
def transaction_detail(request):

    def post(self, request, reference):
        response = ValidateAPIKeysView().post(request)
        print(response.data)

        if response.data["valid"]:
            api_key = request.headers.get("api-key")
            print(api_key)
            if api_key:
                print("yhp")
                user = CustomUser.objects.get(api_key=api_key)
            else:
                print("nope")
                print("using this instead")
                user = CustomUser.objects.get(id=request.user.id)
                print(user)
            wanted_transaction = NewTransaction.objects.filter(reference=reference, user=user).first()
            print(wanted_transaction)
            if wanted_transaction:
                print(wanted_transaction.batch_id)
                batch_id = wanted_transaction.batch_id
                url = f"https://backend.boldassure.net:445/live/api/context/business/airteltigo-gh/ishare/tranx-status/{batch_id}"

                payload = {}
                headers = {
                    'Authorization': config("BEARER_TOKEN")
                }

                response = requests.request("GET", url, headers=headers, data=payload)
                data = response.json()
                print(data)
                try:
                    code = data["flexiIshareTranxStatus"]["flexiIshareTranxStatusResult"]["apiResponse"]["responseCode"]
                except:
                    return Response(data={"code": "0001", "error": "Query Failed", "status": "Failed",
                                          "message": "Could not query transaction"}, status=status.HTTP_200_OK)

                if code == "200":
                    message = data["flexiIshareTranxStatus"]["flexiIshareTranxStatusResult"]["apiResponse"][
                        "responseMsg"]
                    shared_bundle = data["flexiIshareTranxStatus"]["flexiIshareTranxStatusResult"]["sharedBundle"]
                    recipient = \
                        data["flexiIshareTranxStatus"]["flexiIshareTranxStatusResult"]["recipientDetails"][
                            "recipientParams"][
                            0]["recipientMsisdn"]
                    recipient_message = \
                        data["flexiIshareTranxStatus"]["flexiIshareTranxStatusResult"]["recipientDetails"][
                            "recipientParams"][
                            0]["responseMsg"]
                    data_response = {
                        "api_response": {
                            "message": message,
                            "shared_bundle": shared_bundle,
                            "recipient": recipient,
                            "recipient_bundle_status": recipient_message},
                        "code": "0000",
                        "reference": reference,
                        "batch_id": batch_id,
                        "query_status": "Success"
                    }
                    return Response(data=data_response, status=status.HTTP_200_OK)
            else:
                return Response(data={"code": "0001", "status": "Failed", "error": "Transaction not found",
                                      "message": "The reference entered matches no transaction"},
                                status=status.HTTP_200_OK)
            if code == "204":
                return Response(data={"code": "0001", "status": "Failed", "error": "Not Found",
                                      "message": "No record for this transaction. Check reference and try again"},
                                status=status.HTTP_200_OK)
            if code == "205":
                recipient = \
                    data["flexiIshareTranxStatus"]["flexiIshareTranxStatusResult"]["recipientDetails"][
                        "recipientParams"][
                        0][
                        "recipientMsisdn"]
                return Response(data={"code": "0001", "status": "Failed", "error": "Invalid Recipient",
                                      "message": "The recipient number provided was invalid", "recipient": recipient},
                                status=status.HTTP_200_OK)
        else:
            return Response(data={"code": "0001", "error": "Authentication error",
                                  "status": "Failed",
                                  "message": "Unable to authenticate using Authentication keys. Check and try again."},
                            status=status.HTTP_401_UNAUTHORIZED)


@api_view(["GET"])
def user_balance(request):
    response = ValidateAPIKeysView().post(request)
    data = response.data

    if data["valid"]:
        try:
            user = models.CustomUser.objects.get(api_key=request.headers.get("api-key"))
        except models.CustomUser.DoesNotExist:
            return Response(data={"code": "0001", "message": "User not found"}, status=status.HTTP_200_OK)
        user_profile = models.UserProfile.objects.get(user=user)
        print(user_profile)
        user_bundle_balance = user_profile.bundle_amount if user_profile.bundle_amount else 0
        return Response(
            data={"code": "0000", "user": f"{user.first_name} {user.last_name}", "bundle_balance": user_bundle_balance},
            status=status.HTTP_200_OK)
    else:
        return Response(data={"code": "0001", "error": "Authentication error",
                              "status": "Failed",
                              "message": "Unable to authenticate using Authentication keys. Check and try again."},
                        status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([BearerTokenAuthentication])
def null_transaction_query(request):
    return Response(data={"code": "0001", "status": "Failed", "error": "Null Reference",
                          "message": "Provide a valid reference to query"}, status=status.HTTP_200_OK)


@permission_classes([IsAuthenticated])
@authentication_classes([BearerTokenAuthentication])
@api_view(["GET"])
def get_all_transactions(request):
    authorization_header = request.headers.get('Authorization')
    if authorization_header:
        auth_type, token = authorization_header.split(' ')
        if auth_type == 'Bearer':
            try:
                token_obj = Token.objects.get(key=token)
                user = token_obj.user

                user_profile = models.UserProfile.objects.get(user=user)
                all_txns = models.NewTransaction.objects.filter(user=user)
                return Response(all_txns, status=status.HTTP_200_OK)
            except Token.DoesNotExist:
                return Response(data={"status": "Failed", "error": "No account found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response(data={"error": "Authentication error",
                                  "status": "Failed",
                                  "message": "Invalid Token. Check and try again."},
                            status=status.HTTP_401_UNAUTHORIZED)
    else:
        return Response(data={"error": "Authentication error",
                              "status": "Failed",
                              "message": "Invalid Token. Check and try again."},
                        status=status.HTTP_401_UNAUTHORIZED)
