import re


# --------------------------------
# PATTERNS
# --------------------------------

# "₹18,850" or, if OCR keeps the rupee glyph as "Rs.18,850" / "Rs 18850"
AMOUNT_RE = re.compile(r"(?:₹|rs\.?)\s*([\d,]+(?:\.\d+)?)", re.IGNORECASE)

# The ₹ glyph is a common OCR weak spot - Tesseract often drops it
# entirely rather than misreading it, leaving the amount as a bare
# number on its own line (e.g. "255" with nothing else on that line).
# Used only as a fallback, and only before the transaction-details
# section starts, so it can't grab a UPI/reference/account number.
BARE_AMOUNT_LINE_RE = re.compile(r"^[\d,]+(?:\.\d{1,2})?$")

# A last-resort fallback for when OCR merges the amount onto the end
# of another line instead of ever isolating it (e.g. "ABDUL RAHEEM 35"
# or "X5304 235") - a short digit run at the very end of a line, not
# itself preceded by another digit (so it can't just be the tail of a
# much longer reference number).
TRAILING_AMOUNT_RE = re.compile(r"(?<!\d)(\d{1,6})\s*$")

DETAIL_SECTION_MARKERS = (
    "upi transaction id", "transaction id", "ref no", "reference no",
    "google transaction id", "utr"
)

# Explicit "To: <name>" / "From: <name>" detail lines, as shown in the
# transaction-details section every major UPI app includes.
TO_LABELED_RE = re.compile(r"(?im)^\s*to\s*:\s*(.+)$")
FROM_LABELED_RE = re.compile(r"(?im)^\s*from\s*:\s*(.+)$")

# The big, unlabeled headline some apps use instead ("To Bajaj Shree
# Jewellers"), rather than the colon-suffixed detail line.
TO_HEADLINE_RE = re.compile(
    r"(?im)^\s*to\s+([A-Z][A-Za-z0-9 .&'\-()]{2,60})\s*$"
)

# PhonePe's "Transaction Successful" layout puts the label alone on
# its own line ("Paid to"), with the name on the line after it, rather
# than on the same line as either the headline or the colon-suffixed
# detail style above.
TO_STANDALONE_LABEL_RE = re.compile(r"(?im)^\s*paid\s+to\s*$")
FROM_STANDALONE_LABEL_RE = re.compile(r"(?im)^\s*received\s+from\s*$")

# Date and time can appear in either order, sometimes joined by a
# literal word ("17 Sept 2026, 1:22 pm" on Google Pay, "11:57 AM,
# 17 Sep 2026" on Paytm, "09:49 am on 17 Sept 2026" on PhonePe).
_DATE = r"\d{1,2}\s+[A-Za-z]{3,9}\.?\s+\d{4}"
_TIME = r"\d{1,2}[:.]\d{2}\s*[APap]\.?[Mm]\.?"

DATE_THEN_TIME_RE = re.compile(rf"({_DATE})\s*,?\s*(?:at\s+)?({_TIME})")
TIME_THEN_DATE_RE = re.compile(rf"({_TIME})\s*,?\s*(?:on\s+)?({_DATE})")

# Words that signal money coming IN rather than going OUT.
CREDIT_HINTS = ("received", "credited")


def _strip_avatar_initials(name):
    """
    Many UPI apps show a colored circular avatar with 1-2 letter
    initials right beside the name, and OCR sometimes reads that as
    text on the same line - "AR ABDUL RAHEEM" instead of just
    "ABDUL RAHEEM". Strips a short all-caps prefix only when it
    actually matches the initials of the words that follow, so a
    genuine short business name (e.g. "MI STORE") isn't touched.
    """

    match = re.match(r"^([A-Z]{2,3})\s+(.+)$", name)

    if not match:
        return name

    initials, rest = match.group(1), match.group(2)
    rest_words = rest.split()

    if len(rest_words) < len(initials):
        return name

    expected_initials = "".join(
        word[0].upper() for word in rest_words[:len(initials)] if word
    )

    return rest if expected_initials == initials else name


def _clean_name(name):

    name = name.strip()

    name = _strip_avatar_initials(name)

    # Drop a trailing bank name in parentheses, e.g. "(Equitas Bank)"
    name = re.sub(r"\(.*?\)", "", name)

    # Drop a leading honorific, e.g. "Mr SACHIN JADHAV" -> "SACHIN JADHAV"
    name = re.sub(r"^(mr|mrs|ms|dr)\.?\s+", "", name, flags=re.IGNORECASE)

    # If OCR ran a UPI ID, bullet-masked account number, or the amount
    # onto the same line, cut it off there.
    name = re.split(r"[•*@₹]", name)[0]

    # Drop an amount that got glued onto the end of the same line
    # (a short, isolated digit run right at the end).
    name = re.sub(r"(?<!\d)\d{1,6}\s*$", "", name)

    return name.strip(" .:-")


