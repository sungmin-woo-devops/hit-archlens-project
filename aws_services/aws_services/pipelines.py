# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter


class AwsServicesPipeline:
    def process_item(self, item, spider):
        return item


class DedupePipeline:
    def __init__(self):
        self.seen = set()
    def process_item(self, item, spider):
        key = (item.get("group"), item.get("category"), item.get("service"))
        if key in self.seen:
            raise scrapy.exceptions.DropItem("duplicate")
        self.seen.add(key)
        return item
