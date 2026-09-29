from flask import Blueprint, render_template, request, redirect, session, flash
from ..models.database import get_db
import sqlite3

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password)).fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect("/home")
        else:
            flash("Invalid credentials")

    return render_template("login.html")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        try:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            flash("Account created successfully – please log in")
            # do not log the user in automatically; send them to login page
            return redirect("/")
        except sqlite3.IntegrityError:
            flash("Username already exists")
        finally:
            conn.close()

    return render_template("register.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")