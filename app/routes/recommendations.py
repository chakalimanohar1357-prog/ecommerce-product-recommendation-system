from flask import Blueprint, render_template, session, redirect
import pandas as pd
import os

from recommendation_engines.hybrid_model import (
    recommend_similar_products,
    recommend_accessories,
    recommend_same_price,
    recommend_for_user
)

rec_bp = Blueprint('recommendations', __name__)

# Load products
base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, "..", "..", "data")
products = pd.read_csv(os.path.join(data_dir, "products.csv"))


# ==============================
# RECOMMEND PAGE
# ==============================
@rec_bp.route("/recommend")
def recommend():

    if "user" not in session:
        return redirect("/")

    username = session["user"]

    # get user recommendations
    user_recs = recommend_for_user(username)

    # if no recommendations → show random products
    if user_recs.empty:
        user_recs = products.sample(10)

    # choose first product to show details
    product = user_recs.iloc[0]

    similar = recommend_similar_products(product["product_id"])
    accessories = recommend_accessories(product["product_id"])
    same_price = recommend_same_price(product["product_id"])

    return render_template(
        "recommend.html",
        product=product,
        similar=similar.to_dict("records"),
        accessories=accessories.to_dict("records"),
        same_price=same_price.to_dict("records"),
        username=username
    )


# ==============================
# PRODUCT BASED RECOMMENDATION
# ==============================
@rec_bp.route("/recommend/<int:product_id>")
def recommend_for_product(product_id):

    if "user" not in session:
        return redirect("/")

    username = session["user"]

    product = products[products["product_id"] == product_id].iloc[0]

    similar = recommend_similar_products(product_id)
    accessories = recommend_accessories(product_id)
    same_price = recommend_same_price(product_id)

    return render_template(
        "recommend.html",
        product=product,
        similar=similar.to_dict("records"),
        accessories=accessories.to_dict("records"),
        same_price=same_price.to_dict("records"),
        username=username
    )