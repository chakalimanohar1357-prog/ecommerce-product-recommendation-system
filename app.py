from flask import Flask, render_template, request, redirect, session, flash
import pandas as pd
import sqlite3

# when running this file directly the package-level init_db isn't
# automatically executed, so perform a manual import if possible.  This
# keeps the old single-file version working while still benefiting from
# the improved migration logic in app/models/database.py.
try:
    from app.models.database import init_db
    init_db()
except ImportError:
    # if the app package isn't available (e.g. running tests in
    # isolation) just ignore
    pass

# Import recommendation models
# use package-qualified paths so imports work regardless of current
# working directory or how the app is started
from recommendation_engines.content_based import recommend_similar
from recommendation_engines.ml_model import get_recommendations
from recommendation_engines.hybrid_model import (
    recommend_similar_products,
    recommend_accessories,
    recommend_same_price,
    recommend_for_user
)

app = Flask(__name__)
app.secret_key = "secret123"

# Load products
products = pd.read_csv("products.csv")


# =========================
# DATABASE CONNECTION
# =========================
# We no longer create or migrate the schema here.  Initialization is
# handled by `app/models/database.py` which is invoked when the
# application starts (see `create_app` in `app/__init__.py`).  That
# module also includes a small migration helper that will add missing
# columns such as `interaction_type` or `timestamp` if the database was
# created with an earlier version of the schema.  
#
# If you are running this file directly (`python app.py`) instead of
# using `run.py`, you can delete `database.db` after making schema
# changes so the new schema is built from scratch.

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# REGISTER
# =========================
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor()

        try:

            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password)
            )

            conn.commit()
            conn.close()

            flash("Account created successfully – please log in")
            return redirect("/")  # go to login page instead of auto-login

        except:

            conn.close()
            flash("Username already exists")

    return render_template("register.html")


# =========================
# LOGIN
# =========================
@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )

        user = cursor.fetchone()
        conn.close()

        if user:

            session["user"] = username

            if "cart" not in session:
                session["cart"] = []

            return redirect("/home")

        else:

            flash("Invalid login details")

    return render_template("login.html")


# =========================
# HOME PAGE
# =========================
@app.route("/home")
def home():

    if "user" not in session:
        return redirect("/")

    username = session["user"]

    cart_count = len(session.get("cart", []))

    # Personalized recommendations
    recommended = recommend_for_user(username)

    return render_template(
        "home.html",
        products=products.to_dict("records"),
        recommended=recommended.to_dict("records"),
        username=username,
        cart_count=cart_count,
        product_count=len(products)
    )


# =========================
# VIEW PRODUCT (HYBRID RECOMMENDATION)
# =========================
@app.route("/view/<int:product_id>")
def view_product(product_id):

    if "user" not in session:
        return redirect("/")

    username = session["user"]

    # Save interaction; non‑critical so protect against schema issues
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO interactions (username, product_id) VALUES (?, ?)",
            (username, product_id)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print("warning: unable to save view interaction", e)

    # Get recommendations
    similar = recommend_similar_products(product_id)

    accessories = recommend_accessories(product_id)

    same_price = recommend_same_price(product_id)

    return render_template(
        "recommend.html",
        similar=similar.to_dict("records"),
        accessories=accessories.to_dict("records"),
        same_price=same_price.to_dict("records"),
        username=username
    )


# =========================
# ADD TO CART
# =========================
@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):

    if "user" not in session:
        return redirect("/")

    if "cart" not in session:
        session["cart"] = []

    session["cart"].append(product_id)

    session.modified = True

    # Record interaction
    conn = get_db()
    conn.execute(
        "INSERT INTO interactions (username, product_id, interaction_type) VALUES (?, ?, ?)",
        (session["user"], product_id, "add_to_cart")
    )
    conn.commit()
    conn.close()

    return redirect("/home")


# =========================
# VIEW CART
# =========================
@app.route("/cart")
def view_cart():

    if "user" not in session:
        return redirect("/")

    cart_ids = session.get("cart", [])

    cart_products = products[
        products["product_id"].isin(cart_ids)
    ]

    total = cart_products["price"].sum()

    return render_template(
        "cart.html",
        cart=cart_products.to_dict("records"),
        total=total,
        username=session["user"]
    )


# =========================
# CHECKOUT
# =========================
@app.route("/checkout")
def checkout():

    if "user" not in session:
        return redirect("/")

    cart_ids = session.get("cart", [])

    cart_products = products[
        products["product_id"].isin(cart_ids)
    ]

    total = cart_products["price"].sum()

    return render_template(
        "checkout.html",
        cart=cart_products.to_dict("records"),
        total=total,
        username=session["user"]
    )


# =========================
# PLACE ORDER
# =========================
@app.route("/place_order")
def place_order():

    session["cart"] = []

    return render_template("order_success.html")


@app.route("/recommend/<int:product_id>")
def recommend_for_product(product_id):

    if "user" not in session:
        return redirect("/")

    username = session["user"]

    # Get recommendations for a specific product
    similar = recommend_similar_products(product_id)

    accessories = recommend_accessories(product_id)

    same_price = recommend_same_price(product_id)

    return render_template(
        "recommend.html",
        similar=similar.to_dict("records"),
        accessories=accessories.to_dict("records"),
        same_price=same_price.to_dict("records"),
        username=username
    )


# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    app.run(debug=True)