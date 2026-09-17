import os

from datetime import timedelta

import bcrypt

from dotenv import load_dotenv

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    send_from_directory,
    session,
    abort
)

from flask_cors import CORS

from werkzeug.utils import secure_filename

from database.database import (
    save_statement,
    get_user_statements,
    find_user_by_email,
    create_user,
    update_transaction_category,
    save_merchant_category
)
from services.pdf_service import extract_text_from_pdf
from services.ocr_service import extract_text_from_image
from services.transaction_extractor import extract_transactions
from services.screenshot_extractor import extract_transaction_from_screenshot
from services.category_service import (
    CATEGORIES,
    apply_categories,
    merchant_identity_key,
    is_person_like
)

load_dotenv()


# --------------------------------
# APP CONFIGURATION
# --------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# FinSight/Transactions/Transactions -> FinSight
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(BASE_DIR)
)

LOGIN_FRONTEND_DIR = os.path.join(
    PROJECT_ROOT, "Login", "frontend"
)

DASHBOARD_DIR = os.path.join(
    PROJECT_ROOT, "Dashboard"
)

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates")
)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "transaction_upload_secret"
)

# Sessions are how the server knows who is logged in - the signed
# cookie is set on login and read back on every request, so a user
# can never impersonate someone else just by editing browser storage.
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

# Kept for local tools/tests that call the API from a different origin;
# the app itself now serves the frontend and API from the same port.
CORS(app, resources={r"/api/*": {"origins": "*"}})


# --------------------------------
# UPLOAD CONFIGURATION
# --------------------------------

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

# PDFs go through pdf_service (text layer, many transactions per file);
# images go through ocr_service (OCR, one transaction - a payment
# screenshot from an app like Google Pay, PhonePe or Paytm).
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}
ALLOWED_EXTENSIONS = {"pdf"} | IMAGE_EXTENSIONS

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# Create uploads folder if it does not exist
os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)


# --------------------------------
# HELPER FUNCTION
# --------------------------------

def file_extension(filename):

    if "." not in filename:
        return ""

    return filename.rsplit(".", 1)[1].lower()


def allowed_file(filename):

    return file_extension(filename) in ALLOWED_EXTENSIONS


# --------------------------------
# SHARED UPLOAD PROCESSING
# --------------------------------

def process_uploaded_file(file, user_id="temporary_user_123"):
    """
    Saves the uploaded file, extracts its transaction(s) and stores
    them in MongoDB under the given user. Returns (filename, transactions).

    A PDF is treated as a bank statement (many transactions); an image
    is treated as a single payment screenshot (one transaction) and
    goes through OCR instead of the PDF text layer.
    """

    filename = secure_filename(
        file.filename
    )

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    file.save(
        filepath
    )

    if file_extension(filename) in IMAGE_EXTENSIONS:

        extracted_text = extract_text_from_image(
            filepath
        )

        transactions = extract_transaction_from_screenshot(
            extracted_text
        )

    else:

        extracted_text = extract_text_from_pdf(
            filepath
        )

        transactions = extract_transactions(
            extracted_text
        )

    transactions = apply_categories(
        transactions,
        user_id
    )

    save_statement(
        filename,
        transactions,
        user_id
    )

    return filename, transactions


# --------------------------------
# HOME (serves the Login page)
# --------------------------------

@app.route("/")
def home():

    if "user_id" in session:

        return redirect("/dashboard.html")

    return send_from_directory(
        LOGIN_FRONTEND_DIR,
        "index.html"
    )


# --------------------------------
# FRONTEND STATIC FILES
# (Login/frontend and Dashboard share this one flat namespace;
# their filenames don't collide)
# --------------------------------

@app.route("/<path:filename>")
def frontend_assets(filename):

    login_path = os.path.join(LOGIN_FRONTEND_DIR, filename)

    if os.path.isfile(login_path):
        return send_from_directory(LOGIN_FRONTEND_DIR, filename)


    dashboard_path = os.path.join(DASHBOARD_DIR, filename)

    if os.path.isfile(dashboard_path):
        return send_from_directory(DASHBOARD_DIR, filename)


    abort(404)


# --------------------------------
# UPLOAD BANK STATEMENT
# --------------------------------

@app.route(
    "/upload",
    methods=["GET", "POST"]
)
def upload():

    # ----------------------------
    # DISPLAY UPLOAD PAGE
    # ----------------------------

    if request.method == "GET":

        return render_template(
            "upload.html"
        )


    # ----------------------------
    # CHECK IF FILE EXISTS
    # ----------------------------

    if "file" not in request.files:

        flash(
            "No file selected."
        )

        return redirect(
            request.url
        )


    file = request.files["file"]


    # ----------------------------
    # CHECK EMPTY FILENAME
    # ----------------------------

    if file.filename == "":

        flash(
            "No file selected."
        )

        return redirect(
            request.url
        )


    # ----------------------------
    # VALIDATE FILE TYPE
    # ----------------------------

    if not allowed_file(
        file.filename
    ):

        flash(
            "Only PDF, PNG or JPG files are allowed."
        )

        return redirect(
            request.url
        )


    # ----------------------------
    # PROCESS PDF
    # ----------------------------

    filename, transactions = process_uploaded_file(file)


    # ----------------------------
    # DISPLAY TRANSACTIONS
    # ----------------------------

    return render_template(
        "transactions.html",
        filename=filename,
        transactions=transactions
    )


# --------------------------------
# JSON API - REGISTER
# --------------------------------

