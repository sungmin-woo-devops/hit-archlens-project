# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy

class ProductItem(scrapy.Item):
    group = scrapy.Field()
    category = scrapy.Field()
    service = scrapy.Field()
    service_url = scrapy.Field()


class AwsServicesItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass
