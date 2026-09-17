"""
Trains FinSight's keyword-driven category classifier.

The idea: instead of hand-labeling training examples, each synthetic
transaction is BUILT from a merchant name that already contains a
word related to one category (e.g. a name containing "food" or
"restaurant" is drawn from the Food pool) - so the label is decided by
which keyword pool the example came from, automatically, at generation
time. That's the same rule the app already applies at prediction time
(services/category_service.py's keyword matcher) - this script applies
it while building training data instead, so the model itself also
learns "this kind of wording -> this category", not just exact
keyword hits.

This replaces the earlier education-only classifier
(finsight_education_model.pkl / finsight_education_vectorizer.pkl,
now superseded) with one multi-class model covering all 9 FinSight
categories:
    ml/finsight_category_model.pkl
    ml/finsight_category_vectorizer.pkl

It does NOT touch finsight_svm_model.pkl / finsight_tfidf_vectorizer.pkl
(the model trained on the real 137k-row dataset) - that one stays as
the broader, real-world-trained second opinion; this one is the fast,
keyword-grounded first opinion services/category_service.py checks
before it.

Re-run this script any time you want to regenerate the model (e.g.
after adding more merchant names or categories below).
"""

import random
import re

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report


random.seed(42)


# --------------------------------
# TEXT CLEANING
# (mirrors clean_transaction() in Untitled.ipynb, so every model in
# this folder sees text preprocessed the same way)
# --------------------------------

