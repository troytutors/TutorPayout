from typing import Any, Mapping, Text, Tuple
from dotenv import load_dotenv
import stripe
import math
import os


class StripeDeposit:
    def __init__(self, payroll_payload: Any) -> None:
        load_dotenv()
        stripe.api_key = os.getenv("stripe_api_key")
        self.connected_accounts = self.get_connected_accounts()
        self.check_for_invalid_stripe_accounts(payroll_payload)

    def get_connected_accounts(self) -> Mapping[Text, stripe._account.Account]:
        all_connected_accounts = dict()
        connected_accounts = stripe.Account.list()
        for account in connected_accounts.auto_paging_iter():
            all_connected_accounts[account.email] = account
        return all_connected_accounts

    def check_for_invalid_stripe_accounts(self, payroll_payload: Any) -> None:
        tutors_in_payload = {tutor_data["stripeEmail"] for tutor_data in payroll_payload["tutors"]}
        stripe_emails = set(self.connected_accounts.keys())
        invalid_stripe_accounts = tutors_in_payload - stripe_emails
        if len(invalid_stripe_accounts) > 0:
            exception_message = "Invalid Stripe Emails:"
            for missing_tutor in invalid_stripe_accounts:
                exception_message += f"\n{missing_tutor}"
            raise Exception(exception_message)

    def send_direct_deposit(self, tutor_email: Text, desposit_in_dollars: float) -> Tuple[Text, Any]:
        success = True
        payout = None
        connected_account_id = self.connected_accounts[tutor_email].id
        try:
            # Stripe expects the direct deposit amount to be sent in cents
            desposit_in_cents = math.floor(desposit_in_dollars * 100)
            payout = stripe.Transfer.create(
                amount=desposit_in_cents,
                currency="usd",
                destination=connected_account_id
            )
        except stripe.error.StripeError as e:
            print(f"Error: {e.error.message}")
            success = False, payout
        return success, payout
