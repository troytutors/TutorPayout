from payrollmanager import PayrollManager

PAYLOAD_PATH = "tutorpayrollpayload.json"


def request_action():
    print("Would you like to")
    print("1. Check how much you should transfer to Stripe.")
    print("2. Send and document tutors monthly direct deposit.")
    print("3. Document tutors monthly direct deposit.")
    command_actions = {"1": "calculate_stripe_transfer", "2": "send_direct_deposits", "3": "document_only"}
    command = None
    # Let the user specify how to use TutorPayout via the command line
    while command != "1" and command != "2" and command != "3":
        command = input("(1, 2, 3) ====> ").strip()
    return command_actions[command]


def main():
    action = request_action(PAYLOAD_PATH)
    pm = PayrollManager(action)
    pm.handle_request(action)


if __name__ == "__main__":
    main()
