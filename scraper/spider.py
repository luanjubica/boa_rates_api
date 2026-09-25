import scrapy
import json
import re
import sys


BOA_URL = "https://www.bankofalbania.org/Markets/Official_exchange_rate/"
TARGET_CURRENCIES = ["EUR", "USD", "GBP"]


class ExchangeRateSpider(scrapy.Spider):
    name = "boa_exchange_rates"

    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "ROBOTSTXT_OBEY": False,
        "LOG_LEVEL": "ERROR",
        "LOG_ENABLED": False,
        "DOWNLOAD_DELAY": 1,
        "COOKIES_ENABLED": True,
        # Let non-2xx responses reach parse() so we can report them
        "HTTPERROR_ALLOW_ALL": True,
    }

    def __init__(self, date=None, *args, **kwargs):
        """
        Args:
            date: Optional date in DD.MM.YYYY format. When given, the spider
                  queries the historical search instead of today's rates.
        """
        super().__init__(*args, **kwargs)
        self.date = date
        self.results = {
            "date": None,
            "rates": {},
            "source": BOA_URL
        }

    async def start(self):
        # Scrapy >= 2.13 entry point; newer versions no longer call start_requests()
        for request in self.start_requests():
            yield request

    def start_requests(self):
        if not self.date:
            yield scrapy.Request(BOA_URL, callback=self.parse, errback=self.on_error)
            return

        # Same request the site's "Search by period and currency" form sends
        search = (
            f"event=kursi_kembimit.search_this(startDate={self.date};"
            f"endDate={self.date};pubcat=99;menyra_shfaqjes=T)"
        )
        yield scrapy.FormRequest(
            BOA_URL,
            formdata={"ln": "2", "phpVars": search},
            callback=self.parse,
            errback=self.on_error,
        )

    def on_error(self, failure):
        self.results["error"] = f"Request to Bank of Albania failed: {failure.getErrorMessage() or failure.type.__name__}"

    def parse(self, response):
        if response.status != 200:
            self.results["error"] = f"Bank of Albania returned HTTP {response.status}"
            return

        if self.date:
            date_text = response.xpath(
                "//strong[starts-with(normalize-space(), 'Date ')]/text()"
            ).re_first(r"(\d{2}\.\d{2}\.\d{4})")
        else:
            date_text = response.xpath(
                "//span[contains(., 'Last update')]/following-sibling::span[1]/b[1]/text()"
            ).get()
        if not date_text:
            date_match = re.search(r'(\d{1,2}[./]\d{1,2}[./]\d{4})', response.text)
            if date_match:
                date_text = date_match.group(1)

        self.results["date"] = date_text.strip() if date_text else None

        # The official rates are in the first "Main Currency" table; later
        # tables (e.g. bid/ask) also list USD/EUR and must be ignored.
        table = response.xpath("(//table[.//th[contains(., 'Main Currency')]])[1]")
        rows = table.xpath(".//tr") if table else response.css("table tr")

        for row in rows:
            cells = [c.strip() for c in row.xpath("./td//text()").getall() if c.strip()]

            for currency in TARGET_CURRENCIES:
                if currency in self.results["rates"] or currency not in cells:
                    continue
                idx = cells.index(currency)
                if idx + 1 < len(cells):
                    try:
                        self.results["rates"][currency] = float(cells[idx + 1].replace(",", "."))
                    except ValueError:
                        pass

        if not self.results["rates"] and "No records found" in response.text:
            self.results["error"] = f"No exchange rates published for {self.date}"
        elif not self.results["rates"]:
            self.results["error"] = "Could not find exchange rates table in the Bank of Albania page"

        yield self.results

    def closed(self, reason):
        # Output results as JSON to stdout
        print(json.dumps(self.results))


if __name__ == "__main__":
    from scrapy.crawler import CrawlerProcess

    process = CrawlerProcess(settings={
        "LOG_ENABLED": False,
    })
    process.crawl(ExchangeRateSpider, date=sys.argv[1] if len(sys.argv) > 1 else None)
    process.start()
