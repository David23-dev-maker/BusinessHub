import base64
import os
import uuid

import requests


class MTNMoMoError(Exception):
    """Raised when an MTN MoMo operation fails."""


class MTNMoMoProvider:
    """
    MTN MoMo Collections integration for BusinessHub.

    BusinessHub's own prices are stored/displayed in XAF.

    MTN sandbox currently requires EUR for RequestToPay testing,
    so the API currency can be configured separately from the
    BusinessHub payment currency.

    IMPORTANT:
    - Credentials come from environment variables.
    - Never put API keys directly in this file.
    - This provider is for BusinessHub's own services only.
    """

    def __init__(self):
        self.base_url = os.getenv(
            "MTN_MOMO_BASE_URL",
            "https://sandbox.momodeveloper.mtn.com",
        ).rstrip("/")

        self.subscription_key = os.getenv(
            "MTN_MOMO_SUBSCRIPTION_KEY",
            "",
        )

        self.api_user = os.getenv(
            "MTN_MOMO_API_USER",
            "",
        )

        self.api_key = os.getenv(
            "MTN_MOMO_API_KEY",
            "",
        )

        self.target_environment = os.getenv(
            "MTN_MOMO_TARGET_ENVIRONMENT",
            "sandbox",
        )

        self.callback_url = os.getenv(
            "MTN_MOMO_CALLBACK_URL",
            "",
        )

        self.api_currency = os.getenv(
            "MTN_MOMO_API_CURRENCY",
            "EUR",
        )

        self.timeout = int(
            os.getenv(
                "PAYMENT_API_TIMEOUT",
                "30",
            )
        )

    def is_configured(self):
        return bool(
            self.subscription_key
            and self.api_user
            and self.api_key
        )

    def _check_configuration(self):
        if not self.is_configured():
            raise MTNMoMoError(
                "MTN MoMo credentials are not configured."
            )

    def _headers(self):
        return {
            "Ocp-Apim-Subscription-Key": (
                self.subscription_key
            ),
            "X-Target-Environment": (
                self.target_environment
            ),
            "Content-Type": "application/json",
        }

    def _get_basic_auth_header(self):
        credentials = (
            f"{self.api_user}:{self.api_key}"
        )

        encoded = base64.b64encode(
            credentials.encode("utf-8")
        ).decode("utf-8")

        return f"Basic {encoded}"

    def get_access_token(self):
        """
        Generate an MTN MoMo Collections access token.
        """

        self._check_configuration()

        url = (
            f"{self.base_url}"
            "/collection/token/"
        )

        headers = self._headers()

        headers["Authorization"] = (
            self._get_basic_auth_header()
        )

        response = requests.post(
            url,
            headers=headers,
            timeout=self.timeout,
        )

        if response.status_code >= 400:
            raise MTNMoMoError(
                "MTN MoMo authentication failed."
            )

        data = response.json()

        access_token = data.get(
            "access_token"
        )

        if not access_token:
            raise MTNMoMoError(
                "MTN MoMo did not return an access token."
            )

        return access_token

    def request_payment(
        self,
        amount,
        payer_phone,
        external_id,
        payer_message="BusinessHub payment",
        payee_note="BusinessHub service payment",
    ):
        """
        Send a RequestToPay request.

        MTN processes this asynchronously.

        The currency sent to MTN is controlled by
        MTN_MOMO_API_CURRENCY.

        This is intentionally separate from BusinessHub's
        own payment currency, which remains XAF.
        """

        self._check_configuration()

        access_token = self.get_access_token()

        reference_id = str(uuid.uuid4())

        url = (
            f"{self.base_url}"
            "/collection/v1_0/requesttopay"
        )

        headers = self._headers()

        headers["Authorization"] = (
            f"Bearer {access_token}"
        )

        headers["X-Reference-Id"] = (
            reference_id
        )

        if self.callback_url:
            headers["X-Callback-Url"] = (
                self.callback_url
            )

        payload = {
            "amount": str(amount),
            "currency": self.api_currency,
            "externalId": str(external_id),
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
            timeout=self.timeout,
        )

        if response.status_code != 202:
            error_detail = response.text.strip()

            if error_detail:
                raise MTNMoMoError(
                    "MTN MoMo payment request was not accepted: "
                    f"{error_detail}"
                )

            raise MTNMoMoError(
                "MTN MoMo payment request was not accepted."
            )

        return {
            "reference_id": reference_id,
            "status_code": response.status_code,
            "currency": self.api_currency,
            "message": "Payment request accepted.",
        }

    def payment_status(self, reference_id):
        """
        Check the current status of an MTN MoMo
        RequestToPay transaction.
        """

        self._check_configuration()

        access_token = self.get_access_token()

        url = (
            f"{self.base_url}"
            "/collection/v1_0/requesttopay/"
            f"{reference_id}"
        )

        headers = self._headers()

        headers["Authorization"] = (
            f"Bearer {access_token}"
        )

        response = requests.get(
            url,
            headers=headers,
            timeout=self.timeout,
        )

        if response.status_code >= 400:
            error_detail = response.text.strip()

            if error_detail:
                raise MTNMoMoError(
                    "Unable to retrieve MTN MoMo payment "
                    f"status: {error_detail}"
                )

            raise MTNMoMoError(
                "Unable to retrieve MTN MoMo payment status."
            )

        return response.json()