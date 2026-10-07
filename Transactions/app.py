import os

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify
)

from flask_cors import CORS

from werkzeug.utils import secure_filename

from database.database import save_statement
from services.pdf_service import extract_text_from_pdf
from services.transaction_extractor import extract_transactions


# --------------------------------
# APP CONFIGURATION
# --------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates")
)

app.secret_key = "transaction_upload_secret"

# Allow the dashboard (served from a different origin, e.g. a
# file:// page or a different port) to call this API with fetch()
CORS(app)


# --------------------------------
# UPLOAD CONFIGURATION
# --------------------------------

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

ALLOWED_EXTENSIONS = {"pdf"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# Create uploads folder if it does not exist
os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)


# --------------------------------
# HELPER FUNCTION
# --------------------------------

def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(
            ".",
            1
        )[1].lower()
        in ALLOWED_EXTENSIONS
    )


# --------------------------------
# HOME
# --------------------------------

@app.route("/")
def home():

    return redirect(
        url_for("upload")
    )


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
    # VALIDATE PDF
    # ----------------------------

    if not allowed_file(
        file.filename
    ):

        flash(
            "Only PDF files are allowed."
        )

        return redirect(
            request.url
        )


    # ----------------------------
    # SECURE FILE NAME
    # ----------------------------

    filename = secure_filename(
        file.filename
    )


    # ----------------------------
    # CREATE FILE PATH
    # ----------------------------

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )


    # ----------------------------
    # SAVE PDF
    # ----------------------------

    file.save(
        filepath
    )


    # ----------------------------
    # EXTRACT TEXT FROM PDF
    # ----------------------------

    extracted_text = extract_text_from_pdf(
        filepath
    )


    # ----------------------------
    # EXTRACT TRANSACTIONS
    # ----------------------------

    transactions = extract_transactions(
        extracted_text
    )


    # ----------------------------
    # SAVE TRANSACTIONS TO MONGODB
    # ----------------------------

    save_statement(
        filename,
        transactions
    )


    # ----------------------------
    # DISPLAY TRANSACTIONS
    # ----------------------------

    return render_template(
        "transactions.html",
        filename=filename,
        transactions=transactions
    )


# --------------------------------
# UPLOAD BANK STATEMENT (JSON API — used by the dashboard)
# --------------------------------

@app.route(
    "/api/upload",
    methods=["POST"]
)
def api_upload():

    # ----------------------------
    # CHECK IF FILE EXISTS
    # ----------------------------

    if "file" not in request.files:

        return jsonify(
            {"error": "No file selected."}
        ), 400


    file = request.files["file"]


    # ----------------------------
    # CHECK EMPTY FILENAME
    # ----------------------------

    if file.filename == "":

        return jsonify(
            {"error": "No file selected."}
        ), 400


    # ----------------------------
    # VALIDATE PDF
    # ----------------------------

    if not allowed_file(
        file.filename
    ):

        return jsonify(
            {"error": "Only PDF files are allowed."}
        ), 400


    # ----------------------------
    # SECURE FILE NAME
    # ----------------------------

    filename = secure_filename(
        file.filename
    )


    # ----------------------------
    # CREATE FILE PATH
    # ----------------------------

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )


    # ----------------------------
    # SAVE PDF
    # ----------------------------

    file.save(
        filepath
    )


    # ----------------------------
    # EXTRACT TEXT + TRANSACTIONS
    # ----------------------------

    extracted_text = extract_text_from_pdf(
        filepath
    )

    transactions = extract_transactions(
        extracted_text
    )


    # ----------------------------
    # SAVE TRANSACTIONS TO MONGODB
    # ----------------------------

    save_statement(
        filename,
        transactions
    )


    # ----------------------------
    # RETURN JSON FOR THE DASHBOARD
    # ----------------------------

    return jsonify(
        {
            "filename": filename,
            "transactions": transactions
        }
    )


# --------------------------------
# RUN APPLICATION
# --------------------------------

if __name__ == "__main__":

    app.run(
        debug=True,
        use_reloader=False
    )