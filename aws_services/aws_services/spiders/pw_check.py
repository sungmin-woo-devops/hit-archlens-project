# aws_services/spiders/pw_check.py
import scrapy

class PwCheckSpider(scrapy.Spider):
    name = "pw_check"
    start_urls = ["https://aws.amazon.com/products/"]

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta={"playwright": True, "playwright_page_methods": [
                    ("wait_for_load_state", "networkidle")
                ]},
            )

    async def parse(self, response):
        # 렌더링된 본문 일부 확인
        title = response.css("title::text").get()
        yield {"title": title, "len": len(response.text)}

