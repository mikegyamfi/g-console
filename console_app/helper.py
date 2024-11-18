import json
import re

import requests
from decouple import config
from requests.adapters import HTTPAdapter
from urllib3 import Retry


def send_bundle(user, receiver, bundle_amount, reference):
    try:
        url = "https://multidataghana.com/merchintegrate/geosams/ishare_api/"

        payload = {
            'type': 'pushData',
            'apikey': config('API_KEY'),
            'ref': str(reference),
            'data': str(int(bundle_amount)),
            'share': str(receiver)
        }

        response = requests.post(url, data=payload)

        try:
            response_dict = response.json()
            print("Response Dictionary:")
            print(response_dict)
            return response.status_code, response_dict
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            print("Response Text:")
            print(response.text)
            return response.status_code, "bad response"
    except Exception as e:
        print(e)
        # Log the exception
        return 400, "bad response"

