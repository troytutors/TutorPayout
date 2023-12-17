from payout_modules.payroll_manager import PayrollManager
from typing import Any

PAYLOAD_PATH = "tutorpayrollpayload.json"


def request_action() -> Any:
    print("Would you like to")
    print("1. Check how much you should transfer to Stripe.")
    print("2. Send and document tutors' monthly direct deposits.")
    print("3. Document tutors' monthly direct deposits.")
    command_actions = {"1": "calculate_stripe_transfer", "2": "send_direct_deposits", "3": "document_only"}
    command = None
    # Let the user specify how to use TutorPayout via the command line
    while command != "1" and command != "2" and command != "3":
        command = input("(1, 2, 3) ====> ").strip()
    # Extra security measure for direct deposit
    approve = None
    if command == "2":
        while approve != "Y" and approve != "N":
            approve = input("Caution: You are about to send direct deposits to every tutor, based on what is "
                            "listed in the Square data, using the money currently in your Stripe bank. This "
                            "cannot be undone easily. Are you sure you are intending to send out direct "
                            "deposits? (Y, N) ====> ")
        if approve == "N":
            return
    return command_actions[command]


def main() -> Any:
    action = request_action()
    # If user decides to not send out direct deposits, after initially requesting action 2
    if not action:
        return
    pm = PayrollManager(PAYLOAD_PATH)
    pm.handle_request(action)


if __name__ == "__main__":
    main()
