import sqlite3
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

def get_recommendations(username):

    conn = sqlite3.connect("database.db")

    df = pd.read_sql_query(
        "SELECT username, product_id FROM interactions",
        conn
    )

    conn.close()

    if df.empty:
        return []

    # Create user-product matrix
    matrix = pd.crosstab(df['username'], df['product_id'])

    similarity = cosine_similarity(matrix)

    similarity_df = pd.DataFrame(
        similarity,
        index=matrix.index,
        columns=matrix.index
    )

    similar_users = similarity_df[username].sort_values(
        ascending=False
    )

    similar_users = similar_users.index[1:]

    recommended_products = []

    for user in similar_users:

        products = df[df['username'] == user]['product_id'].tolist()

        recommended_products.extend(products)

    return list(set(recommended_products))