
import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, session, redirect

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "atm_project_secret_key")

# Keep the database in the project folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "atm.db")


def connect_db():
    return sqlite3.connect(DATABASE)


# Create database tables automatically when the app starts
def create_database():
    con = connect_db()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            account_no TEXT PRIMARY KEY,
            pin TEXT NOT NULL,
            balance REAL NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_no TEXT,
            type TEXT,
            amount REAL
        )
    """)

    cur.execute("""
        INSERT OR IGNORE INTO accounts
        (account_no, pin, balance)
        VALUES ('1234567890', '1234', 10000)
    """)

    con.commit()
    con.close()


# IMPORTANT: Run database setup when Render imports this file
create_database()


def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "account_no" not in session:
            return redirect("/")
        return function(*args, **kwargs)
    return wrapper


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        account_no = request.form.get("account_no")
        pin = request.form.get("pin")

        con = connect_db()
        cur = con.cursor()

        cur.execute(
            "SELECT * FROM accounts WHERE account_no=? AND pin=?",
            (account_no, pin)
        )

        account = cur.fetchone()
        con.close()

        if account:
            session["account_no"] = account_no
            return redirect("/dashboard")

        return """
        <h1>Invalid Account Number or PIN!</h1>
        <a href="/">Try Again</a>
        """

    if "account_no" in session:
        return redirect("/dashboard")

    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/balance")
@login_required
def balance():
    con = connect_db()
    cur = con.cursor()

    cur.execute(
        "SELECT balance FROM accounts WHERE account_no=?",
        (session["account_no"],)
    )

    balance_amount = cur.fetchone()[0]
    con.close()

    return render_template("balance.html", balance=balance_amount)


@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    message = ""
    account_no = session["account_no"]

    con = connect_db()
    cur = con.cursor()

    if request.method == "POST":
        try:
            amount = float(request.form.get("amount", 0))

            if amount <= 0:
                message = "Please enter a valid amount."
            else:
                cur.execute(
                    "UPDATE accounts SET balance = balance + ? WHERE account_no=?",
                    (amount, account_no)
                )

                cur.execute("""
                    INSERT INTO transactions (account_no, type, amount)
                    VALUES (?, ?, ?)
                """, (account_no, "Deposit", amount))

                con.commit()
                message = "Money Deposited Successfully!"

        except ValueError:
            message = "Please enter a valid number."

    cur.execute(
        "SELECT balance FROM accounts WHERE account_no=?",
        (account_no,)
    )
    balance_amount = cur.fetchone()[0]
    con.close()

    return render_template(
        "deposit.html",
        balance=balance_amount,
        message=message
    )


@app.route("/withdraw", methods=["GET", "POST"])
@login_required
def withdraw():
    message = ""
    account_no = session["account_no"]

    con = connect_db()
    cur = con.cursor()

    if request.method == "POST":
        try:
            amount = float(request.form.get("amount", 0))

            cur.execute(
                "SELECT balance FROM accounts WHERE account_no=?",
                (account_no,)
            )
            balance_amount = cur.fetchone()[0]

            if amount <= 0:
                message = "Please enter a valid amount."
            elif amount > balance_amount:
                message = "Insufficient Balance!"
            else:
                cur.execute(
                    "UPDATE accounts SET balance = balance - ? WHERE account_no=?",
                    (amount, account_no)
                )

                cur.execute("""
                    INSERT INTO transactions (account_no, type, amount)
                    VALUES (?, ?, ?)
                """, (account_no, "Withdrawal", amount))

                con.commit()
                message = "Money Withdrawn Successfully!"

        except ValueError:
            message = "Please enter a valid number."

    cur.execute(
        "SELECT balance FROM accounts WHERE account_no=?",
        (account_no,)
    )
    balance_amount = cur.fetchone()[0]
    con.close()

    return render_template(
        "withdraw.html",
        balance=balance_amount,
        message=message
    )


@app.route("/statement")
@login_required
def statement():
    account_no = session["account_no"]

    con = connect_db()
    cur = con.cursor()

    cur.execute(
        "SELECT balance FROM accounts WHERE account_no=?",
        (account_no,)
    )
    balance_amount = cur.fetchone()[0]

    cur.execute("""
        SELECT type, amount FROM transactions
        WHERE account_no=?
        ORDER BY id DESC
    """, (account_no,))

    rows = cur.fetchall()
    con.close()

    transactions = [
        {"type": row[0], "amount": row[1]}
        for row in rows
    ]

    return render_template(
        "statement.html",
        balance=balance_amount,
        transactions=transactions
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
