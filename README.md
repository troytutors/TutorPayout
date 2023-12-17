# TutorPayout
Tutor Direct Deposit, Documentation, and Bank Transfer Software

### Requirements
TutorPayout requires Python 3.9.

### Installation
Poetry is used to manage package dependencies. Learn how to install
Poetry on your computer [here](https://python-poetry.org/docs/).

After you have poetry, run
```poetry install```
in the root of the project.

### Configure Environment Variables
This code requires your Stripe API key. In your Stripe dashboard, go to Developers,
copy your secret key, and paste it in the .env file.

### Square Invoice Export
In your Square Invoice dashboard, select your preferred Filter and Date, and select
export. Place the exported CSV filepath in your payload under squareInvoiceSummaryFilePath.

### Payload
Fill in **tutorpayrollpayload.json** to configure TutorPayout.
```json
{
    "periodName": "12-2023", # helps indentify payload and used as part of documentation filename
    "squareInvoiceSummaryFilePath": "/Users/zacknawrocki/Desktop/Troy Tutors Square Invoices/invoices-export-20231207T2002.csv", # filepath to Square invoice export
    "payrollDocumentPath": "/Users/zacknawrocki/Desktop/Troy Tutors Payroll Records/", # path to export documentation
    "customerServiceFeeFraction": 0.065, # the Troy Tutors custemer service fee percentage / 100
    "tutors": [
        {
            "name": "Troy T",
            "tutorID": "@troyt",
            "stripeEmail": "troyt@troytutors.com",
            "school": "RPI", # school the tutor tutors at
            "tutorCut": 0.8 # how much the tutor gets from a tutoring session (percentage / 100)
        }
    ],
    "excludeFromPayoutsAndStripeTransfers": [
        "@zacknawrocki",
        "",
        "@troytutors"
    ] # tutor IDs in Square invoice to ignore when handling TutorPayout requests
}
```

### Running TutorPayout
To launch TutorPayout, run ```poetry run python main.py```. Once launching, you are given three options
from the command line:

1. Check how much you should transfer to Stripe.
2. Send and document tutors' monthly direct deposit.
3. Document tutors' monthly direct deposit.

Enter "1" on the command line to see how much money to send to Stripe from your bank, in advance
before paying tutors. Enter "2" to send out and document direct deposits to tutors. Enter "3" to
save documentation for direct deposits, without sending direct deposits. This may be helpful if
you already paid direct deposits in the past, but might have lost your documentation and direct
deposit records, and need them for tax season or for tutors who requested their payroll history,
records, and/or info on payroll calculations.
