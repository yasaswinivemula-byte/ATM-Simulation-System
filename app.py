
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "ATM_SIMULATION_DEMO_SECRET_KEY"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "atm_system.db")


# DATABASE CONNECTION
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# CREATE DATABASE
def initialize_database():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            account_no TEXT PRIMARY KEY,
            pin_hash TEXT NOT NULL,
            balance INTEGER NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_no TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    account = conn.execute(
        "SELECT account_no FROM accounts WHERE account_no = ?",
        ("123456",)
    ).fetchone()

    if account is None:
        conn.execute("""
            INSERT INTO accounts
            (account_no, pin_hash, balance)
            VALUES (?, ?, ?)
        """, (
            "123456",
            generate_password_hash("1234"),
            10000
        ))

    conn.commit()
    conn.close()


# LOGIN PROTECTION
def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "account_no" not in session:
            return redirect(url_for("login"))
        return function(*args, **kwargs)
    return wrapper


# LOGIN
@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        account_no = request.form.get("account_no", "").strip()
        pin = request.form.get("pin", "")

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM accounts WHERE account_no = ?",
            (account_no,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["pin_hash"], pin):
            session.clear()
            session["account_no"] = account_no
            return redirect(url_for("dashboard"))

        flash("Invalid account number or PIN!")

    return render_template("login.html")


# DASHBOARD
@app.route("/dashboard")
@login_required
def dashboard():

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM accounts WHERE account_no = ?",
        (session["account_no"],)
    ).fetchone()

    conn.close()

    return render_template("dashboard.html", user=user)


# BALANCE
@app.route("/balance")
@login_required
def balance():

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM accounts WHERE account_no = ?",
        (session["account_no"],)
    ).fetchone()

    conn.close()

    return render_template("balance.html", user=user)


# DEPOSIT
@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():

    if request.method == "POST":
        try:
            amount = int(request.form.get("amount", "0"))

            if amount <= 0:
                flash("Enter a valid amount!")
                return redirect(url_for("deposit"))

            conn = get_db()

            conn.execute(
                "UPDATE accounts SET balance = balance + ? WHERE account_no = ?",
                (amount, session["account_no"])
            )

            conn.execute("""
                INSERT INTO transactions
                (account_no, transaction_type, amount)
                VALUES (?, ?, ?)
            """, (session["account_no"], "Deposit", amount))

            conn.commit()
            conn.close()

            flash(f"₹{amount} deposited successfully!")
            return redirect(url_for("dashboard"))

        except ValueError:
            flash("Please enter a valid whole number!")

    return render_template("deposit.html")


# WITHDRAW
@app.route("/withdraw", methods=["GET", "POST"])
@login_required
def withdraw():

    if request.method == "POST":
        try:
            amount = int(request.form.get("amount", "0"))

            if amount <= 0:
                flash("Enter a valid amount!")
                return redirect(url_for("withdraw"))

            conn = get_db()

            cursor = conn.execute("""
                UPDATE accounts
                SET balance = balance - ?
                WHERE account_no = ? AND balance >= ?
            """, (amount, session["account_no"], amount))

            if cursor.rowcount == 0:
                conn.rollback()
                flash("Insufficient balance!")
            else:
                conn.execute("""
                    INSERT INTO transactions
                    (account_no, transaction_type, amount)
                    VALUES (?, ?, ?)
                """, (session["account_no"], "Withdrawal", amount))

                conn.commit()
                flash(f"₹{amount} withdrawn successfully!")

            conn.close()
            return redirect(url_for("dashboard"))

        except ValueError:
            flash("Please enter a valid whole number!")

    return render_template("withdraw.html")


# MINI STATEMENT
@app.route("/statement")
@login_required
def statement():

    conn = get_db()

    transactions = conn.execute("""
        SELECT * FROM transactions
        WHERE account_no = ?
        ORDER BY id DESC
    """, (session["account_no"],)).fetchall()

    conn.close()

    return render_template(
        "statement.html",
        transactions=transactions
    )


# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out successfully!")
    return redirect(url_for("login"))


# START APPLICATION
if __name__ == "__main__":
    initialize_database()
    app.run(host="127.0.0.1", port=8000, debug=True)
