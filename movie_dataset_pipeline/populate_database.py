import requests
import json
import os
import time
import psycopg2
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from concurrent.futures import ThreadPoolExecutor
import urllib
import pandas as pd

NCE_PATH = 'nce.pkl'
CE_PATH = 'ce.pkl'

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
HEADERS = {
    'Authorization': f'Bearer {TMDB_API_KEY}',
    'accept': 'application/json'
}
ua = UserAgent()
HEADERS_UA = {'User-Agent': ua.random}

def get_top_rated_movies(page):
    url = f'https://api.themoviedb.org/3/movie/top_rated?language=en-US&page={page}'

    response = requests.get(url, headers=HEADERS)

    if response.ok:
        return response.json().get('results', []), response.json().get('total_pages', -1)
    else:
        print(f"Request failed ({response.status_code}): {response.text}")
        return [], -1

def get_movie_keywords(movie_id):
    url = f'https://api.themoviedb.org/3/movie/{movie_id}/keywords'
    response = requests.get(url, headers=HEADERS)

    if response.ok:
        return response.json().get('keywords', [])
    else:
        print(f"Request failed ({response.status_code}): {response.text}")
        return []
    
def get_movie_genres():
    url = 'https://api.themoviedb.org/3/genre/movie/list?language=en'

    response = requests.get(url, headers=HEADERS)

    if response.ok:
        return response.json().get('genres', [])
    else:
        print(f"Request failed ({response.status_code}): {response.text}")
        return []
    
def get_imdb_id(movie_id):
    url = f'https://api.themoviedb.org/3/movie/{movie_id}/external_ids'

    response = requests.get(url, headers=HEADERS)

    if response.ok:
        return response.json().get('imdb_id', -1)
    else:
        print(f"Request failed ({response.status_code}): {response.text}")
        return -1
    
def get_movie_reviews(movie_id, min_length=500, max_pages=50):
    good_reviews = []
    
    for page in range(1, max_pages + 1):
        url = f'https://api.themoviedb.org/3/movie/{movie_id}/reviews?language=en-US&page={page}'
        response = requests.get(url, headers=HEADERS)

        if not response.ok:
            print(f"Request failed ({response.status_code}): {response.text}")
            break
            
        reviews = response.json().get('results', [])
        
        if not reviews:
            break
            
        for review in reviews:
            content = review.get('content', '')
            if len(content) >= min_length:
                print(f"Found good review for movie id {movie_id} on page {page}")
                good_reviews.append(content)
                if len(good_reviews) >= 3:
                    print(f"Found enough good reviews for movie id {movie_id}")
                    return good_reviews
        
        time.sleep(0.3)
    
    if not good_reviews:
        print(f"Did not find enough good reviews for movie id {movie_id}")
        url = f'https://api.themoviedb.org/3/movie/{movie_id}/reviews?language=en-US&page=1'
        response = requests.get(url, headers=HEADERS)
        
        if response.ok:
            reviews = response.json().get('results', [])
            if reviews:
                return [reviews[0].get('content', '')]
    
    return good_reviews