def clean_transaction(text):

    text = str(text).lower()
    text = re.sub(r"\bxx\d+\b", " ", text)
    text = re.sub(r"rs\.?\s*[\d,]+(?:\.\d+)?", " ", text)
    text = re.sub(r"inr\s*[\d,]+(?:\.\d+)?", " ", text)
    text = re.sub(r"\b\d+(?:\.\d+)?\b", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


# --------------------------------
# PER-CATEGORY MERCHANT NAME POOLS
# Every entry contains a word related to its category (the same
# keywords services/category_service.py's runtime matcher looks for) -
# that relatedness IS the label, so no example needs to be hand-tagged.
# --------------------------------

CATEGORY_MERCHANTS = {

    "Food": [
        "Swiggy Food Delivery", "Zomato Food Order", "Dominos Pizza",
        "McDonald's Restaurant", "KFC Restaurant", "Starbucks Coffee",
        "Cafe Coffee Day", "Barbeque Nation Restaurant", "City Food Court",
        "Behrouz Biryani", "Faasos Food", "Punjabi Dhaba",
        "Sagar Ratna Restaurant", "BigBasket Grocery", "Blinkit Grocery",
        "Zepto Grocery Delivery", "DMart Supermarket",
        "Nature's Basket Grocery", "Spencer's Retail Grocery",
        "More Supermarket"
    ],

    "Travel": [
        "Uber Cab", "Ola Cabs", "Rapido Bike Taxi", "IRCTC Train Booking",
        "Indian Oil Petrol Pump", "Bharat Petroleum Fuel",
        "HP Petrol Pump", "Metro Rail Card Recharge", "City Bus Pass",
        "FASTag Toll Recharge", "IndiGo Airlines", "SpiceJet Airlines",
        "Air India Flight", "Vistara Airlines", "MakeMyTrip Travel",
        "Goibibo Travel Booking", "Yatra Travels", "OYO Rooms Hotel",
        "Airbnb Booking", "Taj Hotel Booking"
    ],

    "Shopping": [
        "Amazon Shopping", "Flipkart Shopping", "Myntra Fashion",
        "Ajio Clothing", "Meesho Shopping", "Reliance Trends Clothing",
        "Pantaloons Fashion", "Lifestyle Store", "Croma Electronics Store",
        "Nykaa Cosmetics", "Lakme Salon", "VLCC Spa",
        "Urban Company Grooming", "Big Bazaar Shopping Mall"
    ],

    "Bills and Utilities": [
        "Airtel Mobile Recharge", "Jio Mobile Bill", "Vodafone Idea Bill",
        "BSES Electricity Bill", "Tata Power Electricity Bill",
        "Adani Electricity Bill", "Mahanagar Gas Bill",
        "ACT Broadband Internet Bill", "Netflix Subscription",
        "Amazon Prime Membership", "Spotify Subscription Renewal",
        "Society Maintenance Charges", "House Rent Payment",
        "Home Loan EMI", "Car Loan EMI Payment"
    ],

    "Healthcare": [
        "Apollo Pharmacy", "Netmeds Pharmacy", "1mg Pharmacy",
        "PharmEasy Medicine", "Fortis Hospital", "Max Healthcare Hospital",
        "AIIMS Hospital Billing", "City Medical Store",
        "Dr. Lal Pathology Lab", "Family Dental Clinic",
        "City Diagnostic Center"
    ],

    "Entertainment": [
        "Netflix Streaming", "Hotstar Subscription", "SonyLIV Streaming",
        "Zee5 Subscription", "BookMyShow Movie Ticket",
        "PVR Cinemas Movie", "INOX Movies Ticket", "Spotify Music",
        "Wynk Music Subscription", "PlayStation Store Game",
        "Steam Games Store", "Concert Ticket Booking"
    ],

    "Savings": [
        "Zerodha Mutual Fund", "Groww Investment", "Upstox Trading",
        "SIP Mutual Fund Payment", "SBI Fixed Deposit",
        "HDFC Recurring Deposit", "PPF Account Deposit",
        "NPS Contribution", "Zerodha Demat Account",
        "Zerodha Stocks Purchase"
    ],

    "Education": [
        "Byju's Learning App", "Unacademy Course", "Udemy Course",
        "Coursera Course", "Vedantu Tuition", "upGrad Course",
        "Manipal University", "Amity University", "Delhi University",
        "Anna University", "St. Xavier's College", "DPS School",
        "Kendriya Vidyalaya School", "Aakash Institute Coaching",
        "FIITJEE Coaching Institute", "Allen Career Institute",
        "Ryan International School", "National Public School",
        "IIT Coaching Center", "Cambridge School",
        "Podar International School"
    ],

    "Others": [
        "Google Pay Cashback", "PhonePe Reward", "Amazon Refund",
        "Flipkart Refund", "Self Transfer", "NEFT Fund Transfer",
        "IMPS Money Transfer", "RTGS Transfer", "Payment Reversal",
        "Chargeback Credit", "Rahul Sharma", "Priya Verma", "Suresh Kumar"
    ]

}


BANKS = [
    "SBI", "HDFC Bank", "ICICI Bank", "IndusInd Bank", "YES Bank",
    "Kotak", "PNB", "Axis Bank", "IDFC FIRST Bank", "AU Bank",
    "Bank of Baroda"
]

TEMPLATES = [
    "{bank}: Rs.{amount} debited from A/c XX{acct} on {date} to "
    "{merchant}",

    "{bank}: Rs.{amount} debited from A/c XX{acct} for {merchant} "
    "on {date}",

    "{bank} Card XX{acct}: Rs.{amount} spent at {merchant} on {date}",

    "Paid to {merchant}",

    "UPI: Rs.{amount} paid to {merchant} on {date}",

    "{bank}: Rs.{amount} credited to A/c XX{acct} from {merchant} "
    "on {date}"
]


def random_amount():
    return round(random.uniform(50, 150000), 2)


def random_date():
    day = random.randint(1, 28)
    month = random.randint(1, 12)
    year = random.randint(23, 26)
    return f"{day:02d}-{month:02d}-{year:02d}"


def random_account():
    return random.randint(1000, 9999)


def build_examples(merchant_pool, count):

    rows = []

    for _ in range(count):

        template = random.choice(TEMPLATES)
        merchant = random.choice(merchant_pool)

        text = template.format(
            bank=random.choice(BANKS),
            amount=random_amount(),
            acct=random_account(),
            date=random_date(),
            merchant=merchant
        )

        rows.append(text)

    return rows


def main():

    texts = []
    labels = []

    for category, merchants in CATEGORY_MERCHANTS.items():

        examples = build_examples(merchants, count=400)

        texts.extend(examples)
        labels.extend([category] * len(examples))

    cleaned = [clean_transaction(t) for t in texts]

    X_train, X_test, y_train, y_test = train_test_split(
        cleaned, labels, test_size=0.2, random_state=42, stratify=labels
    )

    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        min_df=1,
        sublinear_tf=True
    )

    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_test_tfidf = vectorizer.transform(X_test)

    model = LogisticRegression(max_iter=1000, class_weight="balanced")
    model.fit(X_train_tfidf, y_train)

    predictions = model.predict(X_test_tfidf)

    print("Accuracy:", accuracy_score(y_test, predictions))
    print(classification_report(y_test, predictions))

    joblib.dump(model, "finsight_category_model.pkl")
    joblib.dump(vectorizer, "finsight_category_vectorizer.pkl")

    print(
        "Saved finsight_category_model.pkl and "
        "finsight_category_vectorizer.pkl"
    )


if __name__ == "__main__":
    main()
