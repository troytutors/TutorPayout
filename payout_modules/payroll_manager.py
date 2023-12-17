from typing import Text, List, Mapping, Any
from stripe_deposit import StripeDeposit
from datetime import datetime
from tutor import Tutor
import pandas as pd
import json


class PayrollManager:
    def __init__(self, payload_path: Text) -> None:
        with open(payload_path, 'r') as json_file:
            self.payload = json.load(json_file)
            # Remove @ symbols, whether provided or not before tutor id, to consistently check for matches in Square invoice data
            self.remove_at_from_ids()
        self.invoice_data = pd.read_csv(self.payload["squareInvoiceSummaryFilePath"])
        # Column names for resulting CSV with documentation of direct deposit records
        self.documentation_columns = ["Name", "School", "Revenue", "Cut", "Troy Tutors Service Fee", "Takehome (Revenue / (1 + Troy Tutors Service Fee) * Cut)", "ID", "Stripe Email"]
        self.action = None

    def handle_request(self, action: Text) -> None:
        self.action = action
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
            documentation.to_csv(f"{self.payload['payrollDocumentPath']}/{self.payload['periodName']}_{datetime.now().time()}")
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
        tutors_to_pay = {self.invoice_data.iloc[row][7].split()[-1].strip("@").strip() for row in range(len(self.invoice_data))}
        tutors_in_payload = {tutor_data["tutorID"] for tutor_data in self.payload["tutors"]}
        tutors_to_exclude = {self.payload["excludeFromPayoutsAndStripeTransfers"]}
        missing_tutors = tutors_to_pay - tutors_in_payload - tutors_to_exclude
        # Raise exception if tutors are missing from payload
        if len(missing_tutors) > 0:
            exception_message = "Missing information on the following tutors:"
            for missing_tutor in missing_tutors:
                exception_message += f"\n{missing_tutor}"
            raise Exception(f"Missing payload information on: {exception_message}")

    def get_tutors_to_pay(self) -> List[Tutor]:
        # Tutors to pay = {tutors mentioned in payload under "tutors"} - {tutors instructed to be skipped in payload under "excludeFromPayoutsAndStripeTransfers"}
        tutor_ids_in_payload = {tutor_data["tutorID"] for tutor_data in self.payload["tutors"]}
        tutor_ids_to_exclude = {self.payload["excludeFromPayoutsAndStripeTransfers"]}
        tutor_ids_to_pay = tutor_ids_in_payload - tutor_ids_to_exclude
        return [Tutor(tutor_data) for tutor_data in self.payload["tutors"] if tutor_data["tutorID"] in tutor_ids_to_pay]

    def pay_tutor(self, tutor: Tutor) -> Mapping[Text, Any]:
        success = True
        payout_obj = {}
        tutor_revenue = 0
        print(f"Paying tutor {tutor.name} @{tutor.id}")
        for row in range(len(self.invoice_data)):
            # Parse tutor's id from Square Invoice Title, skip canceled invoice, and sum up to calculate tutor revenue
            if self.invoice_data.iloc[row][7].split()[-1].strip("@").strip() == tutor.id:
                if self.invoice_data.iloc[row][8] == "Canceled":
                    print("Canceled!")
                    continue
                amt = float(self.invoice_data.iloc[row][9].strip("$"))
                print(amt)
                tutor_revenue += amt
        print(f"Tutor Revenue: {tutor_revenue}")
        # Tutor takehome = tutor revenue / (1 + service fee) * tutor cut
        service_fee_offset_divisor = 1 + self.payload["customerServiceFeeFraction"]
        tutor_takehome = tutor_revenue / service_fee_offset_divisor * tutor.cut
        print(f"Tutor Takehome: {tutor_revenue}\n")
        if tutor_takehome > 0 and self.action == "send_direct_deposits":
            # Send direct deposit
            tutor_deposit = StripeDeposit(tutor["stripe_email"], tutor_takehome)
            success, payout_obj = tutor_deposit.send_direct_deposit(tutor_takehome)
        return {"success": success, "tutor_revenue": tutor_revenue, "amount_paid": tutor_takehome, "payout": payout_obj}

    def remove_at_from_ids(self) -> None:
        # Remove "@" and whitespaces from tutorID in tutors field
        for tutor_num in range(len(self.payload["tutors"])):
            self.payload["tutors"][tutor_num]["tutorID"] = self.payload["tutors"][tutor_num]["tutorID"].strip("@").strip()
        # Remove "@" and whitespaces from excludeFromPayoutsAndStripeTransfers field
        for tutor_num in range(len(self.payload["excludeFromPayoutsAndStripeTransfers"])):
            self.payload["excludeFromPayoutsAndStripeTransfers"][tutor_num] = self.payload["excludeFromPayoutsAndStripeTransfers"][tutor_num].strip("@").strip()
