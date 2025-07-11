import os
import sys
import zipfile
import io
from dotenv import load_dotenv
import requests

# Adjust sys.path so config.py can be found regardless of where the script is started
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from config import COUNTRIES, OUTPUT_DIR

load_dotenv()

RINF_API_URL = os.getenv('RINF_API_URL')
RINF_USERNAME = os.getenv('RINF_USERNAME')
RINF_PASSWORD = os.getenv('RINF_PASSWORD')

def get_token():
    url = f"{RINF_API_URL}/token"
    data = {
        'grant_type': 'password',
        'username': RINF_USERNAME,
        'password': RINF_PASSWORD
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.post(url, data=data, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()

def get_xml_datasets(access_token, member_state_code):
    url = f"{RINF_API_URL}/XmlDatasets/{member_state_code}"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.content
    else:
        response.raise_for_status()

def extract_and_save_xml(zip_content, save_to):
    with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_ref:
        xml_files = [f for f in zip_ref.namelist() if f.endswith('.xml')]
        if not xml_files:
            raise FileNotFoundError("No XML file found in the ZIP archive.")
        xml_file = xml_files[0]
        with zip_ref.open(xml_file) as source, open(save_to, 'wb') as target:
            target.write(source.read())

if __name__ == "__main__":
    try:
        token_response = get_token()
        access_token = token_response['access_token']
        print("Token successfully retrieved.")

        xml_dir = OUTPUT_DIR / 'xml_countries'
        os.makedirs(xml_dir, exist_ok=True)

        for country in COUNTRIES:
            print(f"Processing country: {country}")
            try:
                zip_content = get_xml_datasets(access_token, country)
                saved_xml_path = xml_dir / f'rinf_{country}.xml'
                extract_and_save_xml(zip_content, saved_xml_path)
                print(f"XML file for {country} saved: {saved_xml_path}")
            except Exception as e:
                print(f"Error processing {country}: {e}")

    except Exception as e:
        print(f"Error processing data: {e}")