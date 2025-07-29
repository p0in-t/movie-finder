import psycopg2
import numpy as np
import pandas as pd
import faiss
from sklearn.preprocessing import normalize
import os
from thefuzz import process
import traceback

OVERVIEW_WEIGHT = 1.0
GENRE_WEIGHT = 2.0
KEYWORD_WEIGHT = 3.0
VOTE_WEIGHT = 0.2
ATMOSPHERE_WEIGHT = 2.0
NARRATIVE_WEIGHT = 2.0
THEMES_WEIGHT = 2.0
COMBINED_CLASSIFIED_WEIGHT = 2.5

FAISS_INDEX_PATH = 'assets/movie_similarity_index.bin'
DF_PATH = 'assets/movie_dataframe.pkl'

def get_movie_embeddings_from_db(cursor, movie_id):
    cursor.execute("""
        SELECT 
            id, title, overview, vote_average, vote_average_scaled,
            overview_emb, genres_emb, keywords_emb, 
            atmosphere, narrative, themes,
            atmosphere_emb, narrative_emb, themes_emb, classified_emb_combined
        FROM movie 
        WHERE id = %s AND classified_emb_combined IS NOT NULL
    """, (movie_id,))
    
    result = cursor.fetchone()
    if not result:
        return None
        
    return {
        'id': result[0],
        'title': result[1],
        'overview': result[2],
        'vote_average': result[3],
        'vote_average_scaled': result[4],
        'overview_emb': result[5],
        'genres_emb': result[6],
        'keywords_emb': result[7],
        'atmosphere': result[8],
        'narrative': result[9],
        'themes': result[10],
        'atmosphere_emb': result[11],
        'narrative_emb': result[12],
        'themes_emb': result[13],
        'classified_emb_combined': result[14]
    }

def create_composite_vector(movie_data):
    summary_emb = np.array(movie_data['overview_emb']) if movie_data['overview_emb'] else np.zeros(384)
    genres_emb = np.array(movie_data['genres_emb']) if movie_data['genres_emb'] else np.zeros(384)
    keywords_emb = np.array(movie_data['keywords_emb']) if movie_data['keywords_emb'] else np.zeros(384)
    vote_scaled = np.array([movie_data['vote_average_scaled']])
    atmosphere_emb = np.array(movie_data['atmosphere_emb']) if movie_data['atmosphere_emb'] else np.zeros(384)
    narrative_emb = np.array(movie_data['narrative_emb']) if movie_data['narrative_emb'] else np.zeros(384)
    themes_emb = np.array(movie_data['themes_emb']) if movie_data['themes_emb'] else np.zeros(384)
    combined_emb = np.array(movie_data['classified_emb_combined']) if movie_data['classified_emb_combined'] else np.zeros(384)

    weighted_summary = summary_emb * OVERVIEW_WEIGHT
    weighted_genres = genres_emb * GENRE_WEIGHT
    weighted_keywords = keywords_emb * KEYWORD_WEIGHT
    weighted_vote = vote_scaled * VOTE_WEIGHT
    weighted_atmosphere = atmosphere_emb * ATMOSPHERE_WEIGHT
    weighted_narrative = narrative_emb * NARRATIVE_WEIGHT
    weighted_themes = themes_emb * THEMES_WEIGHT
    weighted_combined = combined_emb * COMBINED_CLASSIFIED_WEIGHT

    composite_vector = np.hstack([
        weighted_summary,
        weighted_genres,
        weighted_keywords,
        weighted_vote,
        weighted_atmosphere,
        weighted_narrative,
        weighted_themes,
        # weighted_combined
    ])

    composite_vector = normalize(composite_vector.reshape(1, -1), norm='l2', axis=1).astype('float32')
    return composite_vector

