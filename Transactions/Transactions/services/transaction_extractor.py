import re


# PhonePe-style: "Aug 26, 2026"
PHONEPE_DATE_RE = re.compile(
    r"^[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}$"
)

# Google Pay-style: "01Feb,2026"
GPAY_DATE_RE = re.compile(
    r"^\d{1,2}[A-Z][a-z]{2},\d{4}$"
)

GPAY_DEBIT_RE = re.compile(r"^Paidto(.+)$", re.IGNORECASE)
GPAY_CREDIT_RE = re.compile(r"^Receivedfrom(.+)$", re.IGNORECASE)

AMOUNT_RE = re.compile(r"^₹[\d,]+(?:\.\d+)?$")


def _clean_amount(text):

    digits = re.sub(
        r"[^\d.]",
        "",
        text
    )

    return float(digits) if digits else 0.0


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

        line = lines[i]


        # -------------------------
        # PHONEPE-STYLE STATEMENT
        # date / time / type / amount / "Paid to <merchant>"
        # -------------------------

        if PHONEPE_DATE_RE.match(line):

            transaction = {
                "date": line,
                "time": "",
                "type": "",
                "amount": 0.0,
                "merchant": ""
            }

            if i + 1 < len(lines):
                transaction["time"] = lines[i + 1]

            if i + 2 < len(lines):
                transaction["type"] = lines[i + 2].upper()

            if i + 3 < len(lines):
                transaction["amount"] = _clean_amount(lines[i + 3])

            if i + 4 < len(lines):

                merchant_line = lines[i + 4]

                if merchant_line.lower().startswith("paid to"):
                    transaction["merchant"] = merchant_line[7:].strip()

            if transaction["type"] in ["DEBIT", "CREDIT"]:
                transactions.append(transaction)


        # -------------------------
        # GOOGLE PAY-STYLE STATEMENT
        # date / time / "Paidto<merchant>" or "Receivedfrom<merchant>" /
        # UPI transaction id / paid-by bank / amount
        # -------------------------

        elif GPAY_DATE_RE.match(line):

            time_line = lines[i + 1] if i + 1 < len(lines) else ""
            detail_line = lines[i + 2] if i + 2 < len(lines) else ""

            debit_match = GPAY_DEBIT_RE.match(detail_line)
            credit_match = GPAY_CREDIT_RE.match(detail_line)

            if debit_match or credit_match:

                transaction = {
                    "date": line,
                    "time": time_line,
                    "type": "DEBIT" if debit_match else "CREDIT",
                    "amount": 0.0,
                    "merchant":
                        (debit_match or credit_match).group(1).strip()
                }

                # The amount sits a couple of lines further down, after
                # the UPI transaction id and payment-method lines - scan
                # ahead for it instead of assuming a fixed offset, and
                # bail out if we run into the next record first.
                window_end = min(i + 8, len(lines))

                for lookahead in range(i + 3, window_end):

                    candidate = lines[lookahead]

                    if (
                        PHONEPE_DATE_RE.match(candidate)
                        or GPAY_DATE_RE.match(candidate)
                    ):
                        break

                    if AMOUNT_RE.match(candidate):
                        transaction["amount"] = _clean_amount(candidate)
                        break

                transactions.append(transaction)

        i += 1


    return transactions
