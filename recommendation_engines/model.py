import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

# Sample user-product interaction matrix
data = {
    'user1': [5, 3, 0, 1, 0],
    'user2': [4, 0, 0, 1, 1],
    'user3': [1, 1, 0, 5, 0],
    'user4': [0, 0, 5, 4, 0],
}

df = pd.DataFrame(data,
index=['Shirt','Shoes','Watch','Mobile','Laptop'])

# Transpose
df = df.T

# Calculate similarity
similarity = cosine_similarity(df)

similarity_df = pd.DataFrame(
similarity,
index=df.index,
columns=df.index
)

def recommend(user):
    scores = similarity_df[user].sort_values(ascending=False)
    return scores.index[1:4]