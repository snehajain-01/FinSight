# FinSight

## Smart Financial Insights & Management System

FinSight is a web-based financial management application designed to help users organize their financial information and gain meaningful insights from their transactions and financial documents.

The project provides a secure Login/Register system with a backend connected to MongoDB and a dashboard that serves as the central interface for future financial analysis features.

---

## Features

### 🔐 User Authentication
- User registration
- User login
- Password hashing using bcrypt
- MongoDB-based user storage
- Separate frontend and backend

### 📊 Dashboard
The FinSight dashboard provides a centralized interface with sections for:

- Dashboard
- Upload Document
- Transactions
- Insights
- Recommendations

These sections are currently structured for future implementation.

### 📄 Document Processing
The dashboard includes an interface for uploading financial documents. Future versions will process uploaded documents and extract useful financial information.

### 📈 Financial Insights
The Insights section is designed to provide meaningful information based on the user's financial data.

### 💡 Recommendations
The Recommendations section will provide personalized financial suggestions based on spending patterns and financial behavior.

---

## Project Structure

```text
FinSight/
│
├── Login/
│   │
│   ├── frontend/
│   │   ├── index.html
│   │   ├── style.css
│   │   └── script.js
│   │
│   └── backend/
│       ├── models/
│       ├── server.js
│       ├── package.json
│       ├── package-lock.json
│       ├── .env
│       └── .gitignore
│
├── Dashboard/
│   ├── dashboard.html
│   ├── dashboard.css
│   └── dashboard.js
│
└── README.md
