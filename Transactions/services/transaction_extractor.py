import re


def extract_transactions(text):

    transactions = []

    # Split extracted PDF text into clean lines
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    i = 0

    while i < len(lines):

        # Look for a date like:
        # Aug 26, 2026
        if re.match(
            r"^[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}$",
            lines[i]
        ):

            date = lines[i]

            transaction = {
                "date": date,
                "time": "",
                "type": "",
                "amount": 0.0,
                "merchant": ""
            }

            # -------------------------
            # GET TIME
            # -------------------------

            if i + 1 < len(lines):

                transaction["time"] = lines[i + 1]


            # -------------------------
            # GET TYPE
            # -------------------------

            if i + 2 < len(lines):

                transaction["type"] = (
                    lines[i + 2].upper()
                )


            # -------------------------
            # GET AMOUNT
            # -------------------------

            if i + 3 < len(lines):

                amount_text = lines[i + 3]

                # Remove ₹, commas, etc.
                amount_text = re.sub(
                    r"[^\d.]",
                    "",
                    amount_text
                )

                if amount_text:

                    transaction["amount"] = float(
                        amount_text
                    )


            # -------------------------
            # GET MERCHANT
            # -------------------------

            if i + 4 < len(lines):

                merchant_line = lines[i + 4]

                if merchant_line.lower().startswith(
                    "paid to"
                ):

                    transaction["merchant"] = (
                        merchant_line[7:].strip()
                    )


            # Only add valid transactions
            if (
                transaction["type"]
                in ["DEBIT", "CREDIT"]
            ):

                transactions.append(
                    transaction
                )

        i += 1


    return transactions