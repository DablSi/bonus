import requests
import time
import json
import csv # For CSV output

# --- Configuration ---
BASE_URL = "https://api.hh.ru"
SEARCH_TEXT = "python developer"
AREA_ID = "113"  # Russia
TARGET_VACANCIES_COUNT = 1000
PER_PAGE = 100
MAX_PAGES_TO_FETCH_IDS = (TARGET_VACANCIES_COUNT + PER_PAGE - 1) // PER_PAGE

REQUEST_TIMEOUT_SECONDS = 20
OUTPUT_CSV_FILENAME = f"hh_vacancies_data_{SEARCH_TEXT.replace(' ', '_')}_{AREA_ID}.csv" # Updated filename

# Your working User-Agent
HEADERS = {
    'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15"
}

# --- Helper Functions (get_vacancy_ids and get_vacancy_details remain the same as before) ---
def get_vacancy_ids(search_text, area_id, per_page, max_pages, target_count, headers):
    """
    Fetches vacancy IDs from the hh.ru API search.
    """
    vacancy_ids = []
    print(f"Fetching up to {target_count} vacancy IDs for '{search_text}' in area {area_id}...")

    for page_num in range(max_pages):
        if len(vacancy_ids) >= target_count:
            print(f"Target of {target_count} vacancy IDs reached or exceeded. Stopping ID search.")
            break

        params = {
            'text': search_text,
            'area': area_id,
            'per_page': per_page,
            'page': page_num,
            'only_with_salary': 'false',
            'archived': 'false'
        }
        
        prepared_request = requests.Request('GET', f"{BASE_URL}/vacancies", params=params, headers=headers).prepare()
        if (page_num + 1) % 2 == 0 or page_num == 0 :
            print(f"Requesting search page {page_num + 1}/{max_pages} (API page index {page_num})...")

        response_search = None
        try:
            with requests.Session() as session:
                response_search = session.send(prepared_request, timeout=REQUEST_TIMEOUT_SECONDS)
            response_search.raise_for_status()
            data = response_search.json()

            if not data.get('items'):
                print("No more items found in search results. Stopping ID search.")
                break

            for item in data['items']:
                vacancy_ids.append(item['id'])
                if len(vacancy_ids) >= target_count:
                    break 
            
            print(f"Collected {len(vacancy_ids)}/{target_count} vacancy IDs so far.")

            if page_num < max_pages - 1 and len(vacancy_ids) < target_count:
                 time.sleep(0.5) 

        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error fetching search page {page_num + 1}: {e}")
            if e.response is not None: print(f"Response text: {e.response.text[:200]}...")
            break 
        except requests.exceptions.RequestException as e:
            print(f"Request Error fetching search page {page_num + 1}: {e}")
            break
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error from search page {page_num + 1}: {e}")
            if response_search: print(f"Response text: {response_search.text[:200]}...")
            break
            
    return vacancy_ids[:target_count]

def get_vacancy_details(vacancy_id, headers):
    """
    Fetches full details for a single vacancy ID.
    """
    detail_url = f"{BASE_URL}/vacancies/{vacancy_id}"
    response_detail = None
    try:
        with requests.Session() as session:
            response_detail = session.get(detail_url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        response_detail.raise_for_status()
        return response_detail.json()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error fetching details for vacancy {vacancy_id}: {e}")
        if e.response is not None: print(f"Response text: {e.response.text[:200]}...")
    except requests.exceptions.RequestException as e:
        print(f"Request Error fetching details for vacancy {vacancy_id}: {e}")
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error for vacancy {vacancy_id}: {e}")
        if response_detail: print(f"Response text: {response_detail.text[:200]}...")
    return None

# --- Main Script ---
if __name__ == "__main__":
    print(f"--- Starting script to fetch {TARGET_VACANCIES_COUNT} vacancies for '{SEARCH_TEXT}' ---")
    
    # 1. Get Vacancy IDs
    vacancy_ids_to_fetch = get_vacancy_ids(
        SEARCH_TEXT, AREA_ID, PER_PAGE, MAX_PAGES_TO_FETCH_IDS, TARGET_VACANCIES_COUNT, HEADERS
    )
    
    if not vacancy_ids_to_fetch:
        print("No vacancy IDs found or an error occurred during ID fetching. Exiting.")
    else:
        print(f"\nSuccessfully fetched {len(vacancy_ids_to_fetch)} vacancy IDs. Now fetching full details...")

        # List to store dictionaries for each vacancy's combined data
        all_vacancy_data_for_csv = [] 
        
        # 2. Get Full Details and Extract Desired Information
        for i, vac_id in enumerate(vacancy_ids_to_fetch):
            if (i + 1) % 50 == 0 or i == 0 or i == len(vacancy_ids_to_fetch) -1 :
                print(f"Processing vacancy ID {vac_id} ({i+1}/{len(vacancy_ids_to_fetch)})...")
            
            details = get_vacancy_details(vac_id, HEADERS)
            
            if details:
                vacancy_name = details.get('name', '') # Get vacancy name for context if needed
                
                # Extract Salary Info
                salary_info = details.get('salary')
                salary_from = salary_info.get('from') if salary_info else None
                salary_to = salary_info.get('to') if salary_info else None
                salary_currency = salary_info.get('currency') if salary_info else None
                salary_gross = salary_info.get('gross') if salary_info else None
                
                # Extract Address Info
                address_info = details.get('address')
                address_raw = address_info.get('raw') if address_info else None # Often the most useful combined string
                # Or more detailed:
                # address_city = address_info.get('city') if address_info else None
                # address_street = address_info.get('street') if address_info else None
                # address_building = address_info.get('building') if address_info else None

                # Extract Key Skills
                key_skills_list = details.get('key_skills', [])
                skills_str = ", ".join([skill.get('name', '') for skill in key_skills_list if skill.get('name')])

                # Append a dictionary for this vacancy to our list
                all_vacancy_data_for_csv.append({
                    'vacancy_id': vac_id,
                    'vacancy_name': vacancy_name,
                    'salary_from': salary_from,
                    'salary_to': salary_to,
                    'salary_currency': salary_currency,
                    'salary_gross': salary_gross,
                    'address_raw': address_raw,
                    'key_skills': skills_str # Store skills as a comma-separated string
                })
            
            time.sleep(0.3) 

        print(f"\nFinished fetching details for {len(all_vacancy_data_for_csv)} vacancies.")

        # 3. Save Data to CSV
        if all_vacancy_data_for_csv:
            print(f"\nSaving data to {OUTPUT_CSV_FILENAME}...")
            try:
                # Define fieldnames for the CSV
                fieldnames = [
                    'vacancy_id', 'vacancy_name', 
                    'salary_from', 'salary_to', 'salary_currency', 'salary_gross',
                    'address_raw', 'key_skills'
                ]
                with open(OUTPUT_CSV_FILENAME, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    writer.writerows(all_vacancy_data_for_csv)
                print(f"Successfully saved data to {OUTPUT_CSV_FILENAME}")
            except IOError as e:
                print(f"Error writing to CSV file {OUTPUT_CSV_FILENAME}: {e}")
        else:
            print("No data was collected to save.")
            
    print("--- Script finished ---")