def get_movie_reviews_imdb(imdb_id, min_length=500, max_length=1500, max_pages=50):
    good_reviews = []
    
    for page in range(1, max_pages + 1):
        url = f'https://www.imdb.com/title/{imdb_id}/reviews?sort=helpfulnessScore&dir=desc&page={page}'
        response = requests.get(url, headers=HEADERS_UA, timeout=10)

        if not response.ok:
            print(f"Request failed for IMDb ID {imdb_id}, page {page} ({response.status_code}): {response.text}")
            break
            
        soup = BeautifulSoup(response.text, 'html.parser')
        section = soup.find('section', class_='ipc-page-section ipc-page-section--base ipc-page-section--sp-pageMargin')
        if not section:
            break
            
        review_articles = section.find_all('article', class_='sc-a77dbebd-1 iJQoqi user-review-item')
        if not review_articles:
            break
            
        for article in review_articles:
            card = article.find('div', class_='ipc-list-card--border-speech ipc-list-card--hasActions ipc-list-card--base ipc-list-card sc-19165bb8-0 dGaXAC')
            if not card:
                continue
                
            content_div = card.find('div', class_='ipc-list-card__content')
            if not content_div:
                continue
                
            overflow_text = content_div.find('div', class_='ipc-overflowText ipc-overflowText--listCard ipc-overflowText--height-long ipc-overflowText--long ipc-overflowText--click ipc-overflowText--base')
            if not overflow_text:
                continue
                
            overflow_children = overflow_text.find('div', class_='ipc-overflowText--children')
            if not overflow_children:
                continue
                
            html_content = overflow_children.find('div', class_='ipc-html-content ipc-html-content--base')
            if not html_content:
                continue
                
            inner_div = html_content.find('div', class_='ipc-html-content-inner-div')
            content = inner_div.text.strip() if inner_div else ''
            if len(content) >= min_length and len(content) <= max_length:
                # print(f"Found good review for IMDb ID {imdb_id} on page {page}")
                good_reviews.append(content)
                if len(good_reviews) >= 3:
                    print(f"Found enough good reviews for IMDb ID {imdb_id}")
                    return good_reviews
        
        time.sleep(random.uniform(0.1, 0.2))
    
    if not good_reviews:
        print(f"Did not find enough good reviews for IMDb ID {imdb_id}")
        url = f'https://www.imdb.com/title/{imdb_id}/reviews?sort=helpfulnessScore&dir=desc&page=1'
        response = requests.get(url, headers=HEADERS_UA, timeout=10)
        
        if response.ok:
            soup = BeautifulSoup(response.text, 'html.parser')
            section = soup.find('section', class_='ipc-page-section ipc-page-section--base ipc-page-section--sp-pageMargin')
            if section:
                review_articles = section.find_all('article', class_='sc-a77dbebd-1 iJQoqi user-review-item')[:1]
                if review_articles:
                    article = review_articles[0]
                    card = article.find('div', class_='ipc-list-card--border-speech ipc-list-card--hasActions ipc-list-card--base ipc-list-card sc-19165bb8-0 dGaXAC')
                    if card:
                        content_div = card.find('div', class_='ipc-list-card__content')
                        if content_div:
                            overflow_text = content_div.find('div', class_='ipc-overflowText ipc-overflowText--listCard ipc-overflowText--height-long ipc-overflowText--long ipc-overflowText--click ipc-overflowText--base')
                            if overflow_text:
                                overflow_children = overflow_text.find('div', class_='ipc-overflowText--children')
                                if overflow_children:
                                    html_content = overflow_children.find('div', class_='ipc-html-content ipc-html-content--base')
                                    if html_content:
                                        inner_div = html_content.find('div', class_='ipc-html-content-inner-div')
                                        content = inner_div.text.strip() if inner_div else ''
                                        if content:
                                            return [content]
    
    return good_reviews

def capture_session_data(movie_id):
    options = uc.ChromeOptions()
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    driver = uc.Chrome(options=options, use_custom_process=True)
    try:
        url = f"https://www.imdb.com/title/{movie_id}/reviews"
        driver.get(url)

        try:
            load_more_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".ipc-see-more__button"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button)
            time.sleep(0.5)
            load_more_button.click()
            time.sleep(0.5)
        except Exception as e:
            print(f"Load more button not found or clickable: {e}")
            pass
        
        logs = driver.get_log("performance")
        graphql_url = "https://caching.graphql.imdb.com/"
        headers = {}
        payload = None
        after_cursor = ""
        persisted_query = ""
        
        for entry in logs:
            try:
                log = json.loads(entry["message"])["message"]
                if log["method"] == "Network.requestWillBeSent" and graphql_url in log["params"]["request"]["url"]:
                    request = log["params"]["request"]
                    url = request["url"]
                    if "TitleReviewsRefine" in url:
                        headers = {k: v for k, v in request["headers"].items() 
                                 if k in ["User-Agent", "content-type", "Referer",  "x-imdb-client-name", "x-imdb-client-rid", "x-amzn-sessionid", "x-imdb-user-country", "x-imdb-user-language", "x-imdb-weblab-treatment-overrides", "Cookie", "Accept"]}
                        
                        persisted_query = json.loads(urllib.parse.parse_qs(urllib.parse.urlparse(url).query)['extensions'][0])['persistedQuery']['sha256Hash']

                        if request["method"] == "POST":
                            try:
                                payload = json.loads(request.get("postData", "{}"))
                                after_cursor = payload.get("variables", {}).get("after", "")
                            except json.JSONDecodeError:
                                print("Failed to parse POST data")
                                pass
                        break
            except (KeyError, json.JSONDecodeError) as e:
                print(f"Error parsing log entry: {e}")
                continue
        
        return headers, payload, after_cursor, persisted_query
    
    except Exception as e:
        print(f"Error in capture_session_data: {e}")
        return {}, None, ""
    finally:
        driver.quit()

