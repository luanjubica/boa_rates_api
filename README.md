# Bank of Albania Exchange Rate API

A FastAPI application that uses Scrapy to scrape the Bank of Albania website for daily exchange rates.

## Features

- Fetches daily exchange rates for EUR, USD, and GBP
- Returns data in JSON format
- Built with FastAPI and Scrapy

## Installation

```bash
pip install -r requirements.txt
```

## Running the API

```bash
uvicorn main:app --reload
```

Or:

```bash
python main.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

### GET /
Returns API information.

### GET /health
Health check endpoint.

### GET /rates
Returns all exchange rates (EUR, USD, GBP).

**Response:**
```json
{
  "success": true,
  "date": "16.12.2024",
  "rates": {
    "EUR": 98.50,
    "USD": 92.30,
    "GBP": 115.20
  },
  "source": "https://www.bankofalbania.org/Markets/Official_exchange_rate/",
  "fetched_at": "2024-12-16T10:30:00.000000",
  "error": null
}
```

### GET /rates/{currency}
Returns exchange rate for a specific currency.

**Parameters:**
- `currency`: Currency code (EUR, USD, or GBP)

**Response:**
```json
{
  "success": true,
  "currency": "EUR",
  "rate": 98.50,
  "base": "ALL",
  "date": "16.12.2024",
  "source": "https://www.bankofalbania.org/Markets/Official_exchange_rate/",
  "fetched_at": "2024-12-16T10:30:00.000000"
}
```

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Notes

- Exchange rates are in Albanian Lek (ALL)
- Data is scraped from the official Bank of Albania website
