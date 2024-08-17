"""11st Crawler"""

import re
import traceback

from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement

from dask import delayed, compute
from dask.diagnostics import ProgressBar

from gjdanawa_uploader.core.depth_logging import D
from gjdanawa_uploader.utils.crawling import (
    find_element,
    scroll,
    validate_listing_info,
    click_alert,
    scroll_until,
)
from gjdanawa_uploader.utils.elasticsearch.elasticsearch_manager import (
    ElasticSearchManager,
)
from gjdanawa_uploader.crawler.base_crawler import BaseCrawler


class M11stCrawler(BaseCrawler):
    """11번가 Crawler

    Pages:
        https://search.11st.co.kr/MW/search?searchKeyword=%25EB%2582%2598%25EC%259D%25B4%25ED%2582%25A4%2520%25ED%258E%2598%25EA%25B0%2580%25EC%2588%2598%25EC%258A%25A4%252041%2520%25EB%25B8%2594%25EB%25A3%25A8%25ED%2594%2584%25EB%25A6%25B0%25ED%258A%25B8&decSearchKeyword=%25EB%2582%2598%25EC%259D%25B4%25ED%2582%25A4%2520%25ED%258E%2598%25EA%25B0%2580%25EC%2588%2598%25EC%258A%25A4%252041%2520%25EB%25B8%2594%25EB%25A3%25A8%25ED%2594%2584%25EB%25A6%25B0%25ED%258A%25B8
    """

    marketplace: str = "m11st"
    product_name: str
    brand_name: str
    cfgs: dict
    chrome_option: str | None
    driver: webdriver.Chrome
    es_manager: ElasticSearchManager
    selectors: dict
    subinstance: object
    metadata: dict

    def _initialize_selectors(self, listing_url: str):
        """Get selectors based on the listing URL"""
        for selectors in self.metadata["reviews_selectors_grocery"]:
            if re.match(selectors["listing_url"], listing_url):
                # 1. Set selectors
                self.selectors = selectors
                match selectors["version"]:
                    case 1:
                        from gjdanawa_uploader.crawler.m11st import (
                            M11stCrawlerVersion1 as Version1,
                        )

                        cls = Version1
                    case 2:
                        from gjdanawa_uploader.crawler.m11st import (
                            M11stCrawlerVersion2 as Version2,
                        )

                        cls = Version2
                    case _:
                        raise ValueError(f"Invalid version: {selectors['version']}")

                # 2. Set subinstance
                self.subinstance = cls(**self.__dict__)
                return
        raise NotImplementedError(f"Selectors for {listing_url} is not implemented")

    @D
    def _extract_listings(self) -> list[dict]:
        """Extract listing information"""
        # 1. Load search page
        self._load_search_page(driver=self.driver)

        # 2. Get necessary listing elements
        listing_elems = scroll_until(
            self.driver,
            "div[class='l-grid l-grid--nobg'] > ul > li > div.c-card-item > a",
            self.cfgs["crawler"].n_listings,
        )

        # 3. Extract listings
        with ProgressBar():
            tasks = [
                delayed(self._extract_listing)(listing_elem)
                for listing_elem in listing_elems
            ]
            listing_infos = compute(*tasks, scheduler="threads")
            final_listing_infos = [info for info in listing_infos if info]

        # 4. Check the number of listings
        n_expected = len(listing_elems)
        n_extracted = len(final_listing_infos)
        if n_extracted != n_expected:
            print(
                f"[Failure] Some listings are not extracted: \n  - # extracted listings: {len(final_listing_infos)} \n  - # existing listings: {len(listing_elems)}"
            )
            print(traceback.format_exc())

        return final_listing_infos

    @validate_listing_info
    def _extract_listing(self, listing_elem: WebElement) -> dict:
        """Extract listing information from item element"""
        _item_info = find_element(listing_elem, "div.c-card-item__info > dl")
        promotion1 = find_element(_item_info, "div.c-flag-box > dd", astype=str)

        _listing_title = find_element(_item_info, "div.c-card-item__name")
        overseas = find_element(_listing_title, "dd > em", astype=str)
        listing_title = find_element(
            _listing_title, "dd", astype=str, removeprefix=overseas or ""
        )

        seller_name = find_element(
            _item_info,
            "div.c-card-item__brand > dd > span",
            astype=str,
            default=self.marketplace,
        )
        official_seller_badge = find_element(
            _item_info, "div.c-card-item__brand > dd > em", astype=str
        )

        # Fast skip if listing_title is None
        if listing_title is None:
            return {}

        _price_info = find_element(_item_info, "div.c-card-item__price-info")
        lowest_price_badge = find_element(
            _price_info, "dd.c-card-item__lowest > span > span", astype=str
        )

        _rate = find_element(_price_info, "dd.c-card-item__rate")
        discount_rate = find_element(_rate, "strong", astype=float, default=0)

        _price_special = find_element(_price_info, "dd.c-card-item__price-special")
        promotion2 = find_element(_price_special, "strong", astype=int)

        _price = find_element(_price_info, "dd.c-card-item__price")
        price = find_element(_price, "strong", astype=int)
        price_per_unit = find_element(
            _price_info, "dd.c-card-item__price-per", astype=str
        )

        _starrate = find_element(_item_info, "div.c-starrate")
        review_count = find_element(
            _starrate,
            "dd.c-starrate__review",
            astype=int,
            removeprefix="리뷰",
            default=0,
        )
        average_rating = find_element(
            _starrate,
            "dd.c-starrate__sati",
            astype=float,
            pattern=r"만족도 : (\d+)%",
            scale_factor=self.metadata["max_listing_rating"],
        )

        _delivery = find_element(_item_info, "div.c-card-item__delivery")
        delivery_fee = find_element(
            _delivery,
            "dd",
            removeprefix="배송비",
            removesuffix=self.metadata.currency,
            astype=int,
        )
        estimated_time_of_arrival = find_element(_delivery, "dd > em", astype=str)

        _item_thumb = find_element(listing_elem, "div.c-card-item__thumb > span")
        thumbnail_url = find_element(_item_thumb, "img", attribute="url")
        listing_url = listing_elem.get_attribute("href")

        # Update info
        info = self._initialize_listing_info()
        info.update(
            listing_title=listing_title,  # 상품명
            seller_name=seller_name,  # 판매자명
            review_count=review_count,  # 리뷰 수
            price=price,  # 가격
            thumbnail_url=thumbnail_url,  # 썸네일 URL
            listing_url=listing_url,  # 상품 URL
            optional={
                "average_rating": average_rating,  # 리뷰 평점
                "overseas": overseas,  # 해외 상품 뱃지
                "lowest_price_badge": lowest_price_badge,  # 최저가격
                "delivery_fee": delivery_fee,  # 배송비
                "discount_rate": discount_rate,  # 할인률
                "promotion1": promotion1,  # 프로모션 정보
                "promotion2": promotion2,  # 즉시할인가
                "price_per_unit": price_per_unit,  # 가격 단위
                "estimated_time_of_arrival": estimated_time_of_arrival,  # 예상 도착일 (ETA)
                "official_seller_badge": official_seller_badge,  # 공식 판매자 뱃지
            },
        )
        return info

    @D
    def _extract_reviews(self, listing_infos: list[dict]) -> list[dict]:
        """Extract reviews information"""
        review_infos = []
        for listing_info in listing_infos:
            if listing_info["review_count"] == 0:
                # Skip if there is no review
                dist_info = dict(ratings_distribution={}, options_distribution={})
                listing_info["optional"].update(dist_info)
                continue

            review_infos_in_listing = self._extract_reviews_of_listing(
                listing_info, self.driver
            )
            review_infos.extend(review_infos_in_listing)

        return review_infos

    @D
    def _extract_reviews_of_listing(
        self, listing_info: dict, driver: webdriver.Chrome
    ) -> list[dict]:
        """Extract reviews information from listing information"""
        review_infos = []
        listing_url = listing_info["listing_url"]

        # 1. Load the review page
        self._load_review_page(listing_url, driver)

        # 2. Rating information
        dist_info = self.subinstance._extract_distribution(listing_info)
        listing_info["optional"].update(dist_info)

        # 3. Extract review information
        try:
            # 3.1 Get necessary review elements
            review_elems_selector = self.selectors["review_elements"]
            review_elems = scroll_until(
                driver, review_elems_selector, self.cfgs["crawler"].n_reviews
            )

            # 3.2 Extract review information
            with ProgressBar():
                tasks = [
                    delayed(self.subinstance.extract_review)(review_elem, listing_info)
                    for review_elem in review_elems
                ]
                review_infos = compute(*tasks, scheduler="threads")
                final_review_infos = [info for info in review_infos if info]

            # 3.3 Check the number of reviews
            n_expected = min(
                listing_info["review_count"], self.cfgs["crawler"].n_reviews
            )
            n_extracted = len(final_review_infos)
            if n_extracted != n_expected:
                print(
                    f"[Failure] Some reviews are not extracted: \n  - # expected reviews: {n_expected} \n  - # extracted reviews: {n_extracted} \n  - url: {listing_info['listing_url']}"
                )
                print(traceback.format_exc())

            return final_review_infos
        except Exception as e:
            print(f"[Failure] Extract reviews from listing_url: {listing_url}")
            print(traceback.format_exc())
            print(e)
            return [{}]

    @D
    def _load_review_page(self, url: str, driver: webdriver.Chrome):
        """Load review page"""
        # TODO: fix too long stuck
        try:
            # 1. Load item page
            self._load_url(url, driver=driver)
            self._initialize_selectors(driver.current_url)

            # 2. Find review page redirection button and click
            scroll(driver, self.selectors["review_button"], click=True)

            # 3. Dismiss the alert (11st application installation popup)
            click_alert(driver, action="dismiss")
        except Exception as e:
            print(f"[Failure] Load review page: {url}")
            print(traceback.format_exc())
            print(e)


if __name__ == "__main__":
    # listing_title = "페가수스 41 블루프린트"
    # seller_name = "나이키"

    product_name = "퍼펙트휩"
    brand_name = "센카"

    crawler = M11stCrawler(product_name, brand_name, chrome_option="dev", reset_db=True)
    crawler.run()