def find_similar_movies(query_movie_id, k=10, faiss_index=None, movie_df=None):
    if faiss_index is None or movie_df is None:
        raise ValueError("FAISS index and movie DataFrame must be provided.")

    query_movie_data = movie_df[movie_df['id'] == query_movie_id]
    
    if query_movie_data.empty:
        return pd.DataFrame(), f"Movie with ID {query_movie_id} not found"

    query_movie = query_movie_data.iloc[0]
    original_query_movie_df_index = query_movie_data.index[0]

    movie_dict = query_movie.to_dict()
    query_composite_vector = create_composite_vector(movie_dict)

    similarities, indices = faiss_index.search(query_composite_vector, k + 1)

    similar_movie_indices = []
    similar_movie_similarities = []

    for i, idx in enumerate(indices[0]):
        if idx != original_query_movie_df_index and len(similar_movie_indices) < k:
            similar_movie_indices.append(idx)
            similar_movie_similarities.append(similarities[0][i])

    if not similar_movie_indices:
        return pd.DataFrame(), "No similar movies found"

    similar_movies_df = movie_df.iloc[similar_movie_indices].copy()
    similar_movies_df['similarity_score'] = similar_movie_similarities

    similar_movies_df = similar_movies_df.sort_values(by='similarity_score', ascending=False).reset_index(drop=True)

    result_columns = ['id', 'title', 'overview', 'vote_average', 'atmosphere', 'narrative', 'themes', 'similarity_score']
    return similar_movies_df[result_columns], None

def find_movies_by_id(query_movie_id, movie_df):
    if movie_df is None:
        raise ValueError("FAISS index and movie DataFrame must be provided.")

    query_movie_data = movie_df[movie_df['id'] == query_movie_id]

    if query_movie_data.empty:
        return pd.DataFrame(), f"Movie with ID {query_movie_id} not found"

    return query_movie_data, None

def find_id_by_title(query_title, movie_df, score_cutoff=75):
    if movie_df is None:
        raise ValueError("Movie DataFrame must be provided.")
        
    if not query_title or not isinstance(query_title, str):
        return None, "A valid query title must be provided."

    titles = movie_df['title'].tolist()

    best_match = process.extractOne(query_title, titles)
    
    if best_match is None:
        return None, "No titles available for matching."

    matched_title, score = best_match

    if score >= score_cutoff:
        movie_index = movie_df[movie_df['title'] == matched_title].index[0]
        
        movie_id = movie_df.at[movie_index, 'id']
        
        return int(movie_id), None
    else:
        error_message = f"No close match found for '{query_title}'. Best match was '{matched_title}' with a score of {score}, which is below the cutoff of {score_cutoff}."
        return None, error_message

def find_movies_by_description(query_description, k=5, model=None, movie_df=None):
    if model is None or movie_df is None:
        return pd.DataFrame(), "A SentenceTransformer model and a movie DataFrame must be provided."
    if 'overview_emb' not in movie_df.columns:
        return pd.DataFrame(), "DataFrame is missing the required 'overview_emb' column."
    if not query_description or not isinstance(query_description, str):
        return pd.DataFrame(), "A valid string for query_description must be provided."

    try:
        overview_embeddings = np.vstack(movie_df['overview_emb'].dropna().values)

        query_embedding = model.encode([query_description])

        cosine_scores = np.dot(overview_embeddings, query_embedding.T).flatten()

        top_k_indices = np.argpartition(cosine_scores, -k)[-k:]

        similar_movies_df = movie_df.iloc[top_k_indices].copy()
        similar_movies_df['similarity_score'] = cosine_scores[top_k_indices]

        similar_movies_df = similar_movies_df.sort_values(by='similarity_score', ascending=False).reset_index(drop=True)

        result_columns = ['id', 'title', 'overview', 'vote_average', 'similarity_score']
        return_columns = [col for col in result_columns if col in similar_movies_df.columns]
        
        return similar_movies_df[return_columns], None

    except ValueError as ve:
        return pd.DataFrame(), f"Error processing embeddings. Check if all 'overview_emb' entries have the same dimension. Details: {ve}"
    except Exception as e:
        return pd.DataFrame(), f"An unexpected error occurred in find_movies_by_description: {e}"

