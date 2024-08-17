"""Navershoppint Crawler"""

from time import sleep
from pprint import pprint

from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import TimeoutException

from gjdanawa_uploader.configs import CFG_CRAWLER
from gjdanawa_uploader.core.depth_logging import D
from gjdanawa_uploader.utils.crawling import (
    find_element,
    find_elements,
    find_element,
    find_element,
    scroll,
)
from gjdanawa_uploader.utils.elasticsearch.elasticsearch_manager import (
    ElasticSearchManager,
)
from gjdanawa_uploader.crawler.base_crawler import BaseCrawler


class NavershoppingCrawler(BaseCrawler):
    """Navershopping Crawler

    Pages:
        https://msearch.shopping.naver.com/search/all?adQuery=%EB%82%98%EC%9D%B4%ED%82%A4%20%ED%8E%98%EA%B0%80%EC%88%98%EC%8A%A4%2041%20%EB%B8%94%EB%A3%A8%ED%94%84%EB%A6%B0%ED%8A%B8&origQuery=%EB%82%98%EC%9D%B4%ED%82%A4%20%ED%8E%98%EA%B0%80%EC%88%98%EC%8A%A4%2041%20%EB%B8%94%EB%A3%A8%ED%94%84%EB%A6%B0%ED%8A%B8&pagingIndex=1&pagingSize=40&productSet=total&query=%EB%82%98%EC%9D%B4%ED%82%A4%20%ED%8E%98%EA%B0%80%EC%88%98%EC%8A%A4%2041%20%EB%B8%94%EB%A3%A8%ED%94%84%EB%A6%B0%ED%8A%B8&sort=review_rel&viewType=image
    """

    id: str = "navershopping"
    listing_title: str
    seller_name: str
    cfgs: dict
    driver: webdriver.Chrome
    es_manager: ElasticSearchManager

    @D
    def search(self):
        """Search product on Navershopping"""
        # Change the query
        self._load_search_page()

        # Container
        result = []
        n_reviews = 0
        n_pages = 0
        while True:
            last_n_listings = 0
            try:
                # 1. Scroll to the bottom of the page
                scroll(self.driver)

                # 2. Get visible items
                listing_elems = find_elements(
                    self.driver, "div[class^='listContainer_list_inner'] > div"
                )
                cur_n_listings = len(listing_elems)

                # 3. Check if there are more items
                if cur_n_listings > last_n_listings:
                    # 3.1 If there are more items, continue scrolling
                    print(
                        f"  Continue scroll / # extracted items: {len(result)} / # reviews: {n_reviews} / # pages: {n_pages}"
                    )
                    sleep(1)
                    last_n_listings = cur_n_listings
                else:
                    # 3.2 If there are no more items, go to next page or finish
                    items_info = self._extract_items(listing_elems)
                    result.extend(items_info)
                    n_pages += 1

                    # Terminal conditions
                    next_button = self._get_next_button()
                    cond_end = "paginator_disabled" in next_button.get_attribute(
                        "class"
                    )
                    n_reviews += sum(
                        int(item.get("review_count", 0)) for item in items_info
                    )
                    cond_max_reviews = n_reviews >= self.cfgs["crawler"].n_reviews
                    cond_max_items = len(result) >= self.cfgs["crawler"].n_listings

                    print(
                        f"  # extracted items: {len(result)} / # reviews: {n_reviews} / # pages: {n_pages}"
                    )

                    if any((cond_end, cond_max_reviews, cond_max_items)):
                        pprint(result)
                        self.es_manager.insert_documents(
                            result, index=self.cfgs["es"]["listings"]["index"]
                        )
                        return
                    else:
                        next_button.click()
                        break
            except TimeoutException as e:
                print(e)
                print(
                    f"  # extracted items: {len(result)} / # reviews: {n_reviews} / # pages: {n_pages}"
                )

    def _filter(self, item_info: dict) -> bool:
        """Filter items"""
        normalize = lambda s: s.replace(" ", "").lower()

        # Condition 1. listing_title should include all words in product_name (case insensitive, space removed)
        normalized_product_name = item_info["product_name"].lower()
        normalized_listing_title = normalize(item_info["listing_title"])
        words_in_product_name = normalized_product_name.split(" ")
        cond1 = all(word in normalized_listing_title for word in words_in_product_name)

        # filter redirection to other known platforms
        cond2 = all(
            seller_name not in normalize(item_info["seller_name"])
            for seller_name in map(normalize, CFG_CRAWLER.known_marketplaces)
        )

        # TODO: filter with image
        cond3 = True

        conds = [cond1, cond2, cond3]
        return all(conds)

    def _extract_items(self, listing_elems: list[WebElement]) -> list[dict]:
        """Extract items information"""
        items_info = []
        for item in listing_elems:
            # Initial info
            extracted_info = self._initialize_listing_info()
            etc = {}

            # div.product_info_main
            _product_info_main = find_element(item, "div[class^='product_info_main']")

            # div.product_info_main > span.product_img_area > img
            thumbnail_url = find_element(
                _product_info_main, "span[class^='product_img_area'] > img"
            )
            extracted_info["thumbnail_url"] = thumbnail_url

            # div.product_info_main > div.product_txt_area
            _product_txt_area = find_element(
                _product_info_main, "div[class^='product_txt_area']"
            )

            # div.product_info_main > div.product_txt_area > span.product_info_tit > span.product_label
            product_label = find_element(
                _product_txt_area,
                "span[class^='product_info_tit'] > span[class^='product_label']",
            )
            # TODO: change name
            etc["label"] = product_label

            # div.product_info_main > div.product_txt_area > span.product_info_tit
            listing_title = find_element(
                _product_txt_area,
                "span[class^='product_info_tit']",
                removeprefix=product_label,
            )
            extracted_info["listing_title"] = listing_title

            # div.product_info_main > div.product_txt_area > div.product_info_count
            # 리뷰
            _product_info_count = find_elements(
                _product_txt_area, "div[class^='product_info_count'] > span"
            )
            for e in _product_info_count:
                if e.get_attribute("class").startswith("product_grade"):
                    # Review grade
                    label = find_element(e, "span.blind")
                    count = find_element(e, "strong")
                    extracted_info["rating"] = count

                    # Review count
                    count = find_element(e, "em")
                    extracted_info["review_count"] = count
                else:
                    count = find_element(e, "em")
                    label = e.text.removesuffix(count)
                    etc[label] = count

            # div.product_info_main > div.product_txt_area > div.product_price > span.product_num
            product_num = find_element(
                _product_txt_area,
                "div[class^='product_price'] > span[class^='product_num']",
                removesuffix=self.metadata.currency,
            )
            extracted_info["price"] = product_num

            # div.product_info_main > div.product_txt_area > div.product_price > span.product_delivery > span.blind
            _delivery_fee_tag = find_element(
                _product_txt_area,
                "div[class^='product_price'] > span[class^='product_delivery'] > span[class^='blind']",
            )

            # div.product_info_main > div.product_txt_area > div.product_price > span.product_delivery
            delivery_fee = find_element(
                _product_txt_area,
                "div[class^='product_price'] > span[class^='product_delivery']",
                removeprefix=_delivery_fee_tag,
                removesuffix=self.metadata.currency,
            )
            extracted_info["delivery_fee"] = delivery_fee

            # div.product_info_main > div.product_txt_area > div.product_info_area > div.product_link_mall
            seller_name = find_element(
                _product_txt_area,
                "div[class^='product_info_area'] > div[class^='product_link_mall']",
                astype=str,
            )
            extracted_info["seller_name"] = seller_name

            # Naver pay icon
            # div.product_info_main > div.product_txt_area > div.product_info_area > div.product_icon_npay
            # seller_name = product_txt_area.find_element(
            #     By.CSS_SELECTOR,
            #     "div[class^='product_info_area'] > div[class^='product_icon_npay']",
            # )

            # div.product_info_main > a
            product_url = find_element(_product_info_main, "a")
            extracted_info["listing_url"] = product_url

            # div.productExpandSub_info_sub > div.expandList_info_sub_list
            _info_sub = find_elements(
                item,
                "div[class^='productExpandSub_info_sub'] > div[class^='expandList_info_sub_list'] > dl",
            )
            for info in _info_sub:
                key = find_element(info, "dt")
                value = find_element(info, "dd")
                etc[key] = value
            extracted_info["etc"] = etc

            # TODO: expand sub info

            if self._filter(extracted_info):
                items_info.append(extracted_info)

        pprint(items_info)
        return items_info


if __name__ == "__main__":
    # https://www.nike.com/kr/t/%ED%8E%98%EA%B0%80%EC%88%98%EC%8A%A4-41-%EB%B8%94%EB%A3%A8%ED%94%84%EB%A6%B0%ED%8A%B8-%EB%82%A8%EC%84%B1-%EB%A1%9C%EB%93%9C-%EB%9F%AC%EB%8B%9D%ED%99%94-k2kls9T1/HF0013-900
    crawler = NavershoppingCrawler(
        product_name="페가수스 41 블루프린트", brand_name="나이키"
    )
    response = crawler.search()
