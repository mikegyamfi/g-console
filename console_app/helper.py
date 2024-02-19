import json
import re

import requests
from decouple import config


def send_bundle(user, receiver, bundle_amount, reference):
    # url = "https://console.bestpaygh.com/api/flexi/v1/new_transaction/"
    #
    # headers = {
    #     "api-key": config("API_KEY"),
    #     "api-secret": config("API_SECRET"),
    #     'Content-Type': 'application/json'
    # }
    #
    # print("====================================")
    # print(user.phone)
    # print(user.first_name)
    # print(user.last_name)
    # print(user.email)
    # print(receiver)
    # print(reference)
    # print(bundle_amount)
    # print("=====================================")
    #
    # payload = json.dumps({
    #     "first_name": user.first_name,
    #     "last_name": user.last_name,
    #     "account_number": f"0{user.phone}",
    #     "receiver": receiver,
    #     "account_email": user.email,
    #     "reference": reference,
    #     "bundle_amount": bundle_amount
    # })
    #
    # response = requests.request("POST", url, headers=headers, data=payload)
    #
    # print(response.json)
    # return response

    url = "https://multidataghana.com/merchintegrate/geosams/ishare_api/"
    print(reference)
    print(bundle_amount)
    print(str(int(bundle_amount)))
    print(receiver)

    print(type(bundle_amount))
    print(type(receiver))
    payload = {'type': 'pushData',
               'apikey': '8ecce2fb4ba200b6ba148a7994035987f22d411a',
               'ref': str(reference),
               'data': str(int(bundle_amount)),
               'share': str(receiver)
               }
    files = [

    ]
    headers = {}

    response = requests.request("POST", url, headers=headers, data=payload, files=files)
    json_match = re.search(r'getBalance(.+)}', response.text)

    if json_match:
        json_part = json_match.group(1) + '}'
        print("Extracted JSON part:")
        print(json_part)

        try:
            # Parse the extracted JSON into a dictionary
            response_dict = json.loads(json_part)
            print(response_dict)

            # Now you can access the data using keys
            return response_dict
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return "bad response"
    else:
        print("No valid JSON found in the response.")
        return "bad response"

