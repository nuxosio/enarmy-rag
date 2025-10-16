from datetime import datetime, timezone
import time
import os
import json
import uuid
from dotenv import load_dotenv
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from google.oauth2 import service_account
from google.cloud import storage
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

load_dotenv()
credentials_dict = json.loads(os.getenv("GCP_CREDENTIALS"))
credentials = service_account.Credentials.from_service_account_info(credentials_dict)
GCS_CLIENT = storage.Client(credentials=credentials, project=credentials.project_id)
GCS_BUCKET_NAME = 'clinical-guides'
GCS_BUCKET = GCS_CLIENT.bucket(GCS_BUCKET_NAME)

neon_connection = psycopg2.connect(os.getenv('NEON_CONNECTION_STRING'), cursor_factory=RealDictCursor)

init_url = "https://www.imss.gob.mx/guias_practicaclinica?field_categoria_gs_value=All"
ger = "GER"
grr = "GRR"

def get_category(divContent):
    div_specialty = divContent.find_element(By.CLASS_NAME, "field-name-field-categoria-gs")
    div = div_specialty.find_element(By.CLASS_NAME, "field-items")
    specialty = div.text
    return specialty

def get_guide_section_list():
    try:
        guides_section = driver.find_element(By.CLASS_NAME, "view-content")
        items_list = guides_section.find_elements(By.CLASS_NAME, "item-list")
        ul_elements = items_list[0].find_elements(By.TAG_NAME, "ul")
        items = ul_elements[0].find_elements(By.TAG_NAME, "li")
        return items
    except Exception as e:
        print(f"No more pdfs")
        return []

def download_pdf(pdf_url, gcs_filename, blob):
    try:
        response = requests.get(pdf_url, stream=True)
        if response.status_code == 200:
            blob.upload_from_string(response.content, content_type='application/pdf')
            print(f"Uploaded {gcs_filename} to GCS")
        else:
            print(f"error to download {pdf_url} (status {response.status_code})")
            return None
    except Exception as e:
        print(f"error to upload {pdf_url}: {e}")
        return None

def save_pdf_data_to_db(pdf_data):
    try:
        cursor = neon_connection.cursor()
        cursor.execute("""
                       INSERT INTO clinical_guides (id,name, type, description, category, url, created_at)  
                          VALUES (%s, %s, %s, %s, %s, %s, %s)
                          """, (pdf_data['id'], pdf_data['name'], pdf_data['type'], pdf_data['description'], pdf_data['category'], pdf_data['url'], pdf_data['created_at']))   
        neon_connection.commit()
        cursor.close()  
        print(f"Saved {pdf_data['name']} to database")
    except Exception as e:
        print(f"Error saving {pdf_data['name']} to database: {e}")
                  
def pdf_exists_in_db(gcs_filename):
    try:
        cursor = neon_connection.cursor()
        cursor.execute("SELECT id FROM clinical_guides WHERE name = %s", (gcs_filename,))
        result = cursor.fetchone()
        cursor.close()
        return result is not None
    except Exception as e:
        print(f"Error checking existence of {gcs_filename} in database: {e}")
        return False
    
# Main script
options = Options()
#options.add_argument("--headless")
#options.add_argument("--disable-gpu")
service = Service()  
driver = webdriver.Chrome(service=service, options=options)
driver.get(init_url)
time.sleep(3)
    
page = 0
while True:
    guides_section = get_guide_section_list()
    if not guides_section:
        break
    for section in guides_section:
        title = section.find_element(By.TAG_NAME, "h2")
        description = ",".join(title.text.split(",")[1:]).strip()
        pdf_links = section.find_elements(By.XPATH, ".//a[contains(@href, '.pdf')]")
        category = get_category(section)
            
        for link in pdf_links:
            pdf_url = link.get_attribute("href")
            if not pdf_url:
                continue

            pdf_name = link.text.strip()[4:]
            pdf_type = link.text.strip()[:3]
            gcs_filename = f"{pdf_type}-{pdf_name}.pdf"
            info = {
                    "id": str(uuid.uuid4()),
                    "name": gcs_filename,
                    "type": pdf_type,
                    "description": description,
                    "category": category,
                    "url": f"gs://{GCS_BUCKET_NAME}/{gcs_filename}",
                    "created_at": datetime.now(timezone.utc),
                }

            blob = GCS_BUCKET.blob(gcs_filename)
            if blob.exists() and pdf_exists_in_db(gcs_filename):
                print(f"exist in GCS and db: {gcs_filename}")
        
            elif pdf_exists_in_db(gcs_filename) and not blob.exists():
                print(f"exist in db: {gcs_filename}")
                download_pdf(pdf_url, gcs_filename, blob)
                
            elif blob.exists() and not pdf_exists_in_db(gcs_filename):
                print(f"exist in GCS: {gcs_filename}")                
                save_pdf_data_to_db(info)
                
            else:
                download_pdf(pdf_url, gcs_filename, blob)  
                save_pdf_data_to_db(info)
    page += 1
    driver.get(f"{init_url}&page={page}")
    time.sleep(3)

neon_connection.close()
driver.quit()