import json
import scrapy
from aws_services.items import ProductItem

class ProductsAPISpider(scrapy.Spider):
    name = "products_api"
    custom_settings = {
        "ROBOTSTXT_OBEY": False,        # 이 스파이더에만 적용
        "CONCURRENT_REQUESTS": 4,
        "DOWNLOAD_DELAY": 0.25,
    }

    start_urls = [
        ("https://aws.amazon.com/api/dirs/items/search"
         "?item.directoryId=aws-products"
         "&item.locale=en_US"
         "&size=500"
         "&sort_by=item.additionalFields.productCategory"
         "&sort_order=asc")
    ]

    def parse(self, response):
        data = json.loads(response.text)
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
