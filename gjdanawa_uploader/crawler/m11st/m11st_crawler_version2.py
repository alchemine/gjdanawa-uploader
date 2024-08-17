"""11st Crawler"""

from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from gjdanawa_uploader.utils.crawling import (
    find_element,
    find_elements,
    click,
    validate_review_info,
)
from gjdanawa_uploader.crawler.m11st.m11st_crawler import M11stCrawler


class M11stCrawlerVersion2(M11stCrawler):
    """11번가 Crawler

    Pages:
        "^https://m.11st.co.kr/products/m/.+"
        https://m.11st.co.kr/products/m/6130343076?&trTypeCd=MAS51&trCtgrNo=950076&checkCtlgPrd=true
        https://m.11st.co.kr/products/m/1849811748?&trTypeCd=MAS77&trCtgrNo=950076&checkCtlgPrd=true
    """

    def __init__(self, *args, **kwargs):
        for key, val in kwargs.items():
            setattr(self, key, val)

    def _extract_distribution(self, listing_info: dict) -> dict:
        """Extract distribution information"""
        # 1. Check if the distribution information is available
        if listing_info["review_count"] == 0:
            return

        # 2. Click more button
        click(self.driver, "section#satisfyReviewTapWrap > div.satisfy_dtl > button")

        # 3. Extract information
        ratings_distribution = {}
        elems = find_elements(self.driver, "ul#scorePercentage > li")
        for elem in reversed(elems):
            rating, percentage = elem.text.split("\n")
            rating = int(rating.removesuffix("점"))
            percentage = float(percentage.removesuffix("%")) / 100
            ratings_distribution[rating] = percentage

        options_distribution = {}
        stat = find_element(self.driver, "dl#itemGraph")
        idx = 1
        while True:
            try:
                key = find_element(
                    stat, f"dt:nth-child({idx})", astype=str, allow_not_found=False
                )
                options_distribution[key] = {}
                options = find_element(stat, f"dd:nth-child({idx+1})", astype=str)
                options = options.split("\n")
                for i in range(0, len(options), 2):
                    option = options[i]
                    percentage = float(options[i + 1].removesuffix("%")) / 100
                    options_distribution[key][option] = percentage
                idx += 2
            except NoSuchElementException:
                break

        dist_info = dict(
            ratings_distribution=ratings_distribution,
            options_distribution=options_distribution,
        )
        return dist_info

    @validate_review_info
    def extract_review(self, review_elem: WebElement, listing_info: dict) -> dict:
        """Extract review information

        Note:
            Variables with prefix `_` are Selenium WebElement objects.
            Variables without prefix are extracted information.
        """
        # Reviewer ID
        reviewer_id = find_element(review_elem, ".reviewer_info_name dd", astype=str)

        # Reviewer badge
        reviewer_badge = find_element(review_elem, ".reviewer_info_sub dd", astype=str)

        # Fast skip if reviewer_id is None
        if reviewer_id is None:
            return {}

        # Rating
        rating = find_element(
            review_elem,
            ".reviewer_info_star .b_satisfy.per100",
            removeprefix="만족도",
            astype=float,
            scale_factor=self.metadata["max_review_rating"],
        )

        # Summary
        summary = {}
        simple_review_elems = find_elements(review_elem, ".reviewer_info_simple dd")
        for elem in simple_review_elems:
            key = find_element(elem, "strong", By.TAG_NAME, astype=str)
            value = elem.text.removeprefix(key).strip()
            summary[key] = value

        # Options
        options = {}
        option_elems = find_elements(review_elem, ".c-personal-info__item")
        for elem in option_elems:
            key = find_element(elem, ".c-personal-info__title", astype=str)
            value = find_element(elem, ".c-personal-info__lock", astype=str)
            if value is None:
                value = elem.text.removeprefix(key).strip()
            options[key] = value

        # Review Content
        content = find_element(review_elem, ".con_wrp .con", astype=str)

        # Review Date
        date = find_element(
            review_elem, ".reviewer_info_sub .date", dt_format="%Y.%m.%d"
        )

        # Image URL
        # NOTE: Only the first image is extracted
        image_url = find_element(
            review_elem, "ul.photo > li > a > img", attribute="url"
        )
        video_url = find_element(
            review_elem, "ul.photo > li > a:has(span.mov)", attribute="url"
        )

        # Upvotes
        upvotes = find_element(review_elem, ".opinion .count", astype=int)

        info = self._initialize_review_info(listing_info)
        info.update(
            dict(
                reviewer_id=reviewer_id,
                rating=rating,
                content=content,
                date=date,
                optional={
                    "summary": summary,
                    "options": options,
                    "upvotes": upvotes,
                    "reviewer_badge": reviewer_badge,
                    "image_url": image_url,
                    "video_url": video_url,
                },
            )
        )
        return info
