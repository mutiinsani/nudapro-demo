# Property Value Calculator

A web application to calculate property values with NIVU and ITBI data.

## Features

- **NIVU DATA Form**: Input property details including location, type, area, unit price, bedrooms, suites, bathrooms, and parking spaces
- **ITBI DATA Form**: Input neighborhood, postal code, and property type
- **Real-time Calculations**: Get NIVU and ITBI prices instantly
- **Price Display**: View 4 calculated prices based on the property data

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Start the Flask backend:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

## API Endpoints

- `POST /api/nivu-price` - Calculate NIVU price
- `POST /api/itbi-price` - Calculate ITBI price

## Project Structure

```
.
├── app.py                 # Flask backend
├── templates/
│   └── index.html        # Frontend HTML+JS
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Usage

1. Fill in the **NIVU DATA** form with property details
2. Click "Get NIVU Price" to calculate
3. Fill in the **ITBI DATA** form with location details
4. Click "Get ITBI Price" to calculate
5. View the calculated prices in the bottom section

## Notes

- The `calculate_prices(usufruct_pct, nivu, itbi)` function is left empty as per requirements and can be implemented with custom logic
- Current calculations are placeholder values and should be replaced with actual business logic