def load_all_movies_and_build_index(connect, cursor):
    
    try:
        cursor.execute("""
            SELECT 
                id, title, overview, vote_average, vote_average_scaled,
                overview_emb, genres_emb, keywords_emb, 
                atmosphere, narrative, themes,
                atmosphere_emb, narrative_emb, themes_emb, classified_emb_combined
            FROM movie 
            WHERE classified_emb_combined IS NOT NULL
            ORDER BY id
        """)
        
        rows = cursor.fetchall()
        columns = ['id', 'title', 'overview', 'vote_average', 'vote_average_scaled',
                  'overview_emb', 'genres_emb', 'keywords_emb', 
                  'atmosphere', 'narrative', 'themes',
                  'atmosphere_emb', 'narrative_emb', 'themes_emb', 'classified_emb_combined']
        
        df = pd.DataFrame(rows, columns=columns)
        print(f"Loaded {len(df)} movies with embeddings")
        
        composite_vectors = []
        for _, movie in df.iterrows():
            movie_dict = movie.to_dict()
            composite_vector = create_composite_vector(movie_dict)
            composite_vectors.append(composite_vector[0])
        
        composite_vectors = np.array(composite_vectors).astype('float32')
        
        d = composite_vectors.shape[1]
        index = faiss.IndexFlatIP(d)
        index.add(composite_vectors)
        
        print(f"Built FAISS index with {index.ntotal} vectors of dimension {d}")
        
        return df, index
        
    finally:
        cursor.close()
        connect.close()

def build_index():
    movie_df = pd.read_pickle(DF_PATH)
    
    print(f"Loaded {len(movie_df)} movies with embeddings")
        
    composite_vectors = []
    for _, movie in movie_df.iterrows():
        movie_dict = movie.to_dict()
        composite_vector = create_composite_vector(movie_dict)
        composite_vectors.append(composite_vector[0])
    
    composite_vectors = np.array(composite_vectors).astype('float32')
    
    d = composite_vectors.shape[1]
    index = faiss.IndexFlatIP(d)
    index.add(composite_vectors)
    
    print(f"Built FAISS index with {index.ntotal} vectors of dimension {d}")
    
    return movie_df, index

def load_or_build_index(connect, cursor):
    print("v1:Current working directory:", os.getcwd())
    print("faiss index path exists: ", os.path.exists(FAISS_INDEX_PATH))

    if os.path.exists(FAISS_INDEX_PATH) and os.path.exists(DF_PATH):
        print("Loading existing FAISS index and dataframe...")
        try:
            movie_df = pd.read_pickle(DF_PATH)
            faiss_index = faiss.read_index(FAISS_INDEX_PATH)
            print(f"Loaded existing index with {faiss_index.ntotal} movies")
            return movie_df, faiss_index
        except Exception as e:
            print(f"Error loading existing files: {e}")
            traceback.print_exc()  # <== this prints the full stack trace of the error
            print("Rebuilding index...")
    
    print("Building new FAISS index and dataframe...")
    movie_df, faiss_index = build_index()
    
    print("Saving index and dataframe for future use...")
    os.makedirs('assets', exist_ok=True)
    faiss.write_index(faiss_index, FAISS_INDEX_PATH)
    movie_df.to_pickle(DF_PATH)
    print("Assets saved successfully!")
    
    return movie_df, faiss_index

def test():
    try:
        print("Loading movies and building FAISS index...")
        movie_df, faiss_index = load_or_build_index()

        while True:
            query_movie_id = int(input("\nEnter movie id: "))

            print(f"\nFinding movies similar to movie ID: {query_movie_id}")
            
            results, error = find_similar_movies(
                query_movie_id=query_movie_id,
                k=10,
                faiss_index=faiss_index,
                movie_df=movie_df
            )
            
            if error:
                print(f"Error: {error}")
            else:
                print("\nSimilar movies found:")
                print(results[['title', 'atmosphere', 'themes', 'narrative', 'similarity_score']].to_string())
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()