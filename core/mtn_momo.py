import base64
import uuid

import requests
from django.conf import settings


def get_mtn_access_token():
    """
    Generate an MTN MoMo Collections access token.
    """

    api_user = settings.MTN_API_USER
    api_key = settings.MTN_API_KEY
    primary_key = settings.MTN_COLLECTION_PRIMARY_KEY
    base_url = settings.MTN_BASE_URL
    target_environment = settings.MTN_TARGET_ENVIRONMENT

    credentials = f"{api_user}:{api_key}"

    encoded_credentials = base64.b64encode(
        credentials.encode("utf-8")
    ).decode("utf-8")

    url = f"{base_url}/collection/token/"

    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Ocp-Apim-Subscription-Key": primary_key,
        "X-Target-Environment": target_environment,
        "Content-Type": "application/x-www-form-urlencoded",
    }

    response = requests.post(
        url,
        headers=headers,
        data="",
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    return data["access_token"]


def request_to_pay(
    amount,
    external_id,
    payer_phone,
    payer_message="BusinessHub payment",
    payee_note="BusinessHub payment",
):
    """
    Create an MTN MoMo Collections RequestToPay transaction.

    Returns:
        {
            "reference_id": "...",
            "response": {...}
        }
    """

    access_token = get_mtn_access_token()

    reference_id = str(uuid.uuid4())

    base_url = settings.MTN_BASE_URL
    primary_key = settings.MTN_COLLECTION_PRIMARY_KEY
    target_environment = settings.MTN_TARGET_ENVIRONMENT

    url = f"{base_url}/collection/v1_0/requesttopay"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Reference-Id": reference_id,
        "X-Target-Environment": target_environment,
        "Ocp-Apim-Subscription-Key": primary_key,
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }

    payload = {
        "amount": str(amount),
        "currency": "EUR",
        "externalId": external_id,
        "payer": {
            "partyIdType": "MSISDN",
            "partyId": str(payer_phone),
        },
        "payerMessage": payer_message,
        "payeeNote": payee_note,
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=30,
    )

    response.raise_for_status()

    return {
        "reference_id": reference_id,
        "response": response,
    }


def get_transaction_status(reference_id):
    """
    Check the status of an MTN MoMo RequestToPay transaction.
    """

    access_token = get_mtn_access_token()

    base_url = settings.MTN_BASE_URL
    primary_key = settings.MTN_COLLECTION_PRIMARY_KEY
    target_environment = settings.MTN_TARGET_ENVIRONMENT

    url = (
        f"{base_url}/collection/v1_0/requesttopay/"
        f"{reference_id}"
    )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Target-Environment": target_environment,
        "Ocp-Apim-Subscription-Key": primary_key,
        "Cache-Control": "no-cache",
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()