from payout_modules.stripe_deposit import StripeDeposit
from typing import Any, List, Mapping, Text
from decimal import Decimal, ROUND_DOWN
from payout_modules.tutor import Tutor
from datetime import datetime
import pandas as pd
import logging
import json
import os


class PayrollManager:
    def __init__(self, payload_path: Text) -> None:
        with open(payload_path, 'r') as json_file:
            self.payload = json.load(json_file)
        # Update self.payload to remove @ symbols, whether provided or not before tutor id, to consistently check for matches in Square invoice data
        self.remove_at_from_ids()

        self.invoice_data = pd.read_csv(self.payload["squareInvoiceSummaryFilePath"])
        # Column names for resulting CSV with documentation of direct deposit records
        self.documentation_columns = ["Name", "School", "Revenue", "Cut", "Troy Tutors Service Fee", "Takehome (Revenue / (1 + Troy Tutors Service Fee) * Cut, Rounded Down to the Nearest Cent)", "ID", "Stripe Email"]
        # Calculate time now, to consistently name and differentiate payroll documentation and logging pairs
        self.start_time = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Set up logger
        logging_path = f"{self.payload['payrollDocumentPath']}/logs/"
        if not os.path.exists(logging_path):
            os.makedirs(logging_path)
        logging.basicConfig(filename=f"{logging_path}{self.start_time}.log", level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

        self.action = None
        self.tutor_deposit = None

    def handle_request(self, action: Text) -> None:
        self.action = action
        if action == "send_direct_deposits":
            self.tutor_deposit = StripeDeposit(self.payload)
        logging.info(f"Action: {action}\n\n")
        # See if all tutors in Square invoice are part of the payload before handling direct deposits, documentation, or Stripe transfer calculations
        self.check_for_missing_tutors()
        # Identify which tutors to send direct deposits to, document, or be included in the Stripe transfer calculations
        tutors = self.get_tutors_to_pay()
        direct_deposit_records = []
        direct_deposit_total = 0
        failed_deposits = []
        for tutor in tutors:
            resp = self.pay_tutor(tutor)
            # Record of what to pay this tutor, given Square data and its time range
            direct_deposit_records.append([tutor.name, tutor.school, resp["tutor_revenue"], tutor.cut, self.payload["customerServiceFeeFraction"], resp["amount_paid"], tutor.id, tutor.stripe_email])
            direct_deposit_total += resp["amount_paid"]
            if not resp["success"]:
                failed_deposits.add(tutor)

        # The only situation where we don't document is when we are seeing how much we should send to Stripe
        if self.action != "calculate_stripe_transfer":
            documentation = pd.DataFrame(direct_deposit_records, columns=self.documentation_columns)
            documentation.to_csv(f"{self.payload['payrollDocumentPath']}/Period_{self.payload['periodName']}_Ran_{self.start_time}.csv", index=False)
        # Output for when stripe transfer amount is requested
        else:
            print(f"Total to Transfer to Stripe: {direct_deposit_total}")

        # Output for when sending direct deposits to tutors is requested
        if self.action == "send_direct_deposits":
            if len(failed_deposits) > 0:
                print("Unable to send direct deposits to the following:")
                for fd in failed_deposits:
                    print(f"{fd.name} {fd.id}")
            else:
                print("Success! All tutors have been paid.")

    def check_for_missing_tutors(self) -> None:
        # Missing tutors = {tutors from Strip documentation} - {tutors mentioned in payload under "tutors"} - {tutors instructed to be skipped in payload under "excludeFromPayoutsAndStripeTransfers"}
        tutors_to_pay = {self.invoice_data.iloc[row]["Invoice Title"].split()[-1].strip("@").strip() for row in range(len(self.invoice_data))}
        tutors_in_payload = {tutor_data["tutorID"] for tutor_data in self.payload["tutors"]}
        tutors_to_exclude = set(self.payload["excludeFromPayoutsAndStripeTransfers"])
        missing_tutors = tutors_to_pay - tutors_in_payload - tutors_to_exclude
        # Raise exception if tutors are missing from payload
        if len(missing_tutors) > 0:
            exception_message = "Missing information on the following tutors:"
            for missing_tutor in missing_tutors:
                exception_message += f"\n{missing_tutor}"
            raise Exception(exception_message)

    def get_tutors_to_pay(self) -> List[Tutor]:
        # Tutors to pay = {tutors mentioned in payload under "tutors"} - {tutors instructed to be skipped in payload under "excludeFromPayoutsAndStripeTransfers"}
        tutor_ids_in_payload = {tutor_data["tutorID"] for tutor_data in self.payload["tutors"]}
        tutor_ids_to_exclude = set(self.payload["excludeFromPayoutsAndStripeTransfers"])
        tutor_ids_to_pay = tutor_ids_in_payload - tutor_ids_to_exclude
        return [Tutor(tutor_data) for tutor_data in self.payload["tutors"] if tutor_data["tutorID"] in tutor_ids_to_pay]

    def pay_tutor(self, tutor: Tutor) -> Mapping[Text, Any]:
        success = True
        payout_obj = {}
        tutor_revenue = 0
        print(f"Handling tutor {tutor.name} @{tutor.id}")
        logging.info(f"Handling tutor {tutor.name} @{tutor.id}")
        for row in range(len(self.invoice_data)):
            # Parse tutor's id from Square Invoice Title, skip canceled invoice, and sum up to calculate tutor revenue
            if self.invoice_data.iloc[row]["Invoice Title"].split()[-1].strip("@").strip() == tutor.id:
                if self.invoice_data.iloc[row]["Status"] == "Canceled":
                    logging.info("Canceled!")
                    continue
                amt = float(self.invoice_data.iloc[row]["Requested Amount"].strip("$"))
                logging.info(amt)
                tutor_revenue += amt
        logging.info(f"Tutor Revenue: {tutor_revenue}")
        # Tutor takehome = tutor revenue / (1 + service fee) * tutor cut
        service_fee_offset_divisor = 1 + self.payload["customerServiceFeeFraction"]
        tutor_takehome = tutor_revenue / service_fee_offset_divisor * tutor.cut
        # Round tutor takehome down, to the nearest dollar, as part of Troy Tutors’ Tutor Payment Policies
        tutor_takehome = Decimal(tutor_takehome).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
        logging.info(f"Tutor Takehome: {tutor_takehome}\n")

        if tutor_takehome > 0 and self.action == "send_direct_deposits":
            # Send direct deposit
            success, payout_obj = self.tutor_deposit.send_direct_deposit(tutor.stripe_email, tutor_takehome)
        return {"success": success, "tutor_revenue": tutor_revenue, "amount_paid": tutor_takehome, "payout": payout_obj}

    def remove_at_from_ids(self) -> None:
        # Remove "@" and whitespaces from tutorID in tutors field
        for tutor_num in range(len(self.payload["tutors"])):
            self.payload["tutors"][tutor_num]["tutorID"] = self.payload["tutors"][tutor_num]["tutorID"].strip("@").strip()
        # Remove "@" and whitespaces from excludeFromPayoutsAndStripeTransfers field
        for tutor_num in range(len(self.payload["excludeFromPayoutsAndStripeTransfers"])):
            self.payload["excludeFromPayoutsAndStripeTransfers"][tutor_num] = self.payload["excludeFromPayoutsAndStripeTransfers"][tutor_num].strip("@").strip()
