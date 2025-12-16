import scrapy
import json
import sys


BOA_URL = "https://www.bankofalbania.org/Markets/Official_exchange_rate/"
TARGET_CURRENCIES = ["EUR", "USD", "GBP"]


class ExchangeRateSpider(scrapy.Spider):
    name = "boa_exchange_rates"
    start_urls = [BOA_URL]

    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "ROBOTSTXT_OBEY": False,
        "LOG_LEVEL": "ERROR",
        "LOG_ENABLED": False,
        "DOWNLOAD_DELAY": 1,
        "COOKIES_ENABLED": True,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.results = {
            "date": None,
            "rates": {},
            "source": BOA_URL
        }

    def parse(self, response):
        import re

        # Try to find the date of the exchange rates
        date_text = response.css("div.rates-date::text, span.date::text, .exchange-date::text").get()
        if not date_text:
            date_text = response.xpath("//text()[contains(., 'Date') or contains(., 'Datë')]/following::text()[1]").get()
        if not date_text:
            date_text = response.xpath("//table//th[contains(text(), 'Date') or contains(text(), 'Datë')]/following-sibling::th/text()").get()
        if not date_text:
            page_text = response.text
            date_match = re.search(r'(\d{1,2}[./]\d{1,2}[./]\d{4})', page_text)
            if date_match:
                date_text = date_match.group(1)

        self.results["date"] = date_text.strip() if date_text else "Unknown"

        # Parse exchange rates table
        rows = response.css("table tr, table.rates tr")

        for row in rows:
            cells = row.css("td::text, td *::text").getall()
            cells = [c.strip() for c in cells if c.strip()]

            if not cells:
                continue

            for currency in TARGET_CURRENCIES:
                if currency in cells:
                    for cell in cells:
                        try:
                            rate_str = cell.replace(",", ".")
                            rate = float(rate_str)
                            if rate > 0:
                                self.results["rates"][currency] = rate
                                break
                        except ValueError:
                            continue

        # Alternative parsing with xpath
        if not self.results["rates"]:
            for currency in TARGET_CURRENCIES:
                rate_xpath = f"//tr[contains(., '{currency}')]//td[last()]/text()"
                rate = response.xpath(rate_xpath).get()
                if rate:
                    try:
                        self.results["rates"][currency] = float(rate.strip().replace(",", "."))
                    except ValueError:
                        pass

        # Regex fallback
        if not self.results["rates"]:
            page_text = response.text
            for currency in TARGET_CURRENCIES:
                pattern = rf'{currency}[^\d]*(\d+[.,]\d+)'
                match = re.search(pattern, page_text)
                if match:
                    rate_str = match.group(1).replace(",", ".")
                    try:
                        self.results["rates"][currency] = float(rate_str)
                    except ValueError:
                        pass

        yield self.results

    def closed(self, reason):
        # Output results as JSON to stdout
        print(json.dumps(self.results))


if __name__ == "__main__":
    from scrapy.crawler import CrawlerProcess

    process = CrawlerProcess(settings={
        "LOG_ENABLED": False,
    })
    process.crawl(ExchangeRateSpider)
    process.start()