@app.route(
    "/api/register",
    methods=["POST"]
)
def api_register():

    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not name or not email or not password:

        return jsonify({
            "message": "Please fill all fields"
        }), 400


    if find_user_by_email(email):

        return jsonify({
            "message": "User already exists"
        }), 400


    hashed_password = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    create_user(name, email, hashed_password)

    return jsonify({
        "message": "Registration successful"
    }), 201


# --------------------------------
# JSON API - LOGIN
# --------------------------------

@app.route(
    "/api/login",
    methods=["POST"]
)
def api_login():

    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not email or not password:

        return jsonify({
            "message": "Please enter email and password"
        }), 400


    user = find_user_by_email(email)

    if not user:

        return jsonify({
            "message": "Invalid email or password"
        }), 401


    password_match = bcrypt.checkpw(
        password.encode("utf-8"),
        user["password"].encode("utf-8")
    )

    if not password_match:

        return jsonify({
            "message": "Invalid email or password"
        }), 401


    # Establish a signed session so future requests know who this is
    # without the client having to (or being able to) claim an identity.
    session.clear()
    session.permanent = True
    session["user_id"] = str(user["_id"])
    session["user_name"] = user["name"]
    session["user_email"] = user["email"]

    return jsonify({
        "message": "Login successful",
        "user": {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"]
        }
    })


# --------------------------------
# JSON API - LOGOUT
# --------------------------------

@app.route(
    "/api/logout",
    methods=["POST"]
)
def api_logout():

    session.clear()

    return jsonify({
        "message": "Logged out"
    })


# --------------------------------
# JSON API - CURRENT USER (used by the Dashboard to check login state)
# --------------------------------

@app.route(
    "/api/me",
    methods=["GET"]
)
def api_me():

    if "user_id" not in session:

        return jsonify({
            "message": "Not logged in"
        }), 401

    return jsonify({
        "user": {
            "id": session["user_id"],
            "name": session.get("user_name"),
            "email": session.get("user_email")
        }
    })


# --------------------------------
# JSON API - UPLOAD (used by the Dashboard)
# --------------------------------

@app.route(
    "/api/upload",
    methods=["POST"]
)
def api_upload():

    user_id = session.get("user_id")

    if not user_id:

        return jsonify({
            "success": False,
            "message": "You must be logged in to upload a document."
        }), 401


    if "file" not in request.files:

        return jsonify({
            "success": False,
            "message": "No file selected."
        }), 400


    file = request.files["file"]


    if file.filename == "":

        return jsonify({
            "success": False,
            "message": "No file selected."
        }), 400


    if not allowed_file(file.filename):

        return jsonify({
            "success": False,
            "message": "Only PDF, PNG or JPG files are allowed."
        }), 400


    try:

        filename, transactions = process_uploaded_file(file, user_id)

    except Exception as error:

        return jsonify({
            "success": False,
            "message": f"Failed to process the document: {error}"
        }), 500


    return jsonify({
        "success": True,
        "filename": filename,
        "transactions": transactions
    })


# --------------------------------
# JSON API - LIST TRANSACTIONS (used by the Dashboard)
# --------------------------------

@app.route(
    "/api/transactions",
    methods=["GET"]
)
def api_transactions():

    user_id = session.get("user_id")

    if not user_id:

        return jsonify({
            "success": False,
            "message": "You must be logged in to view transactions."
        }), 401


    statements = get_user_statements(user_id)

    transactions = []

    for statement in statements:

        for transaction in statement.get("transactions", []):

            transactions.append(transaction)

    return jsonify({
        "success": True,
        "transactions": transactions
    })


# --------------------------------
# JSON API - LIST CATEGORIES
# --------------------------------

@app.route(
    "/api/categories",
    methods=["GET"]
)
def api_categories():

    return jsonify({
        "categories": CATEGORIES
    })


# --------------------------------
# JSON API - UPDATE A TRANSACTION'S CATEGORY
# (also remembers the choice for this merchant going forward)
# --------------------------------

@app.route(
    "/api/transactions/<transaction_id>/category",
    methods=["POST"]
)
def api_update_transaction_category(transaction_id):

    user_id = session.get("user_id")

    if not user_id:

        return jsonify({
            "success": False,
            "message": "You must be logged in."
        }), 401


    data = request.get_json(silent=True) or {}

    category = data.get("category")

    if category not in CATEGORIES:

        return jsonify({
            "success": False,
            "message": "Invalid category."
        }), 400


    updated_statement = update_transaction_category(
        user_id,
        transaction_id,
        category
    )

    if not updated_statement:

        return jsonify({
            "success": False,
            "message": "Transaction not found."
        }), 404


    updated_transaction = next(
        (
            transaction
            for transaction in updated_statement.get("transactions", [])
            if transaction.get("id") == transaction_id
        ),
        None
    )

    merchant = (
        updated_transaction.get("merchant") if updated_transaction else ""
    )

    merchant_key = merchant_identity_key(merchant)

    is_person = is_person_like(merchant)

    # Once the user has answered for this merchant/person, remember it
    # so we never ask again for it.
    if merchant_key:

        save_merchant_category(
            user_id,
            merchant_key,
            category
        )


    return jsonify({
        "success": True,
        "category": category,
        "is_person": is_person
    })


# --------------------------------
# RUN APPLICATION
# --------------------------------

if __name__ == "__main__":

    app.run(
        debug=True,
        use_reloader=False
    )