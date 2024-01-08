from typing import Any, Mapping, Text


class Tutor:
    # Object to represent a tutor's information
    def __init__(self, tutor_data: Mapping[Text, Any]) -> None:
        self.name = tutor_data["name"]
        self.id = tutor_data["tutorID"]
        self.stripe_email = tutor_data["stripeEmail"]
        self.school = tutor_data["school"]
        self.cut = tutor_data["tutorCut"]
