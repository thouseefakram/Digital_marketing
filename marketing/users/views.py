import requests
from django.conf import settings
from django.http import JsonResponse
from urllib.parse import urlencode
from .meta_api import get_ad_insights
import os
from dotenv import load_dotenv
load_dotenv()


def facebook_login_url(request):
    params = {
        'client_id': os.getenv("FACEBOOK_APP_ID"),
        'redirect_uri': os.getenv("FACEBOOK_REDIRECT_URI"),
        'scope': 'ads_management,ads_read,pages_show_list',
        'response_type': 'code',
    }
    login_url = f"https://www.facebook.com/v18.0/dialog/oauth?{urlencode(params)}"
    return JsonResponse({'login_url': login_url})


def facebook_callback(request):
    code = request.GET.get('code')

    token_exchange_url = 'https://graph.facebook.com/v18.0/oauth/access_token'
    params = {
        'client_id': os.getenv("FACEBOOK_APP_ID"),
        'client_secret': os.getenv("FACEBOOK_APP_SECRET"),
        'redirect_uri': os.getenv("FACEBOOK_REDIRECT_URI"),
        'code': code,
    }

    response = requests.get(token_exchange_url, params=params)
    short_token = response.json().get('access_token')

    # Exchange for long-lived token
    long_token_url = 'https://graph.facebook.com/v18.0/oauth/access_token'
    params = {
        'grant_type': 'fb_exchange_token',
        'client_id': os.getenv("FACEBOOK_APP_ID"),
        'client_secret': os.getenv("FACEBOOK_APP_SECRET"),
        'fb_exchange_token': short_token
    }

    long_response = requests.get(long_token_url, params=params)
    return JsonResponse(long_response.json())


def get_ad_accounts(request):
    access_token = request.GET.get('access_token')
    if not access_token:
        return JsonResponse({'error': 'access_token is required'}, status=400)

    url = 'https://graph.facebook.com/v18.0/me/adaccounts'
    params = {
        'access_token': access_token,
        'fields': 'id,name,account_status,timezone_name'
    }

    r = requests.get(url, params=params)
    return JsonResponse(r.json())


def get_campaigns(request):
    access_token = request.GET.get('access_token')
    ad_account_id = request.GET.get('ad_account_id')  # e.g. act_123456789

    if not access_token or not ad_account_id:
        return JsonResponse({'error': 'access_token and ad_account_id are required'}, status=400)

    url = f"https://graph.facebook.com/v18.0/{ad_account_id}/campaigns"
    params = {
        'access_token': access_token,
        'fields': 'id,name,status,objective,effective_status'
    }

    r = requests.get(url, params=params)
    return JsonResponse(r.json())

# ads/views.py
def get_ad_insights_api(request):
    access_token = request.GET.get('access_token')
    days = int(request.GET.get('days', 30))  # Default: 30 days
    
    if not access_token:
        return JsonResponse({'error': 'access_token is required'}, status=400)
    
    try:
        request.session['fb_user_access_token'] = access_token  # Store token in session
        insights = get_ad_insights(request, days=days)
        return JsonResponse({'data': insights})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# views.py
def facebook_login_url(request):
    params = {
        'client_id': os.getenv("FACEBOOK_APP_ID"),
        'redirect_uri': os.getenv("FACEBOOK_REDIRECT_URI"),
        'scope': os.getenv("FACEBOOK_SCOPE"),  
        'response_type': 'code',
    }
    login_url = f"https://www.facebook.com/v18.0/dialog/oauth?{urlencode(params)}"
    return JsonResponse({'login_url': login_url})

def get_instagram_accounts(request):
    access_token = request.GET.get('access_token')
    if not access_token:
        return JsonResponse({'error': 'access_token is required'}, status=400)

    # First get the user's pages (as Instagram accounts are typically linked to Facebook pages)
    pages_url = 'https://graph.facebook.com/v18.0/me/accounts'
    pages_params = {
        'access_token': access_token,
        'fields': 'id,name,instagram_business_account'
    }

    pages_response = requests.get(pages_url, params=pages_params)
    pages_data = pages_response.json()
    
    if 'error' in pages_data:
        return JsonResponse(pages_data, status=400)
    
    # Extract Instagram accounts from pages
    instagram_accounts = []
    for page in pages_data.get('data', []):
        if 'instagram_business_account' in page:
            ig_account_id = page['instagram_business_account']['id']
            # Get Instagram account details
            ig_url = f'https://graph.facebook.com/v18.0/{ig_account_id}'
            ig_params = {
                'access_token': access_token,
                'fields': 'id,username,profile_picture_url,name,biography'
            }
            ig_response = requests.get(ig_url, params=ig_params)
            ig_data = ig_response.json()
            if 'error' not in ig_data:
                instagram_accounts.append(ig_data)
    
    return JsonResponse({'instagram_accounts': instagram_accounts})

def get_instagram_insights(request):
    access_token = request.GET.get('access_token')
    instagram_account_id = request.GET.get('instagram_account_id')
    days = int(request.GET.get('days', 30))  # Default: 30 days
    
    if not access_token or not instagram_account_id:
        return JsonResponse({'error': 'access_token and instagram_account_id are required'}, status=400)
    
    # Define metrics you want to retrieve
    metrics = [
        'impressions', 'reach', 'profile_views', 'website_clicks',
        'follower_count', 'email_contacts', 'phone_call_clicks',
        'text_message_clicks', 'get_directions_clicks'
    ]
    
    # Calculate date range
    since_date = (date.today() - timedelta(days=days)).strftime('%Y-%m-%d')
    until_date = date.today().strftime('%Y-%m-%d')
    
    insights_url = f'https://graph.facebook.com/v18.0/{instagram_account_id}/insights'
    params = {
        'access_token': access_token,
        'metric': ','.join(metrics),
        'period': 'day',
        'since': since_date,
        'until': until_date
    }
    
    try:
        response = requests.get(insights_url, params=params)
        data = response.json()
        if 'error' in data:
            return JsonResponse(data, status=400)
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)