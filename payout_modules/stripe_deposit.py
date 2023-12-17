from payout_modules.tutor import Tutor
from typing import Text, Tuple, Any
from dotenv import load_dotenv
import stripe
import math
import os


class StripeDeposit:
    def __init__(self, tutor: Tutor) -> None:
        load_dotenv()
        stripe.api_key = os.getenv("stripe_api_key")
        self.connected_account_id = self.get_connected_account_id(tutor.stripe_email)

    def get_connected_account_id(self, tutor_email: Text) -> Any:
        connected_accounts = stripe.Account.list()
        # Find the account id associated with the tutor's Stripe email
        # It's okay if this function return None, as a failed sent direct deposit
        # is handled outside of the StripeDeposit class.
        for account in connected_accounts.auto_paging_iter():
            if account.email == tutor_email:
                return account.id

    def send_direct_deposit(self, desposit_in_dollars: float) -> Tuple[Text, Any]:
        success = True
        payout = None
        try:
            # Stripe expect the direct deposit amount to be sent in cents
            desposit_in_cents = math.floor(desposit_in_dollars * 100)
            payout = stripe.Transfer.create(
                amount=desposit_in_cents,
                currency="usd",
                destination=self.connected_account_id
            )
        except stripe.error.StripeError as e:
            print(f"Error: {e.error.message}")
            success = False, payout
        return success, payout


if __name__ == "__main__":
    tdata = {"name": "name", "tutorID": "tutorID", "stripeEmail": "matthewyoungbar@gmail.com", "school": "s", "tutorCut": "tc"}
    t = Tutor(tdata)
    sd = StripeDeposit(t)
    print(sd.send_direct_deposit(0.01))
