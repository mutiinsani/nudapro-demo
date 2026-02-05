import pandas as pd
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

API_KEY = os.getenv("NIVU_API_KEY")
API_URL = f"https://api.nivu.com.br/v1/pricing-app/inference/udata-api/{API_KEY}"
NIVU_SEARCH_API = f"https://api.nivu.com.br/v1/pricing-app/inference/places/{API_KEY}"
DISCOUNT_RATE = 0.12  # 12% annual discount rate

itbiDF = pd.read_csv('itbi_residential.csv')
mort_male = pd.read_csv('mort_male.csv')
mort_female = pd.read_csv('mort_female.csv')
mort_other = pd.read_csv('mort_other.csv')

def nivu_valuation(payload):
    """
    Call the NIVU API to get property valuation based on property data.
    """
    headers = {
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        API_URL,
        headers=headers,
        json=payload,
        timeout=30
    )

    if response.status_code == 200:
        result = response.json()
    else:
        print("Request failed")
        print("Status code:", response.status_code)
        print(response.text)
        return None

    return result

def get_itbi_price(postal_code, property_type, built_area_sqm):
    """
    Get ITBI price from the CSV data based on property characteristics.
    """
    bucket_start = (built_area_sqm // 100) * 100
    print(f"  ITBI Search - Postal Code: {postal_code}, Bucket Start: {bucket_start}")
    res = itbiDF[(itbiDF.postal_code == postal_code) & 
                 (itbiDF.bucket_start == bucket_start)]
    
    
    itbi_price_avg = res.declared_transaction_value.mean() if not res.empty else 0
    itbi_price_min = res.declared_transaction_value.min() if not res.empty else 0
    itbi_price_max = res.declared_transaction_value.max() if not res.empty else 0
    
    return itbi_price_avg, itbi_price_min, itbi_price_max
    


def nivu_search_neigh(query ):
    """
    Search for neighborhoods using NIVU API.
    
    Args:
        query (str): Neighborhood search query (e.g., "ibirapuera")
    
    Returns:
        list: List of neighborhoods with label and value
    """
    try:
        params = {"q": query}
        
        response = requests.get(
            NIVU_SEARCH_API,
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("data", [])
        else:
            print(f"NIVU API error: {response.status_code}")
            return []
    
    except Exception as e:
        print(f"Error calling NIVU search API: {str(e)}")
        return []

@app.route('/api/search-neighborhood', methods=['POST'])
def search_neighborhood():
    """
    Search for neighborhoods and return results.
    """
    data = request.json
    query = data.get('query', '').strip()
    
    if not query or len(query) < 2:
        return jsonify({
            'success': False,
            'message': 'Search query must be at least 2 characters'
        }), 400
    
    results = nivu_search_neigh(query)
    
    return jsonify({
        'success': True,
        'results': results
    })

@app.route('/api/calculate-price', methods=['POST'])
def calculate_price():
    """
    Main endpoint to calculate property prices based on combined Property and Personal Data.
    """
    data = request.json
    
    # Extract Property Data
    property_data = data.get('propertyData', {})
    personal_data = data.get('personalData', {})
    
    # Validate required fields
    if not property_data or not personal_data:
        return jsonify({
            'success': False,
            'message': 'Missing property or personal data'
        }), 400
    
    try:
        # Extract property information
        neighborhood = property_data.get('neighborhood')  # This is the label (e.g., "sp>barretos>ibirapuera")
        postal_code = int(property_data.get('postalCode'))
        address = property_data.get('address')
        property_type = int(property_data.get('propertyType'))
        area = int(property_data.get('area', 0))
        
        price = float(property_data.get('price', 0))
        unit_price = price / area if area > 0 else 0
        
        bedrooms = int(property_data.get('bedrooms', 0))
        bathrooms = int(property_data.get('bathrooms', 0))
        suites = int(property_data.get('suites', 0))
        parking_spaces = int(property_data.get('parkingSpaces', 0))
        
        # Extract personal information
        name = personal_data.get('name')
        email = personal_data.get('email')
        date_of_birth = personal_data.get('dateOfBirth')
        gender = personal_data.get('gender')
        
        # Validate required fields
        if not neighborhood or not postal_code or not address:
            return jsonify({
                'success': False,
                'message': 'Missing required property fields'
            }), 400
        
        if not name or not email or not date_of_birth or not gender:
            return jsonify({
                'success': False,
                'message': 'Missing personal data fields'
            }), 400
        
        # Validate email format
        if '@' not in email:
            return jsonify({
                'success': False,
                'message': 'Invalid email format'
            }), 400
        
        # Validate date of birth
        try:
            dob = datetime.strptime(date_of_birth, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Invalid date of birth format'
            }), 400
        
        # Prepare NIVU payload using neighborhood label
        nivu_payload = {
            "location": neighborhood,  # Use the label format (e.g., "sp>barretos>ibirapuera")
            "type": property_type,
            "business": 1,
            "area": area,
            "areaRange": 0.3,
            "unitPrice": unit_price,
            "unitPriceRange": 0.3,
            "bedrooms": bedrooms,
            "suites": suites,
            "bathrooms": bathrooms,
            "parkingSpaces": parking_spaces
        }
        
        # Get NIVU valuation
        print("payload:", nivu_payload)
        nivu_result = nivu_valuation(nivu_payload)
        
        if not nivu_result:
            return jsonify({
                'success': False,
                'message': 'Failed to retrieve NIVU pricing data'
            }), 500
        
        nivu_pricing = nivu_result.get("pricing", {})
        nivu_score = nivu_result.get("score", {})
        
        nivu_price = nivu_pricing.get("inference", 0)
        # nivu_median = nivu_pricing.get("price", 0)
        nivu_liquidity_label = nivu_score.get("fit", "N/A")
        nivu_liquidity_value = nivu_score.get("value", 0)
        print(f"  Liquidity: {nivu_liquidity_label} ({nivu_liquidity_value})")
        
        
        # Get ITBI price
        itbi_avg, itbi_min, itbi_max = get_itbi_price(
            postal_code=postal_code,
            property_type="RESIDÊNCIA",
            built_area_sqm=area
        )
        
        print(f"  NIVU Price: R$ {nivu_price}")
        print(f"  ITBI Avg Price: R$ {itbi_avg}")
        print(f"  ITBI Price Range: R$ {itbi_min} - R$ {itbi_max}")
        
        age = (datetime.now() - dob).days // 365
        print(f"  Personal Info - Name: {name}, Email: {email}, Age: {age}, Gender: {gender}")
        # Calculate desagio or other adjustments if needed
        usu_value, bare_value, desagio_min, desagio_max = calculate_desagio(nivu_price, itbi_avg, itbi_min,itbi_max, gender, age)
        print(f"  Usufruct Value: {usu_value}, Bare Property Value: {bare_value}")
        print(f"  Desagio Min: {desagio_min}, Desagio Max: {desagio_max}")
        
        
        result = jsonify({
            'success': True,
            'nivu_price': nivu_price,
            'desagio_min': desagio_min,
            'desagio_max': desagio_max,
            'usu_value': usu_value,
            'bare_value': bare_value,
            'personal_info': {
                'name': name,
                'email': email,
                'age': age
            }
        })
        
        return result
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': f'Invalid input data: {str(e)}'
        }), 400
    except Exception as e:
        print(f"Error in calculate_price: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while calculating prices'
        }), 500

