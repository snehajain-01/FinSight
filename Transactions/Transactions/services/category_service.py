import os
import re
import uuid

import joblib

from database.database import get_merchant_categories_map


# --------------------------------
# CATEGORIES
# --------------------------------

CATEGORIES = [
    "Food",
    "Travel",
    "Shopping",
    "Bills and Utilities",
    "Healthcare",
    "Entertainment",
    "Savings",
    "Education",
    "Others"
]

DEFAULT_CATEGORY = "Others"


# --------------------------------
# KEYWORDS
# (checked longest-keyword-first, so a specific phrase like
# "swiggy instamart" wins over a generic one like "swiggy")
# --------------------------------

CATEGORY_KEYWORDS = {

    # Dining + groceries - both are "buying food" from the user's point
    # of view.
    "Food": [
        "swiggy", "zomato", "restaurant", "cafe", "coffee", "dine",
        "eatery", "kitchen", "biryani", "pizza", "dominos", "mcdonald",
        "kfc", "starbucks", "burger", "bakery", "dhaba", "food court",
        "bigbasket", "big basket", "grofers", "zepto", "blinkit",
        "grocery", "groceries", "supermarket", "dmart", "d-mart",
        "reliance fresh", "swiggy instamart", "instamart",
        "more supermarket", "spencer", "nature basket"
    ],

    # Transportation (commuting/fuel) folds in here alongside travel
    # bookings - both are "getting somewhere".
    "Travel": [
        "uber", "ola", "rapido", "metro", "irctc", "bus", "petrol",
        "diesel", "fuel", "fastag", "parking", " cab", "auto rickshaw",
        "indian oil", "bharat petroleum", "hp petrol", "shell petrol",
        "flight", "airlines", "indigo", "spicejet", "air india",
        "vistara", "makemytrip", "goibibo", "yatra", "airbnb", "oyo",
        "booking.com", "hotel"
    ],

    "Shopping": [
        "amazon", "flipkart", "myntra", "ajio", "meesho", "nykaa fashion",
        "reliance trends", "lifestyle store", "pantaloons", "clothing",
        "electronics store", "shopping mall",
        "salon", "spa", "parlour", "cosmetics", "skincare", "makeup",
        "nykaa", "haircut", "grooming", "barber"
    ],

    # Recurring charges (subscriptions), rent/maintenance and loan EMIs
    # are all bill-like obligations.
    "Bills and Utilities": [
        "electricity", "water bill", "broadband", "internet bill",
        "recharge", "mobile bill", "postpaid", "prepaid", "wifi bill",
        "gas bill", "airtel", "jio", "vodafone", "bses", "tata power",
        "adani electricity", "dth",
        "subscription", "membership", "adobe", "microsoft 365",
        "google one", "icloud", "software renewal", "saas",
        "rent", "society maintenance", "maintenance charge", "landlord",
        "house rent", "housing society",
        "emi", "loan installment", "loan emi"
    ],

    "Healthcare": [
        "hospital", "clinic", "pharmacy", "medical store", "medicine",
        "doctor", "apollo", "pathology", "diagnostic", "lab test",
        "netmeds", "1mg", "pharmeasy", "dentist"
    ],

    "Entertainment": [
        "netflix", "bookmyshow", "pvr", "inox", "cinema", "movie",
        "spotify", "wynk", "gaana", "gaming", "steam", "playstation",
        "xbox", "concert", "hotstar", "sonyliv", "zee5"
    ],

    "Savings": [
        "mutual fund", " sip ", "zerodha", "groww", "upstox", "stocks",
        "fixed deposit", "recurring deposit", " nps ", " ppf ",
        "investment", "demat"
    ],

    "Education": [
        "college", "university", "school fee", "school", "tuition",
        "udemy", "coursera", "byjus", "unacademy", "vedantu", "upgrad",
        "stationery", "exam fee", "course fee", "semester fee",
        "admission fee", "coaching institute", "coaching center"
    ],

    # Things that are obviously neither spending nor saving - a plain
    # transfer, refund or cashback - go straight to Others with
    # confidence, instead of making the user confirm the obvious.
    "Others": [
        "cashback", "reward", "refund", "reversal", "chargeback",
        "self transfer", "fund transfer", "neft", "imps", "rtgs"
    ]

}

_KEYWORD_LOOKUP = sorted(
    (
        (keyword.lower(), category)
        for category, keywords in CATEGORY_KEYWORDS.items()
        for keyword in keywords
    ),
    key=lambda pair: len(pair[0]),
    reverse=True
)


