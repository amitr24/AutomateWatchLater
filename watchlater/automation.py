"""Selenium automation with explicit states and resilient selectors."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

WATCH_LATER_URL = "https://www.youtube.com/playlist?list=WL"


class RunState(str, Enum):
    CREATED = "created"
    PLAYLIST_OPEN = "playlist_open"
    PLAYBACK_STARTED = "playback_started"
    COMPLETE = "complete"


PLAY_SELECTORS = (
    ("css selector", "ytd-playlist-header-renderer a[href*='watch']"),
    ("css selector", "ytd-playlist-header-renderer button[aria-label*='Play']"),
    ("xpath", "//*[contains(@aria-label, 'Play all')]"),
)
SHUFFLE_SELECTORS = (
    ("css selector", "button[aria-label*='Shuffle']"),
    ("xpath", "//*[contains(@aria-label, 'Shuffle play')]"),
)


@dataclass(frozen=True)
class AutomationConfig:
    profile_directory: Path
    timeout_seconds: int = 20
    shuffle: bool = False
    headless: bool = False
    dry_run: bool = False


def selector_plan(shuffle: bool) -> tuple[tuple[str, str], ...]:
    """Return ordered selectors separately from browser side effects."""
    return SHUFFLE_SELECTORS if shuffle else PLAY_SELECTORS


class WatchLaterAutomation:
    def __init__(self, config: AutomationConfig, logger=None) -> None:
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.state = RunState.CREATED

    def _build_driver(self):
        from selenium import webdriver

        options = webdriver.ChromeOptions()
        options.add_argument(f"--user-data-dir={self.config.profile_directory}")
        options.add_experimental_option("detach", True)
        if self.config.headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-notifications")
        return webdriver.Chrome(options=options)

    def _find_first_clickable(self, driver):
        from selenium.webdriver.support import expected_conditions as conditions
        from selenium.webdriver.support.ui import WebDriverWait

        errors = []
        for strategy, selector in selector_plan(self.config.shuffle):
            try:
                return WebDriverWait(driver, self.config.timeout_seconds).until(
                    conditions.element_to_be_clickable((strategy, selector))
                )
            except Exception as exc:
                errors.append(f"{strategy}:{selector} ({type(exc).__name__})")
        raise RuntimeError("No playback control found: " + "; ".join(errors))

    def run(self) -> RunState:
        if self.config.dry_run:
            self.logger.info(
                "dry_run",
                extra={"url": WATCH_LATER_URL, "shuffle": self.config.shuffle},
            )
            return RunState.COMPLETE

        driver = self._build_driver()
        try:
            driver.get(WATCH_LATER_URL)
            self.state = RunState.PLAYLIST_OPEN
            if "accounts.google.com" in driver.current_url:
                raise RuntimeError(
                    "The selected Chrome profile is not signed in to YouTube"
                )
            self._find_first_clickable(driver).click()
            self.state = RunState.PLAYBACK_STARTED
            self.logger.info("playback_started")
            self.state = RunState.COMPLETE
            return self.state
        finally:
            if self.state not in {RunState.PLAYBACK_STARTED, RunState.COMPLETE}:
                driver.quit()