def actuarial_factor_usufruct(gender: int,start_age: int,discount_rate: float,age_col: str = "exact_age",lx_col: str = "number_alive"):
    lifetable = mort_other

    if gender == 'male':
        lifetable = mort_male
    else:
        lifetable = mort_female
    
    print("  Using mortality table for gender:", gender) 
    table = lifetable.sort_values(age_col).reset_index(drop=True)
    # l(x) at starting age
    lx_start = table.loc[table[age_col] == start_age, lx_col].iloc[0]
    actuarial_factor = 0.0

    for _, row in table.iterrows():
        age = row[age_col]
        if age < start_age:
            continue

        t = age - start_age
        survival_prob = row[lx_col] / lx_start
        discount_factor = 1 / ((1 + discount_rate) ** t)

        actuarial_factor += survival_prob * discount_factor

    return actuarial_factor

def get_usufruct_percentage(actuarial_factor: float, discount_rate: float = 0.12):
    perpetuity_factor = 1 / discount_rate
    usufruct_percentage = min(actuarial_factor / perpetuity_factor, 1.0)
    return usufruct_percentage

def calculate_desagio(nivu_price, itbi_avg, itbi_min,itbi_max, gender, age):
    """
    Calculate property prices based on usufruct percentage, NIVU and ITBI values.
    """
    actuarial_factor = actuarial_factor_usufruct(
        gender=gender,
        start_age=age,
        discount_rate=DISCOUNT_RATE
    )
    print("  Actuarial Factor:", actuarial_factor)
    
    usu_pct = get_usufruct_percentage(
        actuarial_factor=actuarial_factor,
        discount_rate=DISCOUNT_RATE
    )
    print("  Usufruct Percentage:", usu_pct)
    
    variance = abs(nivu_price - itbi_avg) / itbi_avg * 100 if itbi_avg else 0
    print("  Variance between NIVU and ITBI Avg:", variance)
    
    usu_value = nivu_price * usu_pct
    bare_value = nivu_price - usu_value
    
    desagio_min = bare_value / nivu_price * 100 if nivu_price else 0
    desagio_max = None
    
    if variance > 10:
        desagio_min = bare_value / itbi_min * 100 if itbi_min else 0
        desagio_max = bare_value / itbi_max * 100 if itbi_max else 0

    return usu_value, bare_value, desagio_min, desagio_max


if __name__ == '__main__':
    app.run(debug=True, port=5000)
