from flask import Flask, jsonify, send_from_directory
import csv
import os
from collections import defaultdict, Counter

app = Flask(__name__, static_folder='.', static_url_path='')

# --- Configuration ---
CSV_FILE_PATH = 'hh_vacancies_data_python_developer_113.csv'
MIN_SALARY_DATA_POINTS_FOR_AVG = 3
TOP_N_SKILLS_FOR_SALARY_CHART = 15
TOP_N_CITIES_FOR_SKILL_BREAKDOWN = 5 # Changed from locations to cities
TOP_N_SKILLS_PER_CITY = 7


def parse_salary(salary_str):
    if salary_str and salary_str.strip():
        try:
            return float(salary_str)
        except ValueError:
            return None
    return None

def parse_skills(skills_str):
    if skills_str and skills_str.strip():
        return [skill.strip() for skill in skills_str.split(',') if skill.strip()]
    return []

def extract_city(address_raw_str):
    """Extracts the first word as the city, assuming it's the city name."""
    if not address_raw_str or not address_raw_str.strip():
        return "Unknown"
    # Split by comma first, take the first part, then split by space and take the first word.
    # This handles cases like "Москва, улица..." and "Санкт-Петербург город..."
    parts = address_raw_str.split(',')[0].strip().split(' ')
    if parts:
        city = parts[0].strip()
        # Handle common cases like "г." or "город" if they are separate and first
        if city.lower() in ["г.", "город"] and len(parts) > 1:
            return parts[1].strip()
        return city
    return "Unknown"


def load_and_process_data(filepath):
    raw_data = []
    if not os.path.exists(filepath):
        print(f"Error: CSV file not found at {filepath}")
        return {"error": f"CSV file not found: {filepath}"}
    try:
        with open(filepath, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                raw_data.append(row)
        print(f"Successfully loaded {len(raw_data)} rows from {filepath}")
    except Exception as e:
        print(f"Error reading CSV file {filepath}: {e}")
        return {"error": f"Error reading CSV: {e}"}

    skill_salaries = defaultdict(list)
    for row in raw_data:
        salary = parse_salary(row.get('salary_from'))
        skills = parse_skills(row.get('key_skills'))
        if salary is not None and salary > 0:
            for skill in skills:
                skill_salaries[skill].append(salary)

    skill_avg_salary_data = []
    for skill, salaries in skill_salaries.items():
        if len(salaries) >= MIN_SALARY_DATA_POINTS_FOR_AVG:
            avg_salary = sum(salaries) / len(salaries)
            skill_avg_salary_data.append({"skill": skill, "avg_salary": round(avg_salary), "count": len(salaries)})
    
    skill_avg_salary_data.sort(key=lambda x: x['avg_salary'], reverse=True)
    top_skill_avg_salary_data = skill_avg_salary_data[:TOP_N_SKILLS_FOR_SALARY_CHART]

    city_skill_counts = defaultdict(lambda: Counter())
    city_counts = Counter()

    for row in raw_data:
        city = extract_city(row.get('address_raw')) # Use new extraction function
        city_counts[city] += 1
        skills = parse_skills(row.get('key_skills'))
        for skill in skills:
            city_skill_counts[city][skill] += 1

    top_cities = [loc for loc, count in city_counts.most_common(TOP_N_CITIES_FOR_SKILL_BREAKDOWN) if loc != "Unknown"]
    
    skills_by_top_city_data = []
    for city_name in top_cities:
        top_skills_for_city = city_skill_counts[city_name].most_common(TOP_N_SKILLS_PER_CITY)
        skills_by_top_city_data.append({
            "city": city_name,
            "vacancy_count": city_counts[city_name],
            "skills": [{"skill": skill, "count": count} for skill, count in top_skills_for_city]
        })
    
    return {
        "all_vacancies": raw_data,
        "skill_salary_correlation": top_skill_avg_salary_data,
        "skills_by_city": skills_by_top_city_data # Renamed from skills_by_location
    }

PROCESSED_DATA = {}

@app.before_request
def load_data_once():
    global PROCESSED_DATA
    if not PROCESSED_DATA or PROCESSED_DATA.get("error"):
        print("Loading and processing data...")
        PROCESSED_DATA = load_and_process_data(CSV_FILE_PATH)
        if PROCESSED_DATA.get("error"):
            print(f"Failed to load/process data: {PROCESSED_DATA.get('error')}")

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/jobdata/all')
def get_all_job_data():
    if PROCESSED_DATA.get("error"):
        return jsonify(PROCESSED_DATA), 500
    return jsonify(PROCESSED_DATA.get("all_vacancies", []))

@app.route('/api/jobdata/skill_salary')
def get_skill_salary_data():
    if PROCESSED_DATA.get("error"):
        return jsonify(PROCESSED_DATA), 500
    return jsonify(PROCESSED_DATA.get("skill_salary_correlation", []))

@app.route('/api/jobdata/skills_by_city') # Renamed endpoint
def get_skills_by_city_data():
    if PROCESSED_DATA.get("error"):
        return jsonify(PROCESSED_DATA), 500
    return jsonify(PROCESSED_DATA.get("skills_by_city", []))


if __name__ == '__main__':
    if not os.path.exists(CSV_FILE_PATH):
        print(f"--- WARNING ---")
        print(f"CSV file '{CSV_FILE_PATH}' not found. API endpoints will likely fail.")
        print(f"---------------")
    app.run(debug=True, port=5001)