def get_movie_reviews_imdb_api(imdb_id, min_length=500, max_length=1500, headers=None, after=None, persisted_query=None):
    good_reviews = []
    has_next_page = True
    
    while has_next_page:
        variables = {
            "after": after,
            "const": imdb_id,
            "filter": {},
            "first": 25,
            "locale": "en-US",
            "sort": {
                "by": "HELPFULNESS_SCORE",
                "order": "DESC"
            }
        }
        
        extensions = {
            "persistedQuery": {
                "sha256Hash": persisted_query,
                "version": 1
            }
        }
        
        variables_encoded = urllib.parse.quote(json.dumps(variables))
        extensions_encoded = urllib.parse.quote(json.dumps(extensions))
        
        url = f'https://caching.graphql.imdb.com/?operationName=TitleReviewsRefine&variables={variables_encoded}&extensions={extensions_encoded}'

        response = requests.get(url, headers=headers, timeout=10)

        if not response.ok:
            print(f"Request failed ({response.status_code}): {response.text}")
            break
            
        reviews = response.json().get('data', {}).get('title', {}).get('reviews', {})

        if not reviews:
            break

        has_next_page = reviews.get('pageInfo', {}).get('hasNextPage', False)

        if has_next_page:
            after = reviews.get('pageInfo', {}).get('endCursor', None)

        edges = reviews.get('edges', [])

        if not edges:
            continue

        review_texts = [
            edge.get('node', {}).get('text', {}).get('originalText', {}).get('plaidHtml', '')
            for edge in edges
            if edge.get('node', {}).get('text', {}).get('originalText', {}).get('plaidHtml', '')
        ]
            
        for review in review_texts:
            soup = BeautifulSoup(review, 'html.parser')
            review = soup.get_text()
            if len(review) >= min_length and len(review) <= max_length:
                # print(f"Found good review for movie id {imdb_id} on cursor {after}")
                good_reviews.append(review)
                if len(good_reviews) >= 3:
                    print(f"Found enough good reviews for movie id {imdb_id}")
                    return good_reviews
        
        time.sleep(random.uniform(0.1, 0.2))
    
    if not good_reviews:
        print(f"Did not find enough good reviews for IMDb ID {imdb_id}")

        variables = {
            "after": after,
            "const": imdb_id,
            "filter": {},
            "first": 25,
            "locale": "en-US",
            "sort": {
                "by": "HELPFULNESS_SCORE",
                "order": "DESC"
            }
        }
        
        extensions = {
            "persistedQuery": {
                "sha256Hash": persisted_query,
                "version": 1
            }
        }
        
        variables_encoded = urllib.parse.quote(json.dumps(variables))
        extensions_encoded = urllib.parse.quote(json.dumps(extensions))
        
        url = f'https://caching.graphql.imdb.com/?operationName=TitleReviewsRefine&variables={variables_encoded}&extensions={extensions_encoded}'
        response = requests.get(url, headers=headers, timeout=10)
        
        if not response.ok:
            print(f"Request failed ({response.status_code}): {response.text}")
            return []
            
        reviews = response.json().get('data', {}).get('title', {}).get('reviews', {})

        if not reviews:
            return []

        edges = reviews.get('edges', [])

        if not edges:
            return []

        review_texts = [
            edge.get('node', {}).get('text', {}).get('originalText', {}).get('plaidHtml', '')
            for edge in edges
            if edge.get('node', {}).get('text', {}).get('originalText', {}).get('plaidHtml', '')
        ]
            
        for review in review_texts:
            soup = BeautifulSoup(review, 'html.parser')
            review = soup.get_text()
            good_reviews.append(review)
    
    return good_reviews

