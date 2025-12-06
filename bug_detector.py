import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from datetime import datetime

from playwright.async_api import Page
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


class BugSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class BugType(str, Enum):
    BROKEN_IMAGE = "broken_image"
    BROKEN_LINK = "broken_link"
    CONSOLE_ERROR = "console_error"
    NETWORK_ERROR = "network_error"
    MISSING_ALT_TEXT = "missing_alt_text"
    FORM_VALIDATION_ERROR = "form_validation_error"
    PERFORMANCE_ISSUE = "performance_issue"
    SECURITY_ISSUE = "security_issue"
    LAYOUT_ISSUE = "layout_issue"
    MISSING_HEADING = "missing_heading"
    MISSING_LABEL = "missing_label"
    INSUFFICIENT_CONTRAST = "insufficient_contrast"
    JAVASCRIPT_ERROR = "javascript_error"


@dataclass
class BugReport:
    title: str
    severity: BugSeverity
    bug_type: BugType
    description: str
    page_url: str
    steps_to_reproduce: List[str]
    expected_behavior: str
    actual_behavior: str
    browser_info: Dict[str, str]
    screenshot_path: Optional[str] = None


class BugDetector:
    def __init__(self, page: Page, base_url: str, execution_id: str):
        self.page = page
        self.base_url = base_url
        self.execution_id = execution_id
        self.bugs: List[BugReport] = []
        self.console_logs: List[Dict[str, Any]] = []
        self.network_errors: List[Dict[str, Any]] = []

    async def setup_listeners(self):
        def on_console(msg):
            if msg.type in ("error", "warning"):
                self.console_logs.append(
                    {
                        "type": msg.type,
                        "text": msg.text,
                        "location": msg.location,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        def on_response(response):
            if response.status >= 400:
                self.network_errors.append(
                    {
                        "url": response.url,
                        "status": response.status,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        self.page.on("console", on_console)
        self.page.on("response", on_response)

    async def detect_broken_images(self) -> List[BugReport]:
        broken_images = await self.page.evaluate(
            """() => {
            const images = Array.from(document.querySelectorAll('img'));
            return images.map(img => ({
                src: img.src,
                alt: img.alt,
                width: img.naturalWidth,
                height: img.naturalHeight,
                complete: img.complete,
                currentSrc: img.currentSrc
            })).filter(img => !img.complete || img.width === 0 || img.height === 0);
        }"""
        )

        bugs = []
        for broken_img in broken_images:
            bug = BugReport(
                title=f"Broken Image: {broken_img['src']}",
                severity=BugSeverity.MEDIUM,
                bug_type=BugType.BROKEN_IMAGE,
                description=f"Image failed to load or has zero dimensions",
                page_url=self.page.url,
                steps_to_reproduce=["Navigate to page", "Observe images"],
                expected_behavior="All images should load and display properly",
                actual_behavior=f"Image at {broken_img['src']} did not load",
                browser_info={"browser": "chromium", "url": self.page.url},
                screenshot_path=None,
            )
            bugs.append(bug)

        return bugs

    async def detect_console_errors(self) -> List[BugReport]:
        bugs = []

        for log in self.console_logs:
            if log["type"] == "error":
                severity = BugSeverity.HIGH
            else:
                severity = BugSeverity.LOW

            bug = BugReport(
                title=f"Console {log['type'].upper()}: {log['text'][:50]}",
                severity=severity,
                bug_type=BugType.CONSOLE_ERROR,
                description=f"Console {log['type']} detected during page execution",
                page_url=self.page.url,
                steps_to_reproduce=["Navigate to page", "Check browser console"],
                expected_behavior="No console errors should appear",
                actual_behavior=log["text"],
                browser_info={
                    "browser": "chromium",
                    "url": self.page.url,
                    "location": str(log.get("location", {})),
                },
            )
            bugs.append(bug)

        return bugs

    async def detect_network_errors(self) -> List[BugReport]:
        bugs = []

        for error in self.network_errors:
            severity_map = {400: BugSeverity.MEDIUM, 404: BugSeverity.HIGH, 500: BugSeverity.CRITICAL}
            severity = severity_map.get(error["status"], BugSeverity.MEDIUM)

            bug = BugReport(
                title=f"Network Error {error['status']}: {error['url']}",
                severity=severity,
                bug_type=BugType.NETWORK_ERROR,
                description=f"Network request returned HTTP {error['status']}",
                page_url=self.page.url,
                steps_to_reproduce=["Navigate to page", "Check network tab"],
                expected_behavior=f"Request should return 2xx status code",
                actual_behavior=f"Request returned {error['status']} status code",
                browser_info={"browser": "chromium", "url": error["url"]},
            )
            bugs.append(bug)

        return bugs

    async def detect_accessibility_issues(self) -> List[BugReport]:
        violations = await self.page.evaluate(
            """() => {
            const issues = [];

            const images = document.querySelectorAll('img');
            images.forEach((img, idx) => {
                if (!img.alt || img.alt.trim() === '') {
                    issues.push({
                        type: 'missing_alt_text',
                        element: 'img',
                        index: idx,
                        html: img.outerHTML.substring(0, 100)
                    });
                }
            });

            const buttons = document.querySelectorAll('button');
            buttons.forEach((btn, idx) => {
                if (!btn.textContent.trim() && !btn.getAttribute('aria-label')) {
                    issues.push({
                        type: 'missing_button_text',
                        element: 'button',
                        index: idx,
                        html: btn.outerHTML.substring(0, 100)
                    });
                }
            });

            const inputs = document.querySelectorAll('input[type="text"], input[type="email"], textarea');
            inputs.forEach((input, idx) => {
                const label = input.id ? document.querySelector(`label[for="${input.id}"]`) : null;
                if (!label && !input.getAttribute('aria-label')) {
                    issues.push({
                        type: 'missing_label',
                        element: 'input',
                        index: idx,
                        html: input.outerHTML.substring(0, 100)
                    });
                }
            });

            const links = document.querySelectorAll('a');
            links.forEach((link, idx) => {
                if (!link.textContent.trim() && !link.getAttribute('aria-label')) {
                    issues.push({
                        type: 'missing_link_text',
                        element: 'a',
                        index: idx,
                        href: link.href
                    });
                }
            });

            return issues;
        }"""
        )

        bugs = []
        for violation in violations:
            bug = BugReport(
                title=f"Accessibility Issue: {violation['type']}",
                severity=BugSeverity.MEDIUM,
                bug_type=BugType.MISSING_ALT_TEXT if violation["type"] == "missing_alt_text" else BugType.MISSING_LABEL,
                description=f"WCAG violation detected: {violation['type']}",
                page_url=self.page.url,
                steps_to_reproduce=["Navigate to page", "Use screen reader"],
                expected_behavior="Page should be fully accessible",
                actual_behavior=f"{violation['type']} for element at index {violation.get('index', 'unknown')}",
                browser_info={"browser": "chromium", "url": self.page.url},
            )
            bugs.append(bug)

        return bugs

    async def detect_layout_issues(self) -> List[BugReport]:
        issues = await self.page.evaluate(
            """() => {
            const problems = [];

            const elements = document.querySelectorAll('*');
            elements.forEach((el, idx) => {
                const rect = el.getBoundingClientRect();

                if (rect.width === 0 || rect.height === 0) {
                    if (el.children.length > 0 && el.tagName !== 'SCRIPT' && el.tagName !== 'STYLE') {
                        problems.push({
                            type: 'zero_dimensions',
                            tagName: el.tagName,
                            index: idx,
                            computed: window.getComputedStyle(el).display
                        });
                    }
                }

                if (rect.top < 0 || rect.left < 0) {
                    if (el.clientHeight > 100 && el.clientWidth > 100) {
                        problems.push({
                            type: 'off_screen',
                            tagName: el.tagName,
                            top: rect.top,
                            left: rect.left
                        });
                    }
                }
            });

            return problems;
        }"""
        )

        bugs = []
        for issue in issues:
            bug = BugReport(
                title=f"Layout Issue: {issue['type']}",
                severity=BugSeverity.LOW,
                bug_type=BugType.LAYOUT_ISSUE,
                description=f"Layout problem detected: {issue['type']}",
                page_url=self.page.url,
                steps_to_reproduce=["Navigate to page", "Inspect layout"],
                expected_behavior="All elements should be properly positioned",
                actual_behavior=f"{issue['type']} for {issue['tagName']} element",
                browser_info={"browser": "chromium", "url": self.page.url},
            )
            bugs.append(bug)

        return bugs

    async def detect_missing_headings(self) -> List[BugReport]:
        issues = await self.page.evaluate(
            """() => {
            const problems = [];

            if (!document.querySelector('h1')) {
                problems.push({ type: 'no_h1' });
            }

            const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
            let lastLevel = 0;

            headings.forEach((h, idx) => {
                const currentLevel = parseInt(h.tagName[1]);
                if (currentLevel - lastLevel > 1) {
                    problems.push({
                        type: 'heading_skip',
                        from: lastLevel,
                        to: currentLevel,
                        index: idx
                    });
                }
                lastLevel = currentLevel;
            });

            return problems;
        }"""
        )

        bugs = []
        for issue in issues:
            bug = BugReport(
                title=f"Heading Issue: {issue['type']}",
                severity=BugSeverity.LOW,
                bug_type=BugType.MISSING_HEADING,
                description=f"Heading structure issue: {issue['type']}",
                page_url=self.page.url,
                steps_to_reproduce=["Navigate to page", "Check heading hierarchy"],
                expected_behavior="Page should have proper heading hierarchy",
                actual_behavior=f"Detected {issue['type']} in heading structure",
                browser_info={"browser": "chromium", "url": self.page.url},
            )
            bugs.append(bug)

        return bugs

    async def detect_all_bugs(self) -> List[BugReport]:
        await self.setup_listeners()
        await self.page.goto(self.base_url, wait_until="networkidle")
        await asyncio.sleep(2)

        all_bugs = []

        logger.info("Detecting broken images...")
        all_bugs.extend(await self.detect_broken_images())

        logger.info("Detecting accessibility issues...")
        all_bugs.extend(await self.detect_accessibility_issues())

        logger.info("Detecting layout issues...")
        all_bugs.extend(await self.detect_layout_issues())

        logger.info("Detecting missing headings...")
        all_bugs.extend(await self.detect_missing_headings())

        await asyncio.sleep(1)

        logger.info("Detecting console errors...")
        all_bugs.extend(await self.detect_console_errors())

        logger.info("Detecting network errors...")
        all_bugs.extend(await self.detect_network_errors())

        return all_bugs

    async def save_bugs_to_database(
        self, project_id: str, execution_id: str, bugs: List[BugReport]
    ):
        for bug in bugs:
            try:
                await supabase.table("bug_reports").insert(
                    {
                        "project_id": project_id,
                        "execution_id": execution_id,
                        "title": bug.title,
                        "description": bug.description,
                        "severity": bug.severity.value,
                        "bug_type": bug.bug_type.value,
                        "page_url": bug.page_url,
                        "steps_to_reproduce": json.dumps(bug.steps_to_reproduce),
                        "expected_behavior": bug.expected_behavior,
                        "actual_behavior": bug.actual_behavior,
                        "browser_info": bug.browser_info,
                        "status": "open",
                    }
                ).execute()
                logger.info(f"Saved bug: {bug.title}")
            except Exception as e:
                logger.error(f"Failed to save bug: {str(e)}")
