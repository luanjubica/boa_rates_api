"""
Bank of Albania Exchange Rate API

A FastAPI application that scrapes the Bank of Albania website
for daily exchange rates (EUR, USD, GBP).
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from scraper.runner import scraper_service

app = FastAPI(
    title="Bank of Albania Exchange Rate API",
    description="API for fetching daily exchange rates from Bank of Albania",
    version="1.0.0"
)


class ExchangeRates(BaseModel):
    EUR: Optional[float] = None
    USD: Optional[float] = None
    GBP: Optional[float] = None


class ExchangeRateResponse(BaseModel):
    success: bool
    date: Optional[str] = None
    rates: ExchangeRates
    source: str
    fetched_at: str
    error: Optional[str] = None


@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Bank of Albania Exchange Rate API",
        "version": "1.0.0",
        "endpoints": {
            "/rates": "Get current exchange rates for EUR, USD, GBP",
            "/health": "Health check endpoint"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/rates", response_model=ExchangeRateResponse)
async def get_exchange_rates():
    """
    Fetch the daily exchange rates from Bank of Albania.

    Returns exchange rates for:
    - EUR (Euro)
    - USD (US Dollar)
    - GBP (British Pound)

    Rates are in Albanian Lek (ALL).
    """
    try:
        result = scraper_service.get_exchange_rates()

        if not result:
            raise HTTPException(
                status_code=503,
                detail="Unable to fetch exchange rates"
            )

        rates = ExchangeRates(
            EUR=result.get("rates", {}).get("EUR"),
            USD=result.get("rates", {}).get("USD"),
            GBP=result.get("rates", {}).get("GBP")
        )

        return ExchangeRateResponse(
            success=bool(result.get("rates")),
            date=result.get("date"),
            rates=rates,
            source=result.get("source", "https://www.bankofalbania.org/Markets/Official_exchange_rate/"),
            fetched_at=datetime.utcnow().isoformat(),
            error=result.get("error")
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching exchange rates: {str(e)}"
        )


@app.get("/rates/{currency}")
async def get_single_rate(currency: str):
    """
    Get exchange rate for a specific currency.

    Args:
        currency: Currency code (EUR, USD, or GBP)

    Returns:
        Exchange rate for the specified currency in Albanian Lek (ALL).
    """
    currency = currency.upper()

    if currency not in ["EUR", "USD", "GBP"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid currency: {currency}. Supported currencies: EUR, USD, GBP"
        )

    try:
        result = scraper_service.get_exchange_rates()

        if not result or not result.get("rates"):
            raise HTTPException(
                status_code=503,
                detail="Unable to fetch exchange rates"
            )

        rate = result.get("rates", {}).get(currency)

        if rate is None:
            raise HTTPException(
                status_code=404,
                detail=f"Exchange rate for {currency} not found"
            )

        return {
            "success": True,
            "currency": currency,
            "rate": rate,
            "base": "ALL",
            "date": result.get("date"),
            "source": result.get("source"),
            "fetched_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching exchange rate: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
