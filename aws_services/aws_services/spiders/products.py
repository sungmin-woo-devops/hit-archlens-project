# aws_services/spiders/products.py
import re
import scrapy
from urllib.parse import urljoin
from aws_services.items import ProductItem

BAD_TEXT = {
    "Learn more", "Get started", "Docs", "Documentation", "Pricing", "FAQ",
    "What Is AWS?", "Create an AWS account", "AWS Partners", "AWS Trust Center",
    "AWS Support Overview", "AWS Accessibility"
}
SERVICE_PREFIXES = ("Amazon ", "AWS ", "Elastic ", "CloudFront", "Aurora", "SageMaker", "RDS", "DynamoDB", "Lambda")

def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").strip())

def _is_service_name(t: str) -> bool:
    t = _norm(t)
    if not t or t in BAD_TEXT:
        return False
    # 서비스명 휴리스틱
    if t.startswith(SERVICE_PREFIXES):
        return True
    # 단어 수가 과도하지 않은 고유명사를 추가 허용
    return len(t.split()) <= 4 and not t.endswith((" Center", " overview", " Overview"))


class ProductsSpider(scrapy.Spider):
    name = "products"
    start_urls = ["https://aws.amazon.com/products/"]

    def start_requests(self):
        for url in self.start_urls:
            # Playwright로 완전 렌더링
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_page_goto_kwargs": {"wait_until": "networkidle"},
                },
            )

    async def parse(self, response):
        # 메인 영역만 대상으로(헤더/푸터 링크 제외)
        main_html = response.css("main").get()
        if main_html:
            response = response.replace(body=main_html.encode(response.charset or "utf-8"))

        found = False

        # 1) Group 섹션(h2/h3) → 내부 Category(h3/h4) → 서비스 링크
        for group_block in response.css("section, div"):
            group = self._extract_group(group_block)
            if not group:
                continue

            # 카테고리 블록들
            cat_blocks = group_block.css("section:has(h3), div:has(h3), section:has(h4), div:has(h4)")
            if not cat_blocks:
                # 그룹 바로 아래 서비스 카드가 나열되는 레이아웃
                for item in self._yield_services(group_block, group=group, category=None, base=response.url):
                    found = True
                    yield item
                continue

            for cb in cat_blocks:
                category = self._extract_category(cb)
                for item in self._yield_services(cb, group=group, category=category, base=response.url):
                    found = True
                    yield item

        # 2) 폴백: A–Z 섹션에서 서비스 확보(그룹/카테고리 미상)
        if not found:
            az = response.urljoin("/products/?nc1=h_ls#A_to_Z")
            yield scrapy.Request(
                az,
                callback=self.parse_az,
                meta={"playwright": True, "playwright_page_goto_kwargs": {"wait_until": "networkidle"}},
            )

    async def parse_az(self, response):
        for a in response.css("a[href]"):
            name = _norm(" ".join(a.css("::text").getall()))
            href = a.attrib.get("href")
            if _is_service_name(name) and href:
                yield ProductItem(
                    group=None, category=None, service=name,
                    service_url=urljoin(response.url, href),
                )

    # ---------- helpers ----------
    def _extract_group(self, sel):
        txt = _norm(sel.css("h2::text, h2 *::text, h3::text, h3 *::text").get())
        if not txt:
            return None
        # AWS 공식 Group 후보(필요 시 추가)
        groups = {
            "Compute", "Storage", "Networking & Content Delivery", "Database",
            "Security, Identity, & Compliance", "Machine Learning", "Analytics",
            "Application Integration", "Developer Tools", "Management & Governance",
            "Migration & Transfer", "Media Services", "Business Applications",
            "End User Computing", "IoT", "AR & VR", "Robotics", "Game Tech",
            "Quantum Technologies", "Customer Enablement", "Blockchain", "Contact Center",
        }
        return txt if txt in groups else None

    def _extract_category(self, sel):
        return _norm(sel.css("h3::text, h3 *::text, h4::text, h4 *::text").get()) or None

    def _yield_services(self, sel, *, group, category, base):
        seen = set()
        for a in sel.css("a[href]"):
            name = _norm(" ".join(a.css("::text").getall()))
            href = a.attrib.get("href")
            if not (_is_service_name(name) and href):
                continue
            key = (name, href)
            if key in seen:
                continue
            seen.add(key)
            yield ProductItem(
                group=group, category=category, service=name,
                service_url=urljoin(base, href),
            )