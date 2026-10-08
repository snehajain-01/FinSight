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

# Sometimes the ₹ glyph doesn't get dropped outright but is misread as
# a stray symbol (e.g. "#20 Split Expense" for "₹20  Split Expense"),
# gluing the amount to the start of a button/label line instead of it
# ever landing on its own. Matches a short digit run right at the
# start of a line - allowing a couple of stray symbol characters
# before it - followed by whitespace then a letter, i.e. more text
# continues on the line rather than the digits being part of a longer
# ID (which wouldn't have whitespace right after these digits).
LEADING_AMOUNT_RE = re.compile(r"^\W{0,2}(\d{1,6}(?:\.\d{1,2})?)\s+[A-Za-z]")

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

# Some receipts (GPay's "Paid Successfully" screen) show the date
# without a year at all ("6 Sep, 04:35 PM") - used only once the
# year-inclusive patterns above have already failed to match.
_DATE_NO_YEAR = r"\d{1,2}\s+[A-Za-z]{3,9}\.?"
DATE_NO_YEAR_THEN_TIME_RE = re.compile(rf"({_DATE_NO_YEAR})\s*,?\s*(?:at\s+)?({_TIME})")
TIME_THEN_DATE_NO_YEAR_RE = re.compile(rf"({_TIME})\s*,?\s*(?:on\s+)?({_DATE_NO_YEAR})")

# Words that signal money coming IN rather than going OUT.
CREDIT_HINTS = ("received", "credited")

# Some layouts (a generic UPI-intent "Payment Successful" confirmation,
# rather than GPay/PhonePe/Paytm's own "To:"/"Paid to" screens) show the
# payee name as a plain headline right under the success banner, with
# no label at all.
SUCCESS_HEADER_RE = re.compile(r"(?i)\b(?:payment|transaction)\s+successful\b")

# Lines that can sit between the success banner and the actual name
# (or right after it) but obviously aren't a name themselves.
NON_NAME_LINE_RE = re.compile(
    r"(?i)^(?:split expense|view details|share receipt|done|paid|"
    r"received|amount|total)\b"
)

# Google Pay's "Paid Successfully" receipt shows the recipient's name
# and UPI ID *before* this banner, with the sender's own name coming
# right after it - the reverse order from the "Payment/Transaction
# Successful" layouts above, so it needs its own marker rather than
# reusing SUCCESS_HEADER_RE (which would otherwise mis-fire here and
# grab the sender's name from the line that follows).
PAID_SUCCESSFULLY_RE = re.compile(r"(?i)\bpaid\s+successfully\b")

# A plausible "Firstname Lastname" style name: 2-5 capitalized words
# and nothing else on the line - a single-word app logo line (e.g.
# "Paytm") doesn't match, so it's naturally skipped over.
PLAUSIBLE_NAME_RE = re.compile(r"^[A-Z][a-zA-Z.'-]*(?:\s+[A-Z][a-zA-Z.'-]*){1,4}$")

# An amount spelled out in words ("One Thousand Seven Hundred Sixty
# Rupees"), as GPay's "Paid Successfully" receipt shows alongside the
# digits - and worth trusting *more* than the digits, since spelled-out
# words aren't vulnerable to the digit-glyph misreads (e.g. "1,760"
# OCR'd as "1,/60") that plague the numeric amount on this layout.
SPELLED_AMOUNT_RE = re.compile(r"(?i)^([a-z ]+?)\s+rupees?\b")

_NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

