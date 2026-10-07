import os

from pymongo import MongoClient
from datetime import datetime


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
# COLLECTION
# --------------------------------

statements_collection = db["statements"]


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