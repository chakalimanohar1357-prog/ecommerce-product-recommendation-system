import pandas as pd
import os
import sqlite3
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# =========================
# LOAD PRODUCTS
# =========================

base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, "..", "data")

products_path = os.path.join(data_dir, "products.csv")
products = pd.read_csv(products_path)


# =========================
# CONTENT BASED FEATURES
# =========================

products["features"] = products["name"] + " " + products["category"]

vectorizer = TfidfVectorizer()

feature_matrix = vectorizer.fit_transform(products["features"])

similarity_matrix = cosine_similarity(feature_matrix)


# =========================
# SIMILAR PRODUCTS
# =========================
def recommend_similar_products(product_id):

    index = products[products["product_id"] == product_id].index

    if len(index) == 0:
        return products.sample(5)

    index = index[0]

    similarity_scores = list(enumerate(similarity_matrix[index]))

    similarity_scores = sorted(
        similarity_scores,
        key=lambda x: x[1],
        reverse=True
    )

    original_category = products.iloc[index]["category"]

    similar_indexes = []

    for idx, score in similarity_scores[1:]:

        if products.iloc[idx]["category"] == original_category:
            similar_indexes.append(idx)

        if len(similar_indexes) >= 5:
            break

    if len(similar_indexes) == 0:
        return products.sample(5)

    return products.iloc[similar_indexes]


# =========================
# ACCESSORIES
# =========================
def recommend_accessories(product_id):

    product = products[products["product_id"] == product_id]

    if product.empty:
        return products.sample(5)

    accessories = products[
        products["category"].str.lower() == "accessory"
    ]

    if accessories.empty:
        return products.sample(5)

    return accessories.head(5)


# =========================
# SAME PRICE RANGE
# =========================
def recommend_same_price(product_id):

    product = products[products["product_id"] == product_id]

    if product.empty:
        return products.sample(5)

    price = product.iloc[0]["price"]

    similar_price = products[
        (products["price"] >= price - 10000)
        &
        (products["price"] <= price + 10000)
    ]

    if similar_price.empty:
        return products.sample(5)

    return similar_price.head(5)


# =========================
# USER BASED RECOMMENDATION
# =========================
def recommend_for_user(username):

    db_path = os.path.join(base_dir, "..", "database.db")

    conn = sqlite3.connect(db_path)

    interactions = pd.read_sql_query(
        "SELECT * FROM interactions WHERE username=?",
        conn,
        params=(username,)
    )

    conn.close()

    if interactions.empty:
        return products.sample(5)

    last_product = interactions.iloc[-1]["product_id"]

    return recommend_similar_products(last_product)


# =========================
# COLLABORATIVE FILTERING
# Customers also bought
# =========================
def recommend_collaborative(product_id):

    interactions_path = os.path.join(data_dir, "interactions.csv")

    if not os.path.exists(interactions_path):
        return products.sample(5)

    interactions = pd.read_csv(interactions_path)

    users = interactions[
        interactions["product_id"] == product_id
    ]["username"]

    if users.empty:
        return products.sample(5)

    similar_products = interactions[
        interactions["username"].isin(users)
    ]["product_id"]

    similar_products = similar_products.unique()

    recs = products[
        products["product_id"].isin(similar_products)
        &
        (products["product_id"] != product_id)
    ]

    if recs.empty:
        return products.sample(5)

    return recs.head(5)