import json
import scrapy
from scrapy_playwright.page import PageMethod
from aws_services.items import ProductItem

class ProductsInterceptSpider(scrapy.Spider):
    name = "products_intercept"
    custom_settings = {
        "ROBOTSTXT_OBEY": True,  # 그대로 유지
    }

    def start_requests(self):
        yield scrapy.Request(
            "https://aws.amazon.com/products/",
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_page_methods": [
                    PageMethod("wait_for_load_state", "networkidle", timeout=60_000),
                ],
            },
            callback=self.parse,
        )

    async def parse(self, response):
        page = response.meta["playwright_page"]
        caught = {}

        def _on_response(res):
            url = res.url
            if ("api/dirs/items/search" in url and
                "item.directoryId=products-cards-interactive-aws-products-ams" in url):
                caught["resp"] = res

        page.on("response", _on_response)
        # 이미 로드 완료 상태이므로 짧게 대기
        await page.wait_for_timeout(1500)

        if "resp" not in caught:
            await page.close()
            self.logger.warning("API 응답을 못 잡았습니다")
            return

        data = await caught["resp"].json()
        await page.close()

        for wrapper in data.get("items", []):
            item = wrapper.get("item", wrapper)
            af = item.get("additionalFields", {})
            group = af.get("productCategory") or af.get("category")
            service = af.get("productTitle") or item.get("title")
            url = (af.get("productLink") or item.get("linkURL") or item.get("uri") or "")
            if url and url.startswith("/"):
                url = response.urljoin(url)
            if service:
                yield ProductItem(group=group, category=None, service=service, service_url=url)
