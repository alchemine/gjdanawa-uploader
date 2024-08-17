"""11st Crawler"""

import re
import traceback
from datetime import datetime

from dask import delayed, compute

from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import (
    TimeoutException,
)

from gjdanawa_uploader.core.depth_logging import D
from gjdanawa_uploader.utils.crawling import (
    INFINITY,
    MINIMUM_SLEEP,
    ElementNotFoundException,
    find_element,
    find_elements,
    validate_listing_info,
    validate_review_info,
    load_url,
    scroll,
    click,
    scroll_until,
    extract_price_per_unit,
    goto_next_page,
)
from gjdanawa_uploader.crawler.base_crawler import BaseCrawler
from gjdanawa_uploader.utils.elasticsearch.elasticsearch_manager import (
    ElasticSearchManager,
)


class DanawaCrawler(BaseCrawler):
    """다나와 Crawler

    Pages:
        https://search.danawa.com/mobile/dsearch.php?keyword=%EC%84%BC%EC%B9%B4+%ED%8D%BC%ED%8E%99%ED%8A%B8%ED%9C%A9
        https://search.danawa.com/mobile/dsearch.php?keyword=%EC%84%BC%EC%B9%B4+%ED%8D%BC%ED%8E%99%ED%8A%B8%ED%9C%A9&keywordType=1&checkedInfo=N&boost=true&adult=0&page=1&sort=saveDESC&list=list&volumeType=va&addDelivery=N&coupangMemberSort=N&coupangMemberSortLayerType=&shop=TP40F%7CEE128%7CEE715%7CTH201%7CEE309%7CTN118%7CED901%7CEE311%7CTSB275%7CED903&defaultUICategoryCode=18222863&defaultPhysicsCategoryCode=9875%7C36919%7C58553%7C0&defaultVmTab=36&defaultVaTab=9726&priceUnitSort=Y&priceUnitSortOrder=A
    """

    marketplace: str = "danawa"
    product_name: str
    brand_name: str
    query: str
    session_id: str
    current_time: datetime
    cfgs: dict
    chrome_option: str | None
    driver: webdriver.Chrome
    es_manager: ElasticSearchManager
    metadata: dict
    search_url: str
    reviews_selectors: dict
    subinstance: object

    @D
    def _extract(
        self, n_listings: int | None = None, n_reviews: int | None = None
    ) -> dict:
        """Extract information from the crawler"""
        # 1. Set n_listings, n_reviews
        if n_listings is None:
            n_listings = self.cfgs["crawler"]["n_listings"]
        elif n_listings == -1:
            n_listings = INFINITY

        if n_reviews is None:
            n_reviews = self.cfgs["crawler"]["n_reviews"]
        elif n_reviews == -1:
            n_reviews = INFINITY

        # 2. Load search page
        load_url(self.driver, self.search_url)

        # 3. Extract listing information
        listing_infos = self._extract_listings(n_listings)

        # 4. Extract review information
        review_infos = self._extract_reviews(listing_infos, n_reviews)

        return dict(
            listings=listing_infos,
            reviews=review_infos,
        )

    @D
    def _extract_listings(self, n_listings: int) -> list[dict]:
        """Get listing information"""
        cur_page = 1
        listing_infos_pages = []
        while True:
            # 1. Extract listing elements
            listing_elems = self._get_listing_elements_in_page()

            # 2. Extract information from element
            tasks = [delayed(self._extract_listing)(elem) for elem in listing_elems]
            listing_infos = list(compute(*tasks, scheduler="threads"))
            listing_infos_pages.extend(listing_infos)

            if len(listing_infos_pages) >= n_listings:
                # 3.1 If the number of listings is satisfied, stop
                break
            else:
                # 3.2 If the number of listings is not satisfied, go to the next page
                result = goto_next_page(
                    self.driver,
                    cur_page=cur_page,
                    page_button_selector=self.metadata.listings_selectors.page_button,
                    view_more_page_button_selector=self.metadata.listings_selectors.view_more_page_button,
                )
                if result:
                    # 4.1 If there is a next page, go to the next page
                    cur_page = result["page"]
                else:
                    # 4.2 If there is no next page, stop
                    break

        return listing_infos_pages[:n_listings]

    @D
    def _get_listing_elements_in_page(self) -> list[WebElement]:
        """Get listing elements"""
        # 1. Get elements
        listing_elems = scroll_until(
            self.driver,
            target_selector=self.metadata.listings_selectors.listings,
            view_more_button_selector=self.metadata.listings_selectors.get(
                "view_more_button"
            ),
            n_elems=self.cfgs["crawler"]["n_listings"],
        )

        # 2. Filtering (optional)
        listing_elems = [elem for elem in listing_elems if elem.text]
        return listing_elems

    @validate_listing_info
    def _extract_listing(self, listing_elem: WebElement) -> dict:
        """Extract listing information from listing element"""
        # 1. Extract information
        listing_title = find_element(listing_elem, "span.goods-list__title", astype=str)
        seller_name = find_element(
            listing_elem, "div.goods-list__info img", attribute="alt"
        )
        if seller_name is None:
            markerplace = self.marketplace
            seller_name = "group"
            badges = ["lowest_price"]
        else:
            markerplace = seller_name
            badges = []

        price = find_element(listing_elem, "div.goods-list__price > em", astype=float)
        price_per_unit_text = find_element(
            listing_elem, "div.goods-list__sub", astype=str
        )
        price_per_unit = extract_price_per_unit(price_per_unit_text)

        average_rating = find_element(
            listing_elem,
            "div.goods-list__review > span.point",
            astype=float,
            scale_factor=self.metadata.max_listing_rating,
        )
        review_count = find_element(
            listing_elem,
            "div.goods-list__review > span.count",
            astype=int,
            pattern="\((\d+)\)",
            default=0,
        )

        date = find_element(
            listing_elem,
            "span.goods-list__date",
            dt_format="%Y.%m.",
            removeprefix="등록월 ",
        )
        thumbnail_url = find_element(listing_elem, "span.thumb > img", attribute="url")
        listing_url = find_element(
            listing_elem, "div.goods-list__wrap > a", attribute="url"
        )

        info = self._initialize_listing_info()
        info.update(
            marketplace=markerplace,
            listing_title=listing_title,
            seller_name=seller_name,
            review_count=review_count,
            price=price,
            thumbnail_url=thumbnail_url,
            listing_url=listing_url,
            date=date,
            optional={
                "average_rating": average_rating,
                "price_per_unit": price_per_unit,
            },
        )
        self._append_badges(info, badges)
        return info

    @D
    def _extract_reviews(self, listing_infos: list[dict], n_reviews: int) -> list[dict]:
        """Extract review information"""
        # 1. Extract review information
        review_infos = []
        for listing_info in filter(lambda x: x["review_count"], listing_infos):
            review_infos_in_listing = self._extract_reviews_of_listing(
                listing_info, n_reviews
            )
            review_infos.extend(review_infos_in_listing)

        return review_infos

    @D
    def _extract_reviews_of_listing(
        self, listing_info: dict, n_reviews: int
    ) -> list[dict]:
        """Extract reviews information from listing information"""
        review_infos = []
        listing_url = listing_info["listing_url"]

        try:
            # 1. Load the review page
            self._load_review_page(listing_url)

            # 2. Load distribution
            ratings_distribution = self._extract_ratings_dist()
            if ratings_distribution:
                listing_info["optional"]["ratings_distribution"] = ratings_distribution

            # 3. Extract review infos
            review_infos = self._get_review_infos(listing_info, n_reviews)

            # 4. Check the number of reviews
            n_expected = min(listing_info["review_count"], n_reviews)
            n_extracted = len(review_infos)
            if (n_expected != -1) and (n_extracted != n_expected):
                print(
                    f"[Failure] Some reviews are not extracted: \n  - # expected reviews: {n_expected} \n  - # extracted reviews: {n_extracted} \n  - url: {listing_info['listing_url']}"
                )
                print(traceback.format_exc())

            return review_infos
        except Exception as e:
            print(f"[Failure] Extract reviews from listing_url: {listing_url}")
            print(traceback.format_exc())
            print(e)
            return [{}]

    @D
    def _extract_ratings_dist(self) -> dict:
        """Extract ratings distribution"""
        selector = "#productBlog-opinion-mall-tabContent-container > div.new_mark_nums > div.right_nums_parea > ul > li"
        ratings_dist_elem = find_elements(self.driver, selector)
        ratings_distribution = {}
        for elem in ratings_dist_elem:
            rating = find_element(elem, "span.tit", astype=int, removesuffix="점")
            percent = find_element(elem, "span.percent", astype=float, removesuffix="%")
            ratings_distribution[rating] = percent
        return ratings_distribution

    @D
    def _get_review_infos(self, listing_info: dict, n_reviews: int) -> list[dict]:
        """Get review information"""
        target_selector = self.reviews_selectors.reviews
        # button_element = find_element(driver, target_text="펼쳐보기")  # multiples candidates
        button_selector = self.reviews_selectors.view_more_button

        cumulated_infos = []
        last_n_visible_elems = 0
        while True:
            try:
                visible_elems = find_elements(self.driver, target_selector)
                unseen_elems = visible_elems[last_n_visible_elems:]
                n_visible_elems = len(visible_elems)
                print(f"# visible elems: {n_visible_elems}, # target: {n_reviews}")

                tasks = [
                    delayed(self._extract_review)(elem, listing_info)
                    for elem in unseen_elems
                ]
                infos = list(compute(*tasks, scheduler="threads"))
                cumulated_infos.extend(infos)

                if n_visible_elems == 0:
                    # 1. If no element is found, stop
                    raise ElementNotFoundException(
                        self.driver.current_url, target_selector
                    )
                elif n_visible_elems == last_n_visible_elems:
                    # 2. If the number of visible elements is not changed, stop
                    break
                elif n_visible_elems < n_reviews:
                    # 3. If the number of visible elements is less than n_elems, scroll down
                    last_n_visible_elems = n_visible_elems
                    if button_selector:
                        # 3.1 There is a button to load more elements
                        click(
                            self.driver,
                            selector=button_selector,
                            sleep_after=0.2,
                        )
                    else:
                        # 3.2 There is not a button to load more elements
                        scroll(self.driver, target_selector)
                else:
                    # 4. If the number of visible elements is satisfied, return the elements
                    break
            except TimeoutException:
                print(
                    f"End of elements: found {n_visible_elems} elements (target: {n_reviews})"
                )
                break

        return cumulated_infos[:n_reviews]

    @validate_review_info
    def _extract_review(self, review_elem: WebElement, listing_info: dict) -> dict:
        """Extract review information from review element"""
        id = self._extract_review_id(review_elem)

        rating = find_element(
            review_elem,
            "div.star_mark_type1",
            astype=float,
            pattern=r"별 (\d)점",
            scale_factor=self.metadata.max_review_rating,
        )

        marketplace = find_element(
            review_elem, "span.best_mall_mall01 > img"
        ).get_attribute("alt")

        date = find_element(review_elem, "span.best_mall_date01", dt_format="%Y.%m.%d.")
        reviewer_id = find_element(review_elem, "span.best_mall_nic01", astype=str)
        content = find_element(review_elem, "p.txt_best_rvw", astype=str)

        selector = f"#productBlog-opinion-mall-list-image-item-1-{id}"
        image_url = find_element(self.driver, selector, attribute="url")

        info = self._initialize_review_info(listing_info)
        info.update(
            reviewer_id=reviewer_id,
            rating=rating,
            content=content,
            date=date,
            optional={
                "image_url": image_url,
            },
            marketplace=marketplace,
            seller_name=marketplace,  # danawa or group is not a seller
        )
        return info

    ####################################################################################################
    # Utility methods
    ####################################################################################################
    def _load_review_page(self, url: str):
        """Load review page"""
        # 1. Load item page
        load_url(self.driver, url)
        self._initialize_reviews_selectors(self.driver.current_url)

        # 2. Find review page redirection button and click
        button = find_element(self.driver, target_text="의견/리뷰", tag_name="a")
        click(self.driver, element=button, sleep_after=MINIMUM_SLEEP)

        button2 = find_element(self.driver, target_text="쇼핑몰 상품리뷰")
        click(self.driver, element=button2, sleep_after=MINIMUM_SLEEP)

    def _extract_review_id(self, element: WebElement) -> str:
        """Extract listing ID from item element"""
        pattern = "^productBlog-opinion-mall-list-listItem-(.*)$"
        id = re.search(pattern, element.get_attribute("id")).group(1)
        return id

    def _initialize_reviews_selectors(self, listing_url: str):
        """Get reviews selectors based on the listing URL"""
        for selectors in self.metadata["reviews_selectors_grocery"]:
            if re.match(selectors["listing_url"], listing_url):
                self.reviews_selectors = selectors
                self.subinstance = self
                return
        raise NotImplementedError(f"Selectors for {listing_url} is not implemented")


if __name__ == "__main__":
    # product_name = "페가수스 41 블루프린트"
    # brand_name = "나이키"

    # product_name = "퍼펙트휩"
    # product_name = "퍼펙트 휩 페이셜 워시"
    # brand_name = "센카"

    product_name = "트롬 스타일러"
    brand_name = "LG전자"
    session_id = "dummy"

    crawler = DanawaCrawler(product_name, brand_name, session_id)
    crawler.run()