# --------------------------------
# ML MODEL (ml/finsight_svm_model.pkl + ml/finsight_tfidf_vectorizer.pkl)
# A LinearSVC trained on Indian bank-SMS transaction text, used as a
# second opinion for merchants the keyword list above doesn't cover.
# --------------------------------

# services/ -> Transactions/Transactions -> Transactions -> FinSight -> ml
_ML_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "ml"
)

_ML_SCORE_THRESHOLD = 0.7

# The model's 13 native labels are broader than our 8 categories, so
# several of them collapse onto the same bucket here.
ML_LABEL_TO_CATEGORY = {
    "bills": "Bills and Utilities",
    "cashback": "Others",
    "emi": "Bills and Utilities",
    "entertainment": "Entertainment",
    "food": "Food",
    "grocery": "Food",
    "healthcare": "Healthcare",
    "investment": "Savings",
    "refund": "Others",
    "shopping": "Shopping",
    "transfer": "Others",
    "transport": "Travel",
    "travel": "Travel"
}

try:

    _ml_model = joblib.load(
        os.path.join(_ML_DIR, "finsight_svm_model.pkl")
    )

    _ml_vectorizer = joblib.load(
        os.path.join(_ML_DIR, "finsight_tfidf_vectorizer.pkl")
    )

except Exception:

    # If the model files are missing or incompatible, fall back to the
    # keyword/heuristic path only rather than breaking uploads.
    _ml_model = None
    _ml_vectorizer = None


# --------------------------------
# KEYWORD-DRIVEN CATEGORY CLASSIFIER
# (ml/finsight_category_model.pkl + ml/finsight_category_vectorizer.pkl)
# The main model above was trained on real bank SMS text and has no
# notion of our 9 categories (or "education" at all) - retraining it
# would mean re-downloading and re-fitting its whole 137k-row source
# dataset. Instead, this is a separate multi-class classifier trained
# on synthetic examples built from merchant names containing each
# category's related words (e.g. a name containing "food" is drawn
# from the Food pool) - so the label comes from the same word-match
# rule the keyword list above uses, just applied while building
# training data instead of at prediction time. See
# ml/train_category_classifier.py.
# --------------------------------

_CATEGORY_MODEL_SCORE_THRESHOLD = 0.75

try:

    _category_model = joblib.load(
        os.path.join(_ML_DIR, "finsight_category_model.pkl")
    )

    _category_vectorizer = joblib.load(
        os.path.join(_ML_DIR, "finsight_category_vectorizer.pkl")
    )

except Exception:

    _category_model = None
    _category_vectorizer = None


def _predict_by_keyword_model(merchant, is_debit):
    """
    Returns (category, confidence) using the keyword-trained model, or
    (None, 0.0) if it isn't available or the merchant is blank.
    """

    if not _category_model or not merchant:
        return None, 0.0

    verb = "paid to" if is_debit else "received from"
    cleaned = _clean_for_ml(f"{verb} {merchant}")

    if not cleaned:
        return None, 0.0

    vector = _category_vectorizer.transform([cleaned])
    probabilities = _category_model.predict_proba(vector)[0]

    best_index = probabilities.argmax()
    best_category = _category_model.classes_[best_index]
    best_confidence = float(probabilities[best_index])

    return best_category, best_confidence


