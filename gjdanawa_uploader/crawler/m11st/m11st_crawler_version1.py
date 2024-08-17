"""11st Crawler"""

import re
import traceback

from selenium.webdriver.remote.webelement import WebElement

from gjdanawa_uploader.core.depth_logging import D
from gjdanawa_uploader.utils.crawling import (
    find_element,
    find_elements,
    validate_review_info,
    click,
)
from gjdanawa_uploader.crawler.m11st import M11stCrawler


class M11stCrawlerVersion1(M11stCrawler):
    """11번가 Crawler

    Pages:
        "^https://m.11st.co.kr/products/ma/.+"
        https://action.adoffice.11st.co.kr/act/click/v1/landing/clickdata/compress?clickData=Y4U76FvyNSp_X3H4vqmgEk-a2HPoy0Iw8LBpksSZaeSIMAPON34tZsJoOzLxgeTDf9u4OymMlRVq3_l1RSfNpCprknqUu135U-2zcgIKDb905xnCdXKruV8L9zUljy1k6kErM5Y6UqPcHJrr6IKXbzuM8-ySXirm_5pW1C_nuIsh8lgfvtsrCheaKKCKUMXRlRc__9CjC8co0L0bwTIs7Unzf7eRSc568kTIbRgsIJX6NYH8-szORGUShDBP3KZsMtkaQkiIvANBxXx2oQM-eIBRXdjXwQIHm72W0mLJcwMH19k0RbB3vaM3HYo4QvcQ1Ap6sdcuWCsuZyhOaxeT6Zh-FZ-m9lLmc2MvJLcMu8mvv-h_gUuwlYedl3KdIdVvjuyUiOnEig3YdEyXC2Ab9aLe6lsebRiXlodJfN28glnSBZWunRLTJHdvh6CxPu1Pnz5IMxMHsW0z8Yfd8R6pHjNMM_-8IhDMFkGSXbS72bG5tbIs8e548RgZh__YutbKOTjJQ9xWTX48w3kQ4Jv2hLirjstMkyHFiQ3nFUiuMa2wmkeqBuZOdYeICFO_C4h9vfJNqVqcjGuFN-pMW9d4yIj4CV4_GSLKLNdaQQ1Qfy4SdxUR7RHHe9S9ty6rRehtYDgNVWZ-VaMqrZnGfDVhRdEj5AdamjLPUCAnaa55p8wwaqAa9W1jDomFWX0FJ_xSe-NhDDrndAQhMk16S0TqxgoLEsGeDKmk8dcc7duNlP1dRG2_L3vR12frMx3Tt4yVh4L1uq3W0wJSfXTaHxcve9TgvnSkM_OiNDm-1472PBXHCCZRtnsiVJzNj8zeicoqQz_uCCY11sVm5X7XEmsXXCnMEyuqpW1uhiURq5zgs0gE4-BvyivsZfvIGmpKjj2JDj398BhipYA7Wc7UqN7y0iBSnOj5LOUnFaxuBLrKyGv5Ie6SEGFQieuH_WcfwmYk4jBdozxTiLzaRZPQ25czxdI2S8JHv1ozVmG-jiRqylguGjrbZwn2_mE_C8La4z4urhbqmzl7d-IKgmYaCJM-BC6XI7Of3ZEBTQ8muFyIlvMEExauL4MgNlyWECZJR5QzYq3MQBEAjz9CroGctyQUu3et3mP09wMmRa9n_5xtf_EY-9DGu-ujuWmu8YXf52BczgW7y6ivXrGrWXxyTT9AIw&redirect=%2F%2Fm.11st.co.kr%2Fproducts%2Fm%2F5802041697%3F%26trTypeCd%3DMAS24%26trCtgrNo%3D950076

    """

    def __init__(self, *args, **kwargs):
        for key, val in kwargs.items():
            setattr(self, key, val)

    @D
    def _extract_distribution(self, listing_info: dict) -> dict:
        """Extract distribution information"""
        default_result = dict(ratings_distribution={}, options_distribution={})

        try:
            # 1. Check if the distribution information is available
            if listing_info["review_count"] == 0:
                return default_result

            # 2. Click more button
            try:
                button_selector = "div#wrap > section#cts > div.c-tabpanel.active > div:nth-child(2) > div.l-grid__row > button"
                click(self.driver, button_selector)
            except Exception as e:
                # NOTE: The button might not exist
                # https://m.11st.co.kr/products/ma/5801468296?&trTypeCd=MAS24&trCtgrNo=950076
                pass

            # 3. Extract information
            elems = find_elements(
                self.driver,
                "div#wrap > section#cts > div.c-tabpanel.active > div:nth-child(2) > div.l-grid__row > ul.c-contents-review__point > li > div > ul > li",
            )

            ratings_distribution = {}
            for elem in reversed(elems):
                pattern = "([1-5])점 리뷰 (\d+)개"
                score, count = map(int, re.search(pattern, elem.text).groups())
                ratings_distribution[score] = count

            options_distribution = {}
            stats = find_elements(
                self.driver,
                "div#wrap > section#cts > div.c-tabpanel.active > div:nth-child(2) > div.l-grid__row > dl.c-contents-review__stat > div.c-stat",
            )
            for stat in stats:
                key = find_element(stat, "dt", astype=str)
                options_distribution[key] = {}
                options = find_elements(stat, "dd.c-stat__detail > ul > li")
                for _option in options:
                    option, percentage = _option.text.split("\n")
                    percentage = float(percentage.removesuffix("%")) / 100
                    options_distribution[key][option] = percentage

            dist_info = dict(
                ratings_distribution=ratings_distribution,
                options_distribution=options_distribution,
            )
            return dist_info
        except Exception as e:
            print(
                f"[Failure] Distribution extraction: \n  - url: {self.driver.current_url} \n  - selector: {button_selector}"
            )
            print(traceback.format_exc())
            print(e)
            return default_result

    @validate_review_info
    def extract_review(self, review_elem: WebElement, listing_info: dict) -> dict:
        """Extract review information

        Note:
            Variables with prefix `_` are Selenium WebElement objects.
            Variables without prefix are extracted information.
        """
        _profile = find_element(review_elem, "header > div.c-profile")
        reviewer_id = find_element(_profile, "[class='c-profile__name']", astype=str)

        # Fast skip if reviewer_id is None
        if reviewer_id is None:
            return {}

        reviewer_badge = find_element(
            _profile, "[class='c-profile__other']", astype=str
        )
        rating = find_element(
            review_elem,
            "strong.c-starrate__review",
            astype=float,
            scale_factor=self.metadata["max_review_rating"],
        )

        summary = {}
        _sumups = find_elements(review_elem, "ul.c-card-review__sumup > li")
        for elem in _sumups:
            key = find_element(elem, "em", astype=str)
            value = find_element(elem, "span", astype=str)
            summary[key] = value

        options = {}
        for elem in find_elements(review_elem, "ul.c-personal-info > li"):
            key = find_element(elem, "strong", astype=str)
            if label := find_element(elem, "span", astype=str):
                value = label
            else:
                value = elem.text.removeprefix(key).strip()
            options[key] = value

        content = find_element(review_elem, "p.c-card-review__text", astype=str)
        date = find_element(
            review_elem,
            "div.c-card-review__other",
            dt_format="%Y.%m.%d",
        )

        # NOTE: Only the first image is extracted
        # TODO: video
        image_url = find_element(review_elem, "img", attribute="url")

        # TODO: integrate prefix, suffix finding
        upvotes = find_element(find_element(review_elem, "footer"), "em", astype=int)

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
                    "video_url": None,
                },
            )
        )
        return info
