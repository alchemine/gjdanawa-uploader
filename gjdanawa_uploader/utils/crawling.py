"""Crawling utilities"""

import re
import random
from time import sleep, perf_counter
from functools import wraps
from datetime import datetime
from typing import Literal

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import (
    InvalidSelectorException,
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException,
)

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

from gjdanawa_uploader.core.depth_logging import D
from gjdanawa_uploader.configs import CFG_CRAWLER


##################################################
# Chrome driver
# - Reference
#   - https://github.com/solver-ai/pop-data-pipeline/blob/main/modules/utils.py
##################################################

USER_AGENT_LIST = [
    # Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36",
    "Mozilla/5.0 (Windows NT 5.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.116 Safari/537.36",
]
BY_CSS_SELECTOR = By.CSS_SELECTOR
FREE_WORDS = CFG_CRAWLER.free_words
INFINITY = 1_000_000_000
TIMEOUT = 2
MINIMUM_SLEEP = 0.5
SLEEP = 1


class DriverContextManager:
    """Driver context manager"""

    def __init__(self, option: str | None = None):
        self.option = option

    def __enter__(self):
        self.driver = get_chrome_driver(self.option)
        return self

    def __exit__(self, *exc):
        self.driver.close()
        return False


class ElementNotFoundException(Exception):
    def __init__(self, url: str, selector: str, message: str = None):
        self.url = url
        self.selector = selector
        if message:
            self.message = message
        else:
            self.message = f"[Failure] Element not found:\n  - url: {url}\n  - CSS selector: {selector}"
        super().__init__(self.message)


def get_random_agent() -> str:
    return random.choice(USER_AGENT_LIST)