def _find_label_then_next_line(lines, label_re):
    """
    For layouts where the "To"/"From" label sits alone on its own line
    and the actual name is the line right after it (PhonePe's
    "Transaction Successful" screen), rather than on the same line.
    """

    for index, line in enumerate(lines):

        if label_re.match(line) and index + 1 < len(lines):
            return lines[index + 1]

    return None


def _find_bare_amount(lines):
    """
    Fallback for when the ₹/Rs. marker got dropped by OCR: a line
    that's purely a short number. Heavily-recompressed images (a
    screenshot re-shared through WhatsApp, say) can OCR badly enough
    that reading order gets scrambled and the amount ends up appearing
    *after* the transaction-details section rather than before it, so
    this scans the whole text rather than stopping at the first
    detail marker - it only skips a number that directly follows a
    marker line, since that position is a reference/ID value, not the
    amount.
    """

    for index, line in enumerate(lines):

        if not BARE_AMOUNT_LINE_RE.match(line):
            continue

        digits_only = line.replace(",", "").replace(".", "")

        if not (1 <= len(digits_only) <= 7):
            continue

        previous_line = lines[index - 1].lower() if index > 0 else ""

        if any(marker in previous_line for marker in DETAIL_SECTION_MARKERS):
            continue

        return line

    return None


def _find_trailing_amount(lines):
    """
    Last-resort fallback: some OCR passes never isolate the amount on
    its own line at all - it stays glued to the end of the merchant
    name or the masked account number line. Looks for a short digit
    run at the end of a line, skipping anything that looks like a
    date/time (a trailing year would otherwise look like an amount)
    or a reference/ID line.
    """

    for index, line in enumerate(lines):

        if re.search(_DATE, line) or re.search(_TIME, line):
            continue

        lowered = line.lower()

        if any(marker in lowered for marker in DETAIL_SECTION_MARKERS):
            continue

        previous_line = lines[index - 1].lower() if index > 0 else ""

        if any(marker in previous_line for marker in DETAIL_SECTION_MARKERS):
            continue

        match = TRAILING_AMOUNT_RE.search(line)

        if match:
            return match.group(1)

    return None


def extract_transaction_from_screenshot(text):
    """
    Parses a single transaction out of OCR'd text from a UPI app's
    payment-confirmation screenshot (Google Pay, PhonePe, Paytm, ...).

    Unlike extract_transactions() (which scans a whole bank statement
    for many transactions), a screenshot only ever shows one - so this
    returns a list of zero or one transaction, kept as a list so both
    extractors have the same shape for callers.
    """

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if not lines:
        return []

    joined = "\n".join(lines)

    amount_match = AMOUNT_RE.search(joined)

    if amount_match:

        amount_text = amount_match.group(1)

    else:

        amount_text = _find_bare_amount(lines) or _find_trailing_amount(lines)

        if not amount_text:
            return []

    amount = float(amount_text.replace(",", ""))

    is_credit = any(hint in joined.lower() for hint in CREDIT_HINTS)
    transaction_type = "CREDIT" if is_credit else "DEBIT"

    merchant = ""

    if is_credit:

        match = FROM_LABELED_RE.search(joined)

        if match:
            merchant = _clean_name(match.group(1))

        if not merchant:

            standalone = _find_label_then_next_line(
                lines, FROM_STANDALONE_LABEL_RE
            )

            if standalone:
                merchant = _clean_name(standalone)

    else:

        match = TO_LABELED_RE.search(joined) or TO_HEADLINE_RE.search(joined)

        if match:
            merchant = _clean_name(match.group(1))

        if not merchant:

            standalone = _find_label_then_next_line(
                lines, TO_STANDALONE_LABEL_RE
            )

            if standalone:
                merchant = _clean_name(standalone)

    if not merchant:

        # Whichever labeled line exists, even if it doesn't match the
        # direction we guessed - better than no name at all.
        fallback = TO_LABELED_RE.search(joined) or FROM_LABELED_RE.search(joined)

        if fallback:
            merchant = _clean_name(fallback.group(1))

    if not merchant:
        return []

    date = ""
    time = ""

    date_time_match = DATE_THEN_TIME_RE.search(joined)

    if date_time_match:
        date, time = date_time_match.group(1), date_time_match.group(2)

    else:

        time_date_match = TIME_THEN_DATE_RE.search(joined)

        if time_date_match:
            time, date = time_date_match.group(1), time_date_match.group(2)

    return [{
        "date": date,
        "time": time,
        "type": transaction_type,
        "amount": amount,
        "merchant": merchant
    }]
