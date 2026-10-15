import os
from typing import Optional

import requests


class OrangeMoneyError(Exception):
    """Raised when an Orange Money operation fails."""


class OrangeMoneyProvider:
    """
    BusinessHub Orange Money provider.

    Credentials must be supplied through environment variables.
    Never hard-code API credentials in the source code.
    """

    def __init__(self):
        self.base_url = os.getenv(
            "ORANGE_MONEY_BASE_URL",
            "https://api-s1.orange.cm/omcoreapis/1.0.2",
        ).rstrip("/")

        self.client_id = os.getenv(
            "ORANGE_MONEY_CLIENT_ID",
            "",
        )

        self.client_secret = os.getenv(
            "ORANGE_MONEY_CLIENT_SECRET",
            "",
        )

        self.timeout = int(
            os.getenv(
                "PAYMENT_API_TIMEOUT",
                "30",
            )
        )

    def is_configured(self):
        return bool(
            self.client_id
            and self.client_secret
        )

    def get_access_token(self):
        """
        Obtain an OAuth access token.

        The exact OAuth request parameters should follow the
        credentials/environment provided by Orange Money.
        """

        if not self.is_configured():
            raise OrangeMoneyError(
                "Orange Money credentials are not configured."
            )

        token_url = (
            f"{self.base_url}/oauth/token"
        )

        response = requests.post(
            token_url,
            auth=(
                self.client_id,
                self.client_secret,
            ),
            data={
                "grant_type": "client_credentials",
            },
            timeout=self.timeout,
        )

        if response.status_code >= 400:
            raise OrangeMoneyError(
                "Orange Money authentication failed."
            )

        data = response.json()

        token = data.get(
            "access_token"
        )

        if not token:
            raise OrangeMoneyError(
                "Orange Money did not return an access token."
            )

        return token

    def initiate_payment(
        self,
        amount,
        reference,
        description,
        customer_phone=None,
    ):
        """
        Initiate an Orange Money merchant payment.

        The request body is intentionally kept behind this provider
        class so the rest of BusinessHub does not depend directly
        on Orange's API format.
        """

        token = self.get_access_token()

        url = (
            f"{self.base_url}/mp/init"
        )

        payload = {
            "amount": str(amount),
            "reference": reference,
            "description": description,
        }

        if customer_phone:
            payload["customerPhone"] = customer_phone

        response = requests.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )

        if response.status_code >= 400:
            raise OrangeMoneyError(
                "Orange Money payment initiation failed."
            )

        return response.json()

    def payment_status(
        self,
        pay_token,
    ):
        """
        Retrieve the status of an Orange Money payment.
        """

        token = self.get_access_token()

        url = (
            f"{self.base_url}/mp/paymentstatus/"
            f"{pay_token}"
        )

        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )

        if response.status_code >= 400:
            raise OrangeMoneyError(
                "Orange Money status request failed."
            )

        return response.json()