_SCALE_WORDS = {
    "hundred": 100, "thousand": 1000, "lakh": 100000, "lac": 100000,
    "crore": 10000000,
}


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

    Uses the *last* match rather than the first: the header banner
    (date/time + "Paid to"/"Received from") often gets OCR'd twice -
    once by ocr_service's dedicated header-region pass, then again as
    part of the full-image pass - so the same label line can appear
    back-to-back before the real content. Taking the first match would
    return the second copy of the duplicated header instead of the
    actual name that follows the real occurrence.
    """

    last_match_index = None

    for index, line in enumerate(lines):

        if label_re.match(line):
            last_match_index = index

    if last_match_index is not None and last_match_index + 1 < len(lines):
        return lines[last_match_index + 1]

    return None


def _find_name_after_success_header(lines):
    """
    Fallback for layouts with no "To:"/"Paid to" label at all - just a
    "Payment Successful" (or "Transaction Successful") banner followed
    by the payee's name as a plain headline. Returns the first line
    after the banner that isn't a date/time, an amount, a bare avatar
    initials line, a UPI ID, or one of the button/label lines that can
    appear nearby (e.g. "Split Expense").
    """

    for index, line in enumerate(lines):

        if not SUCCESS_HEADER_RE.search(line):
            continue

        for candidate in lines[index + 1:]:

            if (
                DATE_THEN_TIME_RE.search(candidate)
                or TIME_THEN_DATE_RE.search(candidate)
                or re.search(_DATE, candidate)
                or re.search(_TIME, candidate)
            ):
                continue

            if AMOUNT_RE.search(candidate) or BARE_AMOUNT_LINE_RE.match(candidate):
                continue

            if "@" in candidate or NON_NAME_LINE_RE.match(candidate):
                continue

            if any(
                marker in candidate.lower() for marker in DETAIL_SECTION_MARKERS
            ):
                continue

            # A lone 1-3 letter avatar-initials line, with nothing else
            # on it (as opposed to "AR ABDUL RAHEEM", which _clean_name
            # already knows how to strip the initials from).
            if re.match(r"^[A-Z]{1,3}$", candidate):
                continue

            return candidate

        break

    return None


def _find_name_before_paid_successfully(lines):
    """
    Fallback for GPay's "Paid Successfully" receipt: the recipient's
    name appears near the top, before their UPI ID, the amount, and
    the "Paid Successfully" banner - rather than after a "Payment
    Successful" banner, or next to a "To:"/"Paid to" label. Scans from
    the top for the first plausible two-or-more-word capitalized name,
    stopping as soon as it hits the UPI ID, the amount, the banner, or
    a date/time - all of which mean the name has already been passed.
    """

    for line in lines:

        if (
            "@" in line
            or AMOUNT_RE.search(line)
            or BARE_AMOUNT_LINE_RE.match(line)
            or PAID_SUCCESSFULLY_RE.search(line)
            or re.search(_DATE, line)
            or re.search(_TIME, line)
        ):
            break

        if PLAUSIBLE_NAME_RE.match(line):
            return line

    return None


def _words_to_number(phrase):
    """
    Converts a spelled-out English number ("one thousand seven hundred
    sixty") to an int, Indian-numbering aware (lakh/crore). Returns
    None if any word isn't recognized.
    """

    total = 0
    current = 0
    matched_any = False

    for word in phrase.lower().replace("-", " ").split():

        if word == "and":
            continue

        if word in _NUMBER_WORDS:
            current += _NUMBER_WORDS[word]
            matched_any = True

        elif word in _SCALE_WORDS:

            scale = _SCALE_WORDS[word]

            if scale == 100:
                current = (current or 1) * scale
            else:
                total += (current or 1) * scale
                current = 0

            matched_any = True

        else:
            return None

    if not matched_any:
        return None

    return total + current


def _find_spelled_out_amount(lines):

    for line in lines:

        match = SPELLED_AMOUNT_RE.match(line.strip())

        if match:

            value = _words_to_number(match.group(1))

            if value is not None:
                return value

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


def _find_leading_amount(lines):
    """
    Fallback for a misread (rather than dropped) ₹ glyph: a short
    digit run at the very start of a line, immediately followed by
    more text on the same line (e.g. "#20 Split Expense"). Skips
    date/time lines so a leading day-of-month ("18 September...")
    doesn't get mistaken for an amount.
    """

    for index, line in enumerate(lines):

        if re.search(_DATE, line) or re.search(_TIME, line):
            continue

        lowered = line.lower()

        if any(marker in lowered for marker in DETAIL_SECTION_MARKERS):
            continue

        match = LEADING_AMOUNT_RE.match(line)

        if match:
            return match.group(1)

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

        amount = float(amount_match.group(1).replace(",", ""))

    else:

        spelled_amount = _find_spelled_out_amount(lines)

        if spelled_amount is not None:

            # Trust the spelled-out words over any digit-based
            # fallback below - they aren't vulnerable to the
            # digit-glyph misreads (e.g. "1,760" OCR'd as "1,/60")
            # that the digit fallbacks exist to work around.
            amount = float(spelled_amount)

        else:

            amount_text = (
                _find_bare_amount(lines)
                or _find_leading_amount(lines)
                or _find_trailing_amount(lines)
            )

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

        candidate = _find_name_after_success_header(lines)

        if candidate:
            merchant = _clean_name(candidate)

    if not merchant and not is_credit:

        candidate = _find_name_before_paid_successfully(lines)

        if candidate:
            merchant = _clean_name(candidate)

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

        else:

            no_year_match = (
                DATE_NO_YEAR_THEN_TIME_RE.search(joined)
                or TIME_THEN_DATE_NO_YEAR_RE.search(joined)
            )

            if no_year_match:

                first, second = no_year_match.group(1), no_year_match.group(2)

                if re.match(_TIME, first):
                    time, date = first, second
                else:
                    date, time = first, second

    return [{
        "date": date,
        "time": time,
        "type": transaction_type,
        "amount": amount,
        "merchant": merchant
    }]
