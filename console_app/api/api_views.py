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
                    status_code, send_bundle_response = helper.send_bundle(request.user, phone_number, bundle_volume, reference)
                    print(send_bundle_response)

                    sms_headers = {
                        'Authorization': 'Bearer 1136|LwSl79qyzTZ9kbcf9SpGGl1ThsY0Ujf7tcMxvPze',
                        'Content-Type': 'application/json'
                    }

                    sms_url = 'https://webapp.usmsgh.com/api/sms/send'
                    if send_bundle_response != "bad response":
                        print("good response")
                        if (
                                status_code == 200 and send_bundle_response['data']['request_status_code'] == '200'
                        ):
                            user_profile.bundle_balance -= float(bundle_volume)
                            user_profile.save()
                            new_txn = models.NewTransaction.objects.create(
                                user=request.user,
                                account_number=phone_number,
                                bundle_amount=bundle_volume,
                                reference=reference,
                                transaction_status="Completed"
                            )
                            new_txn.save()
                            user.save()
                            receiver_message = f"Your bundle purchase has been completed successfully. {bundle_volume}MB has been credited to you by {user_profile.phone}.\nReference: {reference}\n"
                            sms_message = f"Hello @{request.user.username}. Your bundle purchase has been completed successfully. {bundle_volume}MB has been credited to {phone_number}.\nReference: {reference}\nCurrent Wallet Balance: {user_profile.bundle_balance}\n"

                            # response1 = requests.get(
                            #     f"https://sms.arkesel.com/sms/api?action=send-sms&api_key=UnBzemdvanJyUGxhTlJzaVVQaHk&to=0{user_profile.phone}&from=GEO_AT&sms={sms_message}")
                            # print(response1.text)

                            # response2 = requests.get(
                            #     f"https://sms.arkesel.com/sms/api?action=send-sms&api_key=UnBzemdvanJyUGxhTlJzaVVQaHk&to={phone_number}&from=GEO_AT&sms={receiver_message}")
                            # print(response2.text)
                            return Response(
                                data={"status": "Success",
                                      "message": "Transaction was completed successfully",
                                      "reference": reference},
                                status=status.HTTP_200_OK)
                        else:
                            new_txn = models.NewTransaction.objects.create(
                                user=request.user,
                                account_number=phone_number,
                                bundle_amount=bundle_volume,
                                reference=reference,
                                transaction_status="Failed"
                            )
                            new_txn.save()
                            return Response(
                                data={"status": "Failed",
                                      "message": "Something went wrong on our end. Try again later",
                                      "reference": reference},
                                status=status.HTTP_503_SERVICE_UNAVAILABLE)
                else:
                    return Response(
                        data={"status": "Failed", "error": "Body error",
                              "message": "Body Parameters set not valid. Check and try again."},
                        status=status.HTTP_400_BAD_REQUEST)
            except Token.DoesNotExist:
                return Response({'error': 'Token does not exist.'}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({'error': 'Invalid Header Provided.'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes([BearerTokenAuthentication])
def transaction_detail(request, reference):
    authorization_header = request.headers.get('Authorization')
    if authorization_header:
        auth_type, token = authorization_header.split(' ')
        if auth_type == 'Bearer':
            try:
                token_obj = Token.objects.get(key=token)
                user = token_obj.user

                user_profile = models.UserProfile.objects.get(user=user)

                try:
                    referenced_txn = models.NewTransaction.objects.get(reference=reference, user=user)
                    txn_status = referenced_txn.transaction_status
                    txn_date = referenced_txn.transaction_date
                    receiver = referenced_txn.account_number
                    data_volume = referenced_txn.bundle_amount

                    if txn_status == 'Completed':
                        return Response(
                            data={"status": "Success",
                                  "message": "Transaction was completed successfully",
                                  "reference": reference,
                                  "date_created": txn_date,
                                  "receiver": receiver,
                                  "data_volume": data_volume
                                  },
                            status=status.HTTP_200_OK)
                    else:
                        return Response(
                            data={"status": "Incomplete",
                                  "message": "Transaction was not completed",
                                  "reference": reference,
                                  "date_created": txn_date,
                                  "receiver": receiver,
                                  "data_volume": data_volume
                                  },
                            status=status.HTTP_200_OK)
                except models.NewTransaction.DoesNotExist:
                    return Response({'error': 'No Transaction with reference provided.'}, status=status.HTTP_404_NOT_FOUND)

            except Token.DoesNotExist or models.CustomUser.DoesNotExist or models.UserProfile.DoesNotExist:
                return Response({'error': 'Token or User does not exist.'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@authentication_classes([BearerTokenAuthentication])
def user_balance(request):
    authorization_header = request.headers.get('Authorization')
    if authorization_header:
        auth_type, token = authorization_header.split(' ')
        if auth_type == 'Bearer':
            try:
                token_obj = Token.objects.get(key=token)
                user = token_obj.user

                user_profile = models.UserProfile.objects.get(user=user)

                user_balance_left = user_profile.bundle_balance

                if user_balance_left or user_balance_left is not None:
                    return Response(
                        data={"bundle_balance": f"{user_balance_left}MB",
                              "status": "Success",
                              },
                        status=status.HTTP_200_OK)
                else:
                    return Response(
                        data={
                              "status": "Query Unsuccessful",
                              },
                        status=status.HTTP_200_OK)

            except Token.DoesNotExist or models.CustomUser.DoesNotExist or models.UserProfile.DoesNotExist:
                return Response({'error': 'Token or User does not exist.'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([BearerTokenAuthentication])
def null_transaction_query(request):
    return Response(data={"status": "Failed", "error": "Null Reference",
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
