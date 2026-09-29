import pandas as pd
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Load products safely
base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, "..", "data")
file_path = os.path.join(data_dir, "products.csv")

products = pd.read_csv(file_path)

# Create feature column
products["features"] = products["name"] + " " + products["category"]

# Convert text to vectors
vectorizer = TfidfVectorizer()

feature_matrix = vectorizer.fit_transform(products["features"])

# Compute similarity matrix
similarity = cosine_similarity(feature_matrix)


# THIS IS THE FUNCTION APP.PY NEEDS
def recommend_similar(product_id):

    # Find index
    index = products[products["product_id"] == product_id].index

    if len(index) == 0:
        return pd.DataFrame()

    index = index[0]

    similarity_scores = list(enumerate(similarity[index]))

    similarity_scores = sorted(
        similarity_scores,
        key=lambda x: x[1],
        reverse=True
    )

    similar_indices = [i[0] for i in similarity_scores[1:6]]

    return products.iloc[similar_indices]