def get_chrome_options() -> webdriver.ChromeOptions:
    """Get anonymous chrome options"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument(f"user-agent={get_random_agent()}")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    # options.add_argument("--single-process")
    # options.add_argument("--disable-setuid-sandbox")
    return options


# def get_chrome_options() -> webdriver.ChromeOptions:
#     """Get anonymous chrome options"""
#     options = webdriver.ChromeOptions()
#     options.add_argument(f"user-agent={get_random_agent()}")
#     options.add_argument("--headless")
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     options.add_argument("--single-process")
#     options.add_argument("--ignore-certificate-errors")
#     options.add_argument("--ignore-ssl-errors")
#     options.add_argument("--disable-setuid-sandbox")
#     options.add_argument("--disable-gpu")
#     return options


def get_dev_chrome_options() -> webdriver.ChromeOptions:
    """Get anonymous chrome options"""
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument(f"user-agent={get_random_agent()}")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    # options.add_argument("--single-process")
    # options.add_argument("--disable-setuid-sandbox")
    return options


def get_chrome_driver(option: str | None = None) -> webdriver.Chrome:
    """Get singleton anonymous chrome driver"""
    if option is None:
        chrome_options = get_chrome_options()
    elif option == "dev":
        chrome_options = get_dev_chrome_options()
    else:
        raise ValueError(f"Invalid option: {option}")
    return webdriver.Chrome(options=chrome_options)


def wait_until_ready(sleep_after: float = SLEEP):
    """Wait until the page is loaded"""
    # TODO: unexpected alert open
    # WebDriverWait(driver, 2).until(
    #     lambda d: d.execute_script("return document.readyState") == "complete"
    # )
    sleep(sleep_after)


def load_url(driver: webdriver.Chrome, url: str):
    """Wait for the page to be loaded"""
    driver.get(url)
    wait_until_ready()


def click_alert(driver: webdriver.Chrome, action: str):
    """Click the alert window"""
    # 1. Handle the alert window
    # WebDriverWait(driver, 2).until(EC.alert_is_present())
    wait_until_ready()
    if action == "accept":
        driver.switch_to.alert.accept()
    elif action == "dismiss":
        driver.switch_to.alert.dismiss()
    else:
        raise ValueError(f"Invalid action: {action}")
    wait_until_ready()


def send_keys(driver: webdriver.Chrome, selector: str, value: str, enter: bool = False):
    """Send keys to the element by CSS selector"""
    element = find_element(driver, selector)
    element.send_keys(value)
    if enter:
        element.send_keys(Keys.RETURN)
    wait_until_ready()


def click(
    driver: webdriver.Chrome,
    selector: str = "",
    element: WebElement | None = None,
    sleep_after: float = SLEEP,
    timeout: float = TIMEOUT,
):
    """Click the element by CSS selector"""
    if element:
        try:
            element.click()
        except ElementClickInterceptedException:
            # Element is not visible
            driver.execute_script("arguments[0].click();", element)
    else:
        driver.execute_script(
            "arguments[0].click();",
            WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            ),
        )
    wait_until_ready(sleep_after)


def scroll(
    driver: webdriver.Chrome,
    selector: str,
    timeout: float = TIMEOUT,
    sleep_after: float = MINIMUM_SLEEP,
):
    """Scroll down to the bottom of the page"""
    driver.execute_script(
        "arguments[0].scrollIntoView(true);",
        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
        ),
    )
    wait_until_ready(sleep_after)


def goto_next_page(
    driver: webdriver.Chrome,
    cur_page: int,
    page_button_selector: str,
    view_more_page_button_selector: str = "",
    sleep_after: float = SLEEP,
) -> dict:
    """Go to the next page"""
    next_page = cur_page + 1
    try:
        click(
            driver,
            selector=page_button_selector.format(page=next_page),
            sleep_after=sleep_after,
        )
    except TimeoutException:
        if view_more_page_button_selector:
            try:
                click(
                    driver,
                    selector=view_more_page_button_selector,
                    sleep_after=sleep_after,
                )
            except TimeoutException:
                print(f"End of pages: {cur_page} with url: {driver.current_url}")
                return dict()

    return dict(page=next_page)


def scroll_until(
    driver: webdriver.Chrome,
    target_selector: str = "",
    view_more_button_selector: str = "",
    view_more_button_element: WebElement | None = None,
    n_elems: int = INFINITY,
    sleep_after: float = MINIMUM_SLEEP,
) -> list[WebElement]:
    """Scroll until the number of elements is satisfied"""
    if n_elems == -1:
        n_elems = INFINITY

    last_n_visible_elems = 0
    while True:
        try:
            visible_elems = find_elements(driver, target_selector)
            n_visible_elems = len(visible_elems)
            elems = visible_elems[:n_elems]

            print(f"# of visible elements: {n_visible_elems}, target: {n_elems}")
            if n_visible_elems == 0:
                # 1. If no element is found, stop
                raise ElementNotFoundException(driver.current_url, target_selector)
            elif n_visible_elems == last_n_visible_elems:
                # 2. If the number of visible elements is not changed, stop
                return elems
            elif n_visible_elems < n_elems:
                # 3. If the number of visible elements is less than n_elems, scroll down
                last_n_visible_elems = n_visible_elems
                if view_more_button_selector or view_more_button_element:
                    # 3.1 There is a button to load more elements
                    click(
                        driver,
                        selector=view_more_button_selector,
                        element=view_more_button_element,
                        sleep_after=sleep_after,
                    )
                else:
                    # 3.2 There is not a button to load more elements
                    scroll(driver, target_selector)
            else:
                # 4. If the number of visible elements is satisfied, return the elements
                return elems
        except TimeoutException:
            print(
                f"End of elements: found {n_visible_elems} elements (target: {n_elems})"
            )
            return elems


def get_css_selector(
    element: WebElement, log: bool = False, n_tags: int | None = None
) -> str:
    """Get the CSS selector of the given element"""
    path = []
    current = element

    while True:
        tag = current.tag_name
        id: str = current.get_attribute("id")
        class_: str = current.get_attribute("class")

        if id:
            path.append(f"{tag}#{id}")
        elif class_:
            classes = class_.split()
            if len(classes) == 1:
                path.append(f"{tag}.{class_}")
            else:
                path.append(f"{tag}[class='{class_}']")
        else:
            # Element without id or class
            path.append(tag)

        # 부모 요소로 이동
        try:
            current = current.find_element(By.XPATH, "..")
        except InvalidSelectorException:
            break

    selected_path = path[:n_tags] if n_tags else path
    css_selector = " > ".join(reversed(selected_path))
    if log:
        print(f"CSS Selector: {css_selector}")

    return css_selector


def silent_find(fn: callable) -> callable:
    """Ignore errors."""

    @wraps(fn)
    def _fn(*args, **kwargs):
        try:
            rst = fn(*args, **kwargs)
        except (
            NoSuchElementException,
            ElementNotFoundException,
            InvalidSelectorException,
        ):
            if kwargs.get("allow_not_found", True):
                default = kwargs.get("default")
                # print(f"[Warning] find_element() returns default value: {default}")
                rst = default
            else:
                raise ElementNotFoundException(
                    url=kwargs["src"].current_url, selector=kwargs["value"]
                )

        return rst

    return _fn


def select(driver: webdriver.Chrome, selector: str, value: str):
    select = find_element(driver, selector)
    options = find_elements(select, "option")
    for option in options:
        if option.text == value:
            option.click()
            break


@silent_find
def find_element(
    src: webdriver.Chrome | WebElement | None,
    value: str = "",
    by: str = By.CSS_SELECTOR,
    target_text: str = "",
    tag_name: str = "",
    attribute: str = "element",
    astype: type | None = None,
    process: bool = True,
    removeprefix: str = "",
    removesuffix: str = "",
    pattern: str = "",
    dt_format: str = None,
    scale_factor: float = 1,
    n_tags: int | None = None,
    default: str | int | float | None = None,  # used in decorator
    allow_not_found: bool = True,  # used in decorator
    log_selector: bool = False,  # used in decorator
) -> WebElement | str | int | float | list[dict] | None:
    """Find element by CSS selector"""
    # Filter with target text
    if target_text:
        elems = src.find_elements(By.XPATH, f"//*[contains(text(), '{target_text}')]")

        # Filter with tag name
        if tag_name:
            elems = [e for e in elems if e.text and e.tag_name == tag_name]
        else:
            elems = [e for e in elems if e.text]

        if len(elems) > 1:
            cands = []
            for idx, elem in enumerate(elems):
                info = {
                    "text": elem.text,
                    "target_text": target_text,
                    "selector": get_css_selector(elem, n_tags=n_tags),
                    "element": elem,
                }
                cands.append(info)
                print(
                    f"Element with target_text({target_text}) [{idx}]: \n  - text: {info['text']} \n  - selector: {info['selector']}"
                )
            return cands
        elif len(elems) == 1:
            valid_elem = elems[0]
            return valid_elem
        else:
            print(
                f"[Failure] No valid element found with target_text: {target_text} with tag_name: {tag_name}"
            )
            return

    # 1. Filter using :has()
    if matches := re.search(r"^(.+):has\(([a-z])\)$", value):
        # 1.1 Filter using :has()
        raw_value, sub_tag = matches.groups()
        value = f"{raw_value} > {sub_tag}"
        elem = src.find_element(by, value)
        elem = elem.find_element(By.XPATH, "..")
    else:
        # 1.2 Find element using CSS selector
        elem = src.find_element(by, value)

    # 2. Filter attribute
    use_text = astype or not process or pattern or dt_format
    if use_text:
        text = elem.text
    else:
        match attribute:
            case "element":
                return elem
            case "url":
                for attr in ("href", "src"):
                    if url := elem.get_attribute(attr):
                        return url
                return
            case _:
                return elem.get_attribute(attribute)

    # 3. Process text
    text = text.strip()
    if process:
        text = text.replace(",", "")  # 10,000원 -> 10000원
    if pattern:
        if matches := re.search(pattern, text):
            text = matches.group(1)
    else:
        removeprefix = removeprefix or ""
        removesuffix = removesuffix or ""
        text = text.removeprefix(removeprefix)
        text = text.removesuffix(removesuffix)
    text = text.strip()

    # 4. Cast type
    if dt_format:
        result = datetime.strptime(text, dt_format).isoformat()
    elif astype in (int, float):
        # Convert free words(e.g. 무료) to 0
        if any(word in text for word in FREE_WORDS):
            text = 0
        result = float(text)
        result /= scale_factor
        result = astype(result)
    else:
        result = astype(text)

    return result


def find_elements(
    src: webdriver.Chrome | WebElement | None,
    value: str,
    by: str = By.CSS_SELECTOR,
) -> list[WebElement]:
    """Find elements by CSS selector"""
    if matches := re.search(r"^(.+):has\(([a-z])\)$", value):
        # 1.1 Filter using_ :has()
        raw_value, sub_tag = matches.groups()
        value = f"{raw_value} > {sub_tag}"
        elems = src.find_elements(by, value)
        elems = [elem.findelement(By.XPATH, "..") for elem in elems]
    else:
        # 1.2 Find element using CSS selector
        elems = src.find_elements(by, value)

    return elems


def get_option_values(
    driver: webdriver.Chrome,
    selector: str,
    except_first: bool = False,
    except_str: str = "",
):
    """Get option values from the select element"""
    options = find_elements(driver, f"{selector} > option")
    values = [option.text for option in options]
    if except_first:
        values = values[1:]
    if except_str:
        values = [value for value in values if value != except_str]
    return values


if __name__ == "__main__":
    DRIVER = get_chrome_driver()
    DRIVER.get("https://www.google.com")
    page_source = DRIVER.page_source
    print(page_source)