def _clean_for_ml(text):
    """
    Mirrors the exact preprocessing the model was trained with (see
    ml/Untitled.ipynb) - lowercase, strip account numbers, amounts and
    punctuation, so the vectorizer sees text shaped like its training
    data.
    """

    text = str(text or "").lower()

    text = re.sub(r"\bxx\d+\b", " ", text)
    text = re.sub(r"rs\.?\s*[\d,]+(?:\.\d+)?", " ", text)
    text = re.sub(r"inr\s*[\d,]+(?:\.\d+)?", " ", text)
    text = re.sub(r"\b\d+(?:\.\d+)?\b", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def _ml_predict(merchant, is_debit):
    """
    Returns (category, raw_score) using the trained model, or (None, 0)
    if the model isn't available, the merchant is blank, or its
    top prediction doesn't map onto one of our categories.
    """

    if not _ml_model or not merchant:
        return None, 0.0

    verb = "paid to" if is_debit else "received from"
    cleaned = _clean_for_ml(f"{verb} {merchant}")

    if not cleaned:
        return None, 0.0

    vector = _ml_vectorizer.transform([cleaned])
    scores = _ml_model.decision_function(vector)[0]

    best_index = scores.argmax()
    best_label = _ml_model.classes_[best_index]
    best_score = float(scores[best_index])

    category = ML_LABEL_TO_CATEGORY.get(best_label)

    return category, best_score

# A bare "First Last" / "SINGLEWORD" style merchant with no matched
# keyword is more likely a person-to-person payment than a business.
_NAME_LIKE_RE = re.compile(r"^[A-Za-z]+(\s+[A-Za-z]+){0,3}$")

MATCHED_CONFIDENCE = 0.85
GUESSED_CONFIDENCE = 0.2
CONFIDENCE_THRESHOLD = 0.5


def normalize_merchant(merchant):

    return re.sub(
        r"\s+",
        " ",
        (merchant or "")
    ).strip().lower()


def merchant_identity_key(merchant):
    """
    A whitespace-insensitive identity key for "is this the same
    merchant" purposes (the learned-category map, and the confirm-once
    "never ask again" logic) - distinct from normalize_merchant(),
    which keeps single spaces so multi-word keywords like "big basket"
    can still match. Different extractors format the same real-world
    name differently (the bank-statement PDF parser concatenates it as
    "ABDULRAHEEM"; the screenshot OCR path naturally keeps the space,
    "ABDUL RAHEEM") - without stripping whitespace entirely here, those
    would be treated as two unrelated merchants and the app would keep
    asking for a category it already knows.
    """

    return re.sub(
        r"\s+",
        "",
        (merchant or "")
    ).lower()


def predict_category(merchant, is_debit=True):
    """
    Returns (category, confidence) for a merchant name. Tries, in order:
    1. our curated keyword list (fast, precise brand/domain matches)
    2. the keyword-trained category classifier, when confident (checked
       before the main model, since it knows all 9 of our categories -
       including Education, which the main model has never heard of -
       and would otherwise confidently misfile it elsewhere)
    3. the trained ML model (ml/finsight_svm_model.pkl), when confident
    4. a "this looks like a person" guess (defaults to Others)
    5. a low-confidence ML guess, if it had one
    6. Others, as a last resort

    Confidence below CONFIDENCE_THRESHOLD means the caller should ask
    the user to confirm/pick the category themselves.
    """

    matched_category = _match_keyword(merchant)

    if matched_category:
        return matched_category, MATCHED_CONFIDENCE

    keyword_model_category, keyword_model_score = _predict_by_keyword_model(
        merchant, is_debit
    )

    if (
        keyword_model_category
        and keyword_model_score >= _CATEGORY_MODEL_SCORE_THRESHOLD
    ):
        return keyword_model_category, MATCHED_CONFIDENCE

    ml_category, ml_score = _ml_predict(merchant, is_debit)

    if ml_category and ml_score >= _ML_SCORE_THRESHOLD:
        return ml_category, MATCHED_CONFIDENCE

    if is_person_like(merchant):
        return DEFAULT_CATEGORY, GUESSED_CONFIDENCE

    if ml_category:
        return ml_category, GUESSED_CONFIDENCE

    return DEFAULT_CATEGORY, GUESSED_CONFIDENCE


def _match_keyword(merchant):

    normalized = normalize_merchant(merchant)

    for keyword, category in _KEYWORD_LOOKUP:

        if keyword in normalized:
            return category

    return None


def is_person_like(merchant):
    """
    True for a merchant name that looks like a person rather than a
    business (no recognized keyword, and shaped like "First Last" or a
    single name) - e.g. a friend on a UPI transfer. Used to pick a
    sensible default guess (Others) and to show a hint on the
    Confirm Categories screen.
    """

    if not merchant:
        return False

    if _match_keyword(merchant) is not None:
        return False

    return bool(_NAME_LIKE_RE.match(merchant.strip()))


def apply_categories(transactions, user_id):
    """
    Assigns a stable id and a category to every transaction. A merchant
    the user has manually categorized before (learned_categories) always
    wins over a fresh guess from the keyword list or the ML model.
    """

    learned = get_merchant_categories_map(user_id)

    for transaction in transactions:

        transaction["id"] = str(uuid.uuid4())

        merchant = transaction.get("merchant")
        merchant_key = merchant_identity_key(merchant)
        is_debit = (transaction.get("type") or "").upper() == "DEBIT"

        transaction["is_person"] = is_person_like(merchant)

        if merchant_key and merchant_key in learned:

            transaction["category"] = learned[merchant_key]
            transaction["confidence"] = 1.0
            transaction["needs_review"] = False
            continue

        category, confidence = predict_category(merchant, is_debit)

        transaction["category"] = category
        transaction["confidence"] = confidence
        transaction["needs_review"] = confidence < CONFIDENCE_THRESHOLD

    return transactions
