from pathlib import Path

from watchlater.automation import (
    AutomationConfig,
    RunState,
    WatchLaterAutomation,
    selector_plan,
)


def test_dry_run_has_no_browser_dependency():
    automation = WatchLaterAutomation(
        AutomationConfig(profile_directory=Path("profile"), dry_run=True)
    )
    assert automation.run() == RunState.COMPLETE


def test_shuffle_uses_a_distinct_fallback_plan():
    assert selector_plan(True) != selector_plan(False)
    assert len(selector_plan(True)) >= 2
    assert len(selector_plan(False)) >= 2
