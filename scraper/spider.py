import scrapy
from scrapy.crawler import CrawlerRunner
from scrapy import signals
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
import crochet

crochet.setup()

BOA_URL = "https://www.bankofalbania.org/Markets/Official_exchange_rate/"

TARGET_CURRENCIES = ["EUR", "USD", "GBP"]


class ExchangeRateSpider(scrapy.Spider):
    name = "boa_exchange_rates"
    start_urls = [BOA_URL]

    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "ROBOTSTXT_OBEY": False,
        "LOG_LEVEL": "WARNING",
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
        # Try to find the date of the exchange rates
        date_text = response.css("div.rates-date::text, span.date::text, .exchange-date::text").get()
        if not date_text:
            # Try alternative selectors
            date_text = response.xpath("//text()[contains(., 'Date') or contains(., 'Datë')]/following::text()[1]").get()
        if not date_text:
            # Look for date in table headers or nearby elements
            date_text = response.xpath("//table//th[contains(text(), 'Date') or contains(text(), 'Datë')]/following-sibling::th/text()").get()
        if not date_text:
            # Try to find date pattern in page
            import re
            page_text = response.text
            date_match = re.search(r'(\d{1,2}[./]\d{1,2}[./]\d{4})', page_text)
            if date_match:
                date_text = date_match.group(1)

        self.results["date"] = date_text.strip() if date_text else "Unknown"

        # Parse exchange rates table
        # Bank of Albania typically has a table with currency codes and rates
        rows = response.css("table tr, table.rates tr")

        for row in rows:
            cells = row.css("td::text, td *::text").getall()
            cells = [c.strip() for c in cells if c.strip()]

            if not cells:
                continue

            # Check if any target currency is in this row
            for currency in TARGET_CURRENCIES:
                if currency in cells:
                    # Find the rate value (usually a number with decimals)
                    for cell in cells:
                        try:
                            # Try to parse as float, handling different decimal separators
                            rate_str = cell.replace(",", ".")
                            rate = float(rate_str)
                            if rate > 0:
                                self.results["rates"][currency] = rate
                                break
                        except ValueError:
                            continue

        # Alternative parsing: look for specific patterns
        if not self.results["rates"]:
            # Try xpath with more specific patterns
            for currency in TARGET_CURRENCIES:
                rate_xpath = f"//tr[contains(., '{currency}')]//td[last()]/text()"
                rate = response.xpath(rate_xpath).get()
                if rate:
                    try:
                        self.results["rates"][currency] = float(rate.strip().replace(",", "."))
                    except ValueError:
                        pass

        # Another alternative: look for currency followed by numbers
        if not self.results["rates"]:
            import re
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

        return self.results


class ScraperService:
    def __init__(self):
        self.results = None

    @crochet.wait_for(timeout=30)
    def scrape(self):
        """Run the spider and return results."""
        self.results = None
        runner = CrawlerRunner()

        @inlineCallbacks
        def crawl():
            spider_results = {}

            def collect_results(item, response, spider):
                spider_results.update(item)

            crawler = runner.create_crawler(ExchangeRateSpider)
            crawler.signals.connect(collect_results, signal=signals.item_scraped)

            yield runner.crawl(crawler)

            # Get results from spider instance
            spider = crawler.spider
            if spider:
                self.results = spider.results

        return crawl()

    def get_exchange_rates(self):
        """Fetch exchange rates from Bank of Albania."""
        try:
            self.scrape()
            return self.results
        except Exception as e:
            return {
                "error": str(e),
                "date": None,
                "rates": {},
                "source": BOA_URL
            }


# Singleton instance
scraper_service = ScraperService()
