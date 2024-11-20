import requests
from bs4 import BeautifulSoup
import time
import datetime
import pandas as pd
import logging
import os
#from src.utils.config import BASE_URL, RECIPE_LIST_URL, HEADERS
import traceback
BASE_URL = 'https://pinchofyum.com/'
RECIPE_LIST_URL = f'{BASE_URL}/recipes/all'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36'
}

# Setup logging with timestamped log file
current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
log_filename = f"../../logs/scraper/scraper_{current_time}.log"
log_dir = os.path.dirname(log_filename)
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
logging.basicConfig(level=logging.INFO, filename=log_filename, filemode='w', format='%(asctime)s - %(message)s')

def get_number_of_pages():
    """
    Retrieves the total number of pages to scrape from the recipe list URL.
    """
    try:
        response = requests.get(RECIPE_LIST_URL, headers=HEADERS)
        soup = BeautifulSoup(response.content, 'html.parser')

        dots_span = soup.find('span', class_='page-numbers dots')
        if dots_span:
            next_page_link = dots_span.find_next('a', class_='page-numbers')
            if next_page_link:
                return int(next_page_link.get_text(strip=True))
    except Exception as e:
        logging.error(f"Error fetching the number of pages: {e}")
    return 1  # Default to a single page if pagination details are unavailable

def get_recipe_links(total_pages):
    """
    Collects all recipe links from the given number of pages.
    """
    recipe_links = []
    for page in range(1, total_pages + 1):
        time.sleep(5)  # Throttle requests to avoid IP blocking
        page_url = f"{RECIPE_LIST_URL}/page/{page}"
        print(f"Fetching recipes from: {page_url}")

        try:
            response = requests.get(page_url, headers=HEADERS)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            articles = soup.select("div.grid.grid-cols-12.gap-4 article")
            recipe_links.extend(article.find("a")["href"] for article in articles)
        except Exception as e:
            logging.error(f"Error fetching page {page}: {e}")
    return recipe_links

def get_recipes(recipe_url):
    """
    Extracts recipe details from a given recipe URL.
    """
    try:
        print(f"Scraping recipe details from {recipe_url}")
        response = requests.get(recipe_url, headers=HEADERS)
        soup = BeautifulSoup(response.content, "html.parser")

        recipe_div = soup.find("div", class_="tasty-recipes")
        recipe = {
            'image': recipe_div.find("img", class_="attachment-thumbnail size-thumbnail")["src"],
            'title': recipe_div.find("h2", class_="tasty-recipes-title").text.strip(),
            'description': recipe_div.find("div", class_="tasty-recipes-description-body").find("p").text.strip() if recipe_div.find("div", class_="tasty-recipes-description-body") else "",
            'total time': recipe_div.find("span", class_="tasty-recipes-total-time").text.strip(),
            'ingredients': [li.input["aria-label"] for li in recipe_div.find("div", class_="tasty-recipes-ingredients-header").find_next_sibling("div").find_all("li")],
            'instructions': [li.text.strip() for li in recipe_div.find("div", class_="tasty-recipes-instructions-header").find_next_sibling("div").find_all("li")]
        }
        return recipe
    except Exception as e:
        logging.error(f"Error scraping {recipe_url}: {e}\n{traceback.format_exc()}")
        return None

def scrape_recipes():
    """
    Orchestrates the scraping of recipes from the website.
    """
    total_pages = get_number_of_pages()
    print(f"Total pages to scrape: {total_pages}")

    recipe_urls = get_recipe_links(total_pages)
    for url in recipe_urls:
        logging.info(f"Scraping started for {url}")
        time.sleep(120)  # Throttle to reduce server load
        recipe_data = get_recipes(url)
        if recipe_data:
            print(recipe_data)
            logging.info(f"Scraping completed for {url}")
            save_recipe_to_csv(recipe_data)
        else:
            logging.error(f"Failed to scrape data from {url}")

def save_recipe_to_csv(recipe, filename='../../data/raw/recipes.csv'):
    """
    Saves a single recipe's data to a CSV file.
    """
    try:
        df = pd.DataFrame([recipe])
        df.to_csv(filename, mode='a', header=not pd.io.common.file_exists(filename), index=False)
    except PermissionError:
        logging.error(f"Permission denied for writing to file: {filename}")
    except OSError as e:
        logging.error(f"OS error while writing to file {filename}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error while writing to file {filename}: {e}")

if __name__ == "__main__":
    scrape_recipes()
