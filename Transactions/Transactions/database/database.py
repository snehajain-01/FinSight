import os

from dotenv import load_dotenv
from pymongo import MongoClient, ReturnDocument
from datetime import datetime

load_dotenv()


# --------------------------------
# MONGODB CONNECTION
# --------------------------------

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://localhost:27017"
)


client = MongoClient(MONGO_URI)


# Test the connection
try:
    client.admin.command("ping")
    print("Connected to MongoDB successfully!")

except Exception as e:
    print("MongoDB connection failed:")
    print(e)


# --------------------------------
# DATABASE
# --------------------------------

db = client["finsight_db"]


# --------------------------------
# COLLECTIONS
# --------------------------------

statements_collection = db["statements"]

# Merchant name (per user) -> category the user manually picked, so we
# never have to ask again for that merchant.
merchant_categories_collection = db["merchant_categories"]

# Same "users" collection the Login backend (Login/backend) writes to,
# just in the "finsight" database instead of "finsight_db".
users_collection = client["finsight"]["users"]


# --------------------------------
# SAVE BANK STATEMENT
# --------------------------------

def save_statement(
    filename,
    transactions,
    user_id="temporary_user_123"
):

    statement = {
        "user_id": user_id,
        "document_name": filename,
        "uploaded_at": datetime.now(),
        "transactions": transactions
    }

    result = statements_collection.insert_one(
        statement
    )

    return str(result.inserted_id)


# --------------------------------
# GET USER STATEMENTS
# --------------------------------

def get_user_statements(
    user_id="temporary_user_123"
):

    statements = statements_collection.find(
        {
            "user_id": user_id
        }
    )

    return list(statements)


# --------------------------------
# FIND USER BY EMAIL
# --------------------------------

def find_user_by_email(email):

    return users_collection.find_one(
        {
            "email": email
        }
    )


# --------------------------------
# CREATE USER
# --------------------------------

def create_user(name, email, hashed_password):

    user = {
        "name": name,
        "email": email,
        "password": hashed_password,
        "createdAt": datetime.now(),
        "updatedAt": datetime.now()
    }

    result = users_collection.insert_one(user)

    return str(result.inserted_id)


# --------------------------------
# PASSWORD RESET - STORE OTP
# --------------------------------

def set_password_reset_otp(email, otp_hash, expires_at):

    users_collection.update_one(
        {
            "email": email
        },
        {
            "$set": {
                "reset_otp_hash": otp_hash,
                "reset_otp_expires": expires_at,
                "updatedAt": datetime.now()
            }
        }
    )


# --------------------------------
# PASSWORD RESET - UPDATE PASSWORD + CLEAR OTP
# --------------------------------

def reset_user_password(email, hashed_password):

    users_collection.update_one(
        {
            "email": email
        },
        {
            "$set": {
                "password": hashed_password,
                "updatedAt": datetime.now()
            },
            "$unset": {
                "reset_otp_hash": "",
                "reset_otp_expires": ""
            }
        }
    )


# --------------------------------
# GET LEARNED MERCHANT -> CATEGORY MAP (for one user)
# --------------------------------

def get_merchant_categories_map(user_id):

    docs = merchant_categories_collection.find(
        {
            "user_id": user_id
        }
    )

    return {
        doc["merchant_key"]: doc["category"]
        for doc in docs
    }


# --------------------------------
# REMEMBER A MANUALLY CHOSEN CATEGORY FOR A MERCHANT
# --------------------------------

def save_merchant_category(user_id, merchant_key, category):

    merchant_categories_collection.update_one(
        {
            "user_id": user_id,
            "merchant_key": merchant_key
        },
        {
            "$set": {
                "category": category
            }
        },
        upsert=True
    )


# --------------------------------
# UPDATE A SINGLE TRANSACTION'S CATEGORY
# --------------------------------

def update_transaction_category(user_id, transaction_id, category):

    return statements_collection.find_one_and_update(
        {
            "user_id": user_id,
            "transactions.id": transaction_id
        },
        {
            "$set": {
                "transactions.$.category": category,
                "transactions.$.confidence": 1.0,
                "transactions.$.needs_review": False
            }
        },
        return_document=ReturnDocument.AFTER
    )