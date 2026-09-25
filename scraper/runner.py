"""
Runner module that executes the Scrapy spider in a subprocess
to avoid Twisted/asyncio reactor conflicts.
"""

import subprocess
import json
import sys
import os
from pathlib import Path
from typing import Optional

BOA_URL = "https://www.bankofalbania.org/Markets/Official_exchange_rate/"


def run_spider(date: Optional[str] = None) -> dict:
    """
    Run the Scrapy spider in a subprocess and return the results.

    Args:
        date: Optional date in DD.MM.YYYY format for historical rates.

    Returns:
        dict: Exchange rate data with keys: date, rates, source
    """
    # Get the path to the spider module
    spider_path = Path(__file__).parent / "spider.py"

    try:
        # Run the spider as a subprocess
        args = [sys.executable, str(spider_path)]
        if date:
            args.append(date)

        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(Path(__file__).parent.parent)
        )

        # Parse the JSON output from stdout
        output = result.stdout.strip()

        if output:
            # Find the JSON object in the output (last line should be our JSON)
            lines = output.split('\n')
            for line in reversed(lines):
                line = line.strip()
                if line.startswith('{') and line.endswith('}'):
                    try:
                        return json.loads(line)
                    except json.JSONDecodeError:
                        continue

        # If we couldn't parse output, return error
        return {
            "date": None,
            "rates": {},
            "source": BOA_URL,
            "error": f"Failed to parse spider output: {result.stderr or 'No output'}"
        }

    except subprocess.TimeoutExpired:
        return {
            "date": None,
            "rates": {},
            "source": BOA_URL,
            "error": "Spider execution timed out"
        }
    except Exception as e:
        return {
            "date": None,
            "rates": {},
            "source": BOA_URL,
            "error": str(e)
        }


class ScraperService:
    """Service class for fetching exchange rates."""

    def get_exchange_rates(self, date: Optional[str] = None) -> dict:
        """
        Fetch exchange rates from Bank of Albania.

        Args:
            date: Optional date in DD.MM.YYYY format. Defaults to today's rates.

        Returns:
            dict: Exchange rate data
        """
        return run_spider(date)


# Singleton instance
scraper_service = ScraperService()
