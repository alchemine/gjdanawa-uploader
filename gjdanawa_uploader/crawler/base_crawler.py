"""Base Crawler: superclass for all crawler classes"""

import traceback
from datetime import datetime
from abc import ABCMeta, abstractmethod
import uuid

from selenium import webdriver

from gjdanawa_uploader.core.depth_logging import D
from gjdanawa_uploader.configs import (
    CFG_CRAWLER,
    CFG_ES,
    METADATA,
    FIELD_DESCRIPTIONS,
)
from gjdanawa_uploader.utils.crawling import get_chrome_driver
from gjdanawa_uploader.utils.elasticsearch.elasticsearch_manager import (
    ElasticSearchManager,
)


class BaseCrawler(metaclass=ABCMeta):
    """Base Crawler"""

    marketplace: str
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

    def __init__(
        self,
        product_name: str,
        brand_name: str,
        session_id: str,
        chrome_option: str | None = None,
        es_manager: ElasticSearchManager | None = None,
        reset_db: bool = False,
    ):
        assert self.marketplace, "marketplace should be defined"
        self.product_name = product_name
        self.brand_name = brand_name
        self.query = self._get_search_query()
        self.session_id = session_id if session_id else str(uuid.uuid4())
        self.current_time = datetime.now().isoformat()
        self.cfgs = {
            "crawler": CFG_CRAWLER.marketplaces[self.marketplace],
            "es": CFG_ES,
        }
        self.chrome_option = chrome_option
        self.driver = get_chrome_driver(chrome_option)
        if es_manager is None:
            es_manager = ElasticSearchManager(reset=reset_db)
        self.es_manager = es_manager
        self.metadata = METADATA[self.marketplace]
        kwargs = {self.metadata["query"]: self.query}
        self.search_url = self.metadata["search_url"].format(**kwargs)

        # Update indices
        if reset_db:
            self._update_indices()

    def __del__(self):
        """Destructor"""
        self.driver.quit()

    @D
    def run(self, n_listings: int | None = None, n_reviews: int | None = None):
        """Run crawler"""
        # Extract and load listings and reviews
        infos = self._extract(n_listings, n_reviews)
        self._load(infos)
        self.driver.quit()
        return infos

    @D
    def _load(self, infos: dict):
        """Load listing and review information to Elasticsearch"""
        for key, data in infos.items():
            self.es_manager.insert_documents(data, index=self.cfgs["es"][key]["index"])

    ####################################################################################################
    # Abstract methods
    ####################################################################################################
    @abstractmethod
    def _extract(
        self, n_listings: int | None = None, n_reviews: int | None = None
    ) -> dict:
        """Extract information from the crawler"""
        raise NotImplementedError

    ####################################################################################################
    # Utility methods
    ####################################################################################################
    def _update_indices(self):
        """Update metadata, field descriptions indices"""
        # 1. Metadata
        index = CFG_ES.metadata.index
        document = self.metadata
        # query = {"query": {"term": {"marketplace.keyword": self.marketplace}}}

        # Remove and insert new metadata
        # self.es_manager.delete_documents(index, query)
        self.es_manager.insert_document(document, index)
        print(f"Index updated: {index}")

        # 2. Field descriptions
        index = CFG_ES.field_descriptions.index
        document = FIELD_DESCRIPTIONS

        # Remove and insert new metadata
        # self.es_manager.delete_documents(index)
        self.es_manager.insert_document(document, index)
        print(f"Index updated: {index}")

    def _get_search_query(self) -> str:
        """Get search query"""
        return f"{self.brand_name} {self.product_name}"

    def _initialize_listing_info(self) -> dict:
        """Initialize extracted listing information"""
        # Load placeholder
        keys = list(self.cfgs["es"]["listings"]["mappings"]["properties"])
        extracted_info = {key: None for key in keys}

        # Set common fields
        extracted_info["session_id"] = self.session_id
        extracted_info["marketplace"] = self.marketplace
        extracted_info["product_name"] = self.product_name
        extracted_info["brand_name"] = self.brand_name
        extracted_info["query"] = self.query
        extracted_info["updated_at"] = self.current_time
        extracted_info["optional"] = {}
        return extracted_info

    def _initialize_review_info(self, listing_info: dict) -> dict:
        """Initialize extracted review information"""
        # Load placeholder
        keys = list(self.cfgs["es"]["reviews"]["mappings"]["properties"])
        extracted_info = {key: None for key in keys}

        # Set common fields
        for key in (
            "session_id",
            "marketplace",
            "product_name",
            "brand_name",
            "query",
            "listing_title",
            "seller_name",
            "listing_url",
            "updated_at",
        ):
            extracted_info[key] = listing_info[key]
        extracted_info["optional"] = {}
        return extracted_info

    def _initialize_dist_info(self) -> dict:
        """Initialize distribution information"""
        # Load placeholder
        extracted_info = dict(ratings_distribution={}, options_distribution={})
        return extracted_info

    def _append_badges(self, info: dict, badges: list[str] | str):
        """Add badges to information"""
        if isinstance(badges, str):
            badges = [badges]
        if badges and ("badges" not in info["optional"]):
            info["optional"]["badges"] = []
        for badge in badges:
            info["optional"]["badges"].append(badge)

    def _raise_for_num_extracted(self, n_expected: int, n_extracted: int, id: str):
        if (n_expected != -1) and (n_extracted != n_expected):
            print(
                f"[Failure] Some {id} are not extracted: \n  - # expected {id}: {n_expected} \n  - # extracted {id}: {n_extracted}"
            )
            print(traceback.format_exc())
