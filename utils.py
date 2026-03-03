import os
import secrets
from wsgiref import headers

from dns.query import https
from __init__ import app
import json
import requests


def save_image(file):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(file.filename)
    image_name = random_hex + f_ext
    image_path = os.path.join(app.root_path, 'static/event_images', image_name)
    file.save(image_path)
    return image_name


def delete_image(image_name):
    image_path = os.path.join(app.root_path, 'static/event_images', image_name)
    if os.path.exists(image_path):
        os.remove(image_path)


def generate_pesapal_access_token():
    with open('../config.json') as config_file:
        config = json.load(config_file)
    consumer_key = config.get('consumer_key')
    consumer_secret = config.get('consumer_secret')

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    params = {
        'consumer_key': consumer_key,
        'consumer_secret': consumer_secret
    }

    response = requests.post('https://pay.pesapal.com/v3/api/Auth/RequestToken', headers=headers, json=params)
    if response.json().get('status') == '200':
        token = response.json().get('token')
        return  token
    else:
        return None



def pesa_pal_submit_order_request(token, order_details):
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    params = order_details

    response = requests.post('https://pay.pesapal.com/v3/api/Transactions/SubmitOrderRequest', headers=headers, json=params)
    return response.json()



def register_IPN_URL():
    token = generate_pesapal_access_token()
    
    if token is None:
        print('Error generating access token for IPN registration. Please check your credentials and try again.')
        return None
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    params = {
        "url": "https://gopass.space/ipn",
        "ipn_notification_type": "GET"
    }

    response = requests.post('https://pay.pesapal.com/v3/api/URLSetup/RegisterIPN', headers=headers, json=params)
    return response.json()


def get_IPN_url():
    token = generate_pesapal_access_token()
    
    if token is None:
        print('Error generating access token for IPN retrieval. Please check your credentials and try again.')
        return None
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    response = requests.get('https://pay.pesapal.com/v3/api/URLSetup/GetIpnList', headers=headers)
    return response.json()