def get_or_create_genre(cursor, id, name):
    cursor.execute("SELECT id FROM genre WHERE id = %s", (id,))
    result = cursor.fetchone()

    if result:
        return result[0]
    else:
        cursor.execute(
            "INSERT INTO genre (id, name) VALUES (%s, %s) RETURNING id",
            (id, name)
        )
        return cursor.fetchone()[0]
    
def get_or_create_keyword(cursor, id, name):
    cursor.execute("SELECT id FROM keyword WHERE id = %s", (id,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    else:
        cursor.execute(
            "INSERT INTO keyword (id, name) VALUES (%s, %s) RETURNING id",
            (id, name)
        )
        return cursor.fetchone()[0]
    
def get_or_create_movie(cursor, data):
    movie_id = data["id"]
    
    cursor.execute("SELECT id FROM movie WHERE id = %s", (movie_id,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    
    cursor.execute(
        """
        INSERT INTO movie (
            id,
            adult,
            backdrop_path,
            original_language,
            overview,
            popularity,
            poster_path,
            release_date,
            title,
            vote_average,
            vote_count
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            data.get("id"),
            data.get("adult"),
            data.get("backdrop_path"),
            data.get("original_language"),
            data.get("overview"),
            data.get("popularity"),
            data.get("poster_path"),
            data.get("release_date"),
            data.get("title"),
            data.get("vote_average"),
            data.get("vote_count")
        )
    )
    return cursor.fetchone()[0]

def update_imdb_ids(connect, cursor):
    cursor.execute("SELECT id FROM movie")
    movie_ids = [row[0] for row in cursor.fetchall()]

    print(f"Updating IMDB IDs for {len(movie_ids)} movies...")

    for i, movie_id in enumerate(movie_ids):
        imdb_id = get_imdb_id(movie_id)
        
        if imdb_id != -1:
            cursor.execute(
                "UPDATE movie SET imdb_id = %s WHERE id = %s",
                (imdb_id, movie_id)
            )

        if i % 100 == 0:
            print(f'Processed {i} movies...')
            connect.commit()
            
        time.sleep(0.1)

    connect.commit()
    print('IMDB ID updates complete.')

def commit_genres(connect, cursor):
    genres = get_movie_genres()

    for genre in genres:
        get_or_create_genre(cursor, genre['id'], genre['name'])

    connect.commit()

def commit_movies(connect, cursor):
    movie_data, total_pages = get_top_rated_movies(1)

    if not movie_data:
        return
    
    for page in range(2, total_pages + 1):
        print(f'Fetching page {page}...')

        page_data, _ = get_top_rated_movies(page)

        if page_data:
            movie_data.extend(page_data)
        
        time.sleep(0.3)

    for movie in movie_data:
        movie_id = movie['id']
        genre_ids = movie.get('genre_ids', [])

        get_or_create_movie(cursor, movie)

        for genre_id in genre_ids:
            cursor.execute("SELECT id FROM genre WHERE id = %s", (genre_id,))
            genre_row = cursor.fetchone()

            if genre_row:
                cursor.execute("""
                    INSERT INTO movie_genre (movie_id, genre_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """, (movie_id, genre_id))

    connect.commit()

    print('Successfully commited all pages!')

def commit_keywords(connect, cursor):
    cursor.execute("SELECT id FROM movie")
    movie_ids = [row[0] for row in cursor.fetchall()]

    print(f"Fetching keywords for {len(movie_ids)} movies...")

    for i, movie_id in enumerate(movie_ids):
        keywords = get_movie_keywords(movie_id)

        for kw in keywords:
            keyword_id = kw['id']
            name = kw['name']

            cursor.execute("""
                INSERT INTO keyword (id, name)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (keyword_id, name))

            cursor.execute("""
                INSERT INTO movie_keyword (movie_id, keyword_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (movie_id, keyword_id))

        if i % 50 == 0:
            print(f'Processed {i} movies...')
            connect.commit()

        time.sleep(0.3)

    connect.commit()

    print('Keyword linking complete.')

def commit_reviews(connect, cursor):
    cursor.execute("SELECT id, imdb_id FROM movie")
    movie_data = cursor.fetchall()

    if not movie_data:
        print("No movies found in the database to fetch reviews for.")
        return
    
    print(f"Fetching reviews for {len(movie_data)} movies...")

    headers, _, after, persisted_query = capture_session_data('tt0166924')

    resume_index = 0

    for i, (movie_id, imdb_id) in enumerate(movie_data[resume_index:], start=resume_index):
        reviews = get_movie_reviews_imdb_api(imdb_id, headers=headers, after=after, persisted_query=persisted_query)

        for review_content in reviews:
            cursor.execute("""
                INSERT INTO movie_review (movie_id, review_content)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (movie_id, review_content))

        if i % 50 == 0:
            print(f'Processed {i} movies...')
            connect.commit()

        # time.sleep(0.1)

    connect.commit()

    print('Reviews linking complete.')

def commit_all():
    connect = psycopg2.connect(dbname='movies', user='postgres', password='8055', host='localhost')
    cursor = connect.cursor()

    commit_movies(connect, cursor)
    commit_genres(connect, cursor)
    commit_keywords(connect, cursor)
    update_imdb_ids(connect, cursor)
    commit_reviews(connect, cursor)

    if cursor:
        cursor.close()
    if connect:
        connect.close()

def populate_nce(connect, cursor):
    cursor.execute("SELECT id FROM movie")
    movie_ids = [row[0] for row in cursor.fetchall()]
    df = pd.read_pickle(NCE_PATH)

    print("Loaded DF.")
    print(df.head())

    print(f"Adding NCEs for {len(movie_ids)} movies...")

    for i, row in df.iterrows():
        movie_id = row['id']
        overview_emb = row['overview_emb'].tolist()
        genres_emb = row['genres_emb'].tolist()
        keywords_emb = row['keywords_emb'].tolist()
        vote_scaled = row['vote_average_scaled']

        cursor.execute(
            """
            UPDATE movie
            SET
                overview_emb = %s,
                genres_emb = %s,
                keywords_emb = %s,
                vote_average_scaled = %s
            WHERE id = %s
            """,
            (overview_emb, genres_emb, keywords_emb, vote_scaled, movie_id)
        )

        if i % 100 == 0:
            print(f'Processed {i} movies...')
            connect.commit()

    connect.commit()
    print('Adding NCEs complete.')

def populate_ce(connect, cursor):
    cursor.execute("SELECT id FROM movie")
    movie_ids = [row[0] for row in cursor.fetchall()]
    df = pd.read_pickle(CE_PATH)

    print("Loaded DF.")
    print(df.head())

    print(f"Adding CEs for {len(movie_ids)} movies...")

    for i, row in df.iterrows():
        movie_id = row['id']
        atmosphere = row['atmosphere']
        narrative = row['narrative_structure']
        themes = row['themes']
        atmosphere_emb = row['atmosphere_emb'].tolist()
        narrative_emb = row['narrative_emb'].tolist()
        themes_emb = row['themes_emb'].tolist()
        combined_emb = row['combined_emb'].tolist()

        cursor.execute(
            """
            UPDATE movie
            SET
                atmosphere = %s,
                narrative = %s,
                themes = %s,
                atmosphere_emb = %s,
                narrative_emb = %s,
                themes_emb = %s,
                classified_emb_combined = %s
            WHERE id = %s
            """,
            (atmosphere, narrative, themes, atmosphere_emb, narrative_emb, themes_emb, combined_emb, movie_id)
        )

        if i % 100 == 0:
            print(f'Processed {i} movies...')
            connect.commit()

    connect.commit()
    print('Adding CEs complete.')

def work_db():
    connect = psycopg2.connect(dbname='your-db-name', user='your-user', password='your-password', host='your-host')
    cursor = connect.cursor()

    populate_nce(connect, cursor)
    populate_ce(connect, cursor)

    if cursor:
        cursor.close()
    if connect:
        connect.close()

# work_db()
