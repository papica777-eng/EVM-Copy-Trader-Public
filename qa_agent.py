import asyncio
import json
import time
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from abc import ABC, abstractmethod

import aiohttp
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


class TestType(str, Enum):
    FUNCTIONAL = "functional"
    PERFORMANCE = "performance"
    ACCESSIBILITY = "accessibility"
    VISUAL_REGRESSION = "visual_regression"
    BROKEN_LINKS = "broken_links"
    FORM_VALIDATION = "form_validation"
    SECURITY = "security"


class BugSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class TestStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class TestResult:
    status: TestStatus
    message: str
    duration_ms: int
    details: Dict[str, Any] = None
    error: Optional[str] = None


@dataclass
class BugReport:
    title: str
    severity: BugSeverity
    bug_type: str
    description: str
    page_url: str
    steps_to_reproduce: List[str]
    expected_behavior: str
    actual_behavior: str
    browser_info: Dict[str, str]


class BaseTestRunner(ABC):
    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url
        self.bugs = []

    @abstractmethod
    async def run(self) -> TestResult:
        pass

    def add_bug(self, bug: BugReport):
        self.bugs.append(bug)


class FunctionalTestRunner(BaseTestRunner):
    async def run(self) -> TestResult:
        try:
            start = time.time()
            await self.page.goto(self.base_url, wait_until="networkidle")

            elements_found = await self.page.query_selector_all("*")
            interactive_elements = await self.page.query_selector_all(
                "button, input, a, form, select, textarea"
            )

            duration = int((time.time() - start) * 1000)

            return TestResult(
                status=TestStatus.PASSED,
                message=f"Functional test completed. Found {len(interactive_elements)} interactive elements.",
                duration_ms=duration,
                details={
                    "total_elements": len(elements_found),
                    "interactive_elements": len(interactive_elements),
                    "page_loaded": True,
                },
            )
        except Exception as e:
            return TestResult(
                status=TestStatus.FAILED,
                message="Functional test failed",
                duration_ms=0,
                error=str(e),
            )


class PerformanceTestRunner(BaseTestRunner):
    async def run(self) -> TestResult:
        try:
            start = time.time()

            metrics = await self.page.evaluate(
                """() => {
                const perf = performance.getEntriesByType('navigation')[0];
                const paint = performance.getEntriesByType('paint');
                return {
                    domInteractive: perf.domInteractive,
                    domContentLoaded: perf.domContentLoadedEventEnd,
                    loadEventEnd: perf.loadEventEnd,
                    fcpTime: paint.find(p => p.name === 'first-contentful-paint')?.startTime || 0,
                    lcpTime: 0
                };
            }"""
            )

            resource_timing = await self.page.evaluate(
                """() => {
                const resources = performance.getEntriesByType('resource');
                return {
                    count: resources.length,
                    totalSize: resources.reduce((sum, r) => sum + (r.transferSize || 0), 0) / 1024,
                    failedRequests: resources.filter(r => !r.responseEnd).length
                };
            }"""
            )

            duration = int((time.time() - start) * 1000)

            thresholds_passed = metrics["loadEventEnd"] < 5000

            return TestResult(
                status=TestStatus.PASSED if thresholds_passed else TestStatus.WARNING,
                message="Performance test completed",
                duration_ms=duration,
                details={
                    "domContentLoaded": metrics["domContentLoaded"],
                    "loadEventEnd": metrics["loadEventEnd"],
                    "fcp": metrics["fcpTime"],
                    "resourceCount": resource_timing["count"],
                    "totalSizeKb": resource_timing["totalSize"],
                },
            )
        except Exception as e:
            return TestResult(
                status=TestStatus.FAILED,
                message="Performance test failed",
                duration_ms=0,
                error=str(e),
            )


class AccessibilityTestRunner(BaseTestRunner):
    async def run(self) -> TestResult:
        try:
            start = time.time()

            violations = await self.page.evaluate(
                """() => {
                const violations = [];

                const images = document.querySelectorAll('img');
                images.forEach(img => {
                    if (!img.alt || img.alt.trim() === '') {
                        violations.push({type: 'missing_alt_text', element: 'img'});
                    }
                });

                const buttons = document.querySelectorAll('button');
                buttons.forEach(btn => {
                    if (!btn.textContent.trim() && !btn.getAttribute('aria-label')) {
                        violations.push({type: 'missing_button_label', element: 'button'});
                    }
                });

                const labels = document.querySelectorAll('input');
                labels.forEach(input => {
                    if (!input.id || !document.querySelector(`label[for="${input.id}"]`)) {
                        violations.push({type: 'missing_form_label', element: 'input'});
                    }
                });

                const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
                let lastLevel = 0;
                headings.forEach(h => {
                    const currentLevel = parseInt(h.tagName[1]);
                    if (currentLevel - lastLevel > 1) {
                        violations.push({type: 'heading_level_skip', element: h.tagName});
                    }
                    lastLevel = currentLevel;
                });

                return violations;
            }"""
            )

            duration = int((time.time() - start) * 1000)

            severity = (
                TestStatus.FAILED if len(violations) > 5 else TestStatus.WARNING
                if len(violations) > 0
                else TestStatus.PASSED
            )

            return TestResult(
                status=severity,
                message=f"Accessibility test completed. Found {len(violations)} potential issues.",
                duration_ms=duration,
                details={"violations_count": len(violations), "violations": violations},
            )
        except Exception as e:
            return TestResult(
                status=TestStatus.FAILED,
                message="Accessibility test failed",
                duration_ms=0,
                error=str(e),
            )


class BrokenLinksTestRunner(BaseTestRunner):
    async def run(self) -> TestResult:
        try:
            start = time.time()

            links = await self.page.query_selector_all("a[href]")
            broken_links = []
            checked_urls = set()

            async with aiohttp.ClientSession() as session:
                for link in links:
                    href = await link.get_attribute("href")

                    if not href or href.startswith("#") or href.startswith("javascript:"):
                        continue

                    if href in checked_urls:
                        continue

                    checked_urls.add(href)

                    url = href if href.startswith("http") else self.base_url.rstrip("/") + "/" + href.lstrip("/")

                    try:
                        async with session.head(url, timeout=aiohttp.ClientTimeout(total=5), allow_redirects=True) as resp:
                            if resp.status >= 400:
                                broken_links.append({"url": href, "status": resp.status})
                    except Exception as e:
                        broken_links.append({"url": href, "error": str(e)})

            duration = int((time.time() - start) * 1000)

            severity = (
                TestStatus.FAILED if len(broken_links) > 3 else TestStatus.WARNING
                if len(broken_links) > 0
                else TestStatus.PASSED
            )

            return TestResult(
                status=severity,
                message=f"Broken links test completed. Found {len(broken_links)} broken links.",
                duration_ms=duration,
                details={"broken_links_count": len(broken_links), "broken_links": broken_links},
            )
        except Exception as e:
            return TestResult(
                status=TestStatus.FAILED,
                message="Broken links test failed",
                duration_ms=0,
                error=str(e),
            )


class FormValidationTestRunner(BaseTestRunner):
    async def run(self) -> TestResult:
        try:
            start = time.time()

            forms = await self.page.query_selector_all("form")
            form_issues = []

            for idx, form in enumerate(forms):
                inputs = await form.query_selector_all("input, textarea, select")

                has_submit = await form.query_selector("button[type='submit'], input[type='submit']")

                if not has_submit:
                    form_issues.append(
                        {
                            "form_index": idx,
                            "issue": "No submit button found",
                        }
                    )

                for input_elem in inputs:
                    input_type = await input_elem.get_attribute("type")
                    input_name = await input_elem.get_attribute("name")
                    is_required = await input_elem.get_attribute("required")

                    if is_required and not input_name:
                        form_issues.append(
                            {
                                "form_index": idx,
                                "issue": f"Required {input_type} input missing name attribute",
                            }
                        )

            duration = int((time.time() - start) * 1000)

            severity = (
                TestStatus.FAILED if len(form_issues) > 5 else TestStatus.WARNING
                if len(form_issues) > 0
                else TestStatus.PASSED
            )

            return TestResult(
                status=severity,
                message=f"Form validation test completed. Found {len(form_issues)} issues.",
                duration_ms=duration,
                details={"form_issues_count": len(form_issues), "form_issues": form_issues},
            )
        except Exception as e:
            return TestResult(
                status=TestStatus.FAILED,
                message="Form validation test failed",
                duration_ms=0,
                error=str(e),
            )


class ConsoleErrorDetector(BaseTestRunner):
    async def run(self) -> TestResult:
        try:
            start = time.time()

            console_errors = []
            exceptions = []

            def handle_console(msg):
                if msg.type in ("error", "warning"):
                    console_errors.append(
                        {"type": msg.type, "text": msg.text, "location": msg.location}
                    )

            def handle_exception(exception):
                exceptions.append(str(exception))

            self.page.on("console", handle_console)
            self.page.on("pageerror", handle_exception)

            await self.page.goto(self.base_url, wait_until="networkidle")
            await asyncio.sleep(2)

            duration = int((time.time() - start) * 1000)

            all_issues = console_errors + [{"type": "exception", "text": e} for e in exceptions]

            severity = (
                TestStatus.FAILED if len(all_issues) > 5 else TestStatus.WARNING
                if len(all_issues) > 0
                else TestStatus.PASSED
            )

            return TestResult(
                status=severity,
                message=f"Console error detection completed. Found {len(all_issues)} issues.",
                duration_ms=duration,
                details={"console_errors": console_errors, "exceptions": exceptions},
            )
        except Exception as e:
            return TestResult(
                status=TestStatus.FAILED,
                message="Console error detection failed",
                duration_ms=0,
                error=str(e),
            )


class QAAgent:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None

    async def initialize(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch()
        logger.info("Browser initialized")

    async def cleanup(self):
        if self.browser:
            await self.browser.close()
        logger.info("Browser closed")

    async def create_test_execution(
        self, project_id: str, execution_id: str
    ) -> Dict[str, Any]:
        return {
            "id": execution_id,
            "project_id": project_id,
            "status": "running",
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0,
        }

    async def run_test_suite(
        self, project_id: str, base_url: str, test_types: List[TestType]
    ) -> Dict[str, Any]:
        execution_id = str(__import__("uuid").uuid4())

        try:
            self.context = await self.browser.new_context()
            page = await self.context.new_page()

            execution = await self.create_test_execution(project_id, execution_id)

            test_runners = {
                TestType.FUNCTIONAL: FunctionalTestRunner(page, base_url),
                TestType.PERFORMANCE: PerformanceTestRunner(page, base_url),
                TestType.ACCESSIBILITY: AccessibilityTestRunner(page, base_url),
                TestType.BROKEN_LINKS: BrokenLinksTestRunner(page, base_url),
                TestType.FORM_VALIDATION: FormValidationTestRunner(page, base_url),
            }

            results = []

            for test_type in test_types:
                if test_type in test_runners:
                    logger.info(f"Running {test_type.value} test")
                    runner = test_runners[test_type]

                    result = await runner.run()
                    results.append(
                        {
                            "test_type": test_type.value,
                            "result": asdict(result),
                        }
                    )

                    if result.status == TestStatus.PASSED:
                        execution["passed"] += 1
                    elif result.status == TestStatus.FAILED:
                        execution["failed"] += 1
                    else:
                        execution["warnings"] += 1

                    execution["total_tests"] += 1

            await page.close()
            await self.context.close()

            execution["status"] = "completed"

            await supabase.table("test_executions").insert(
                {
                    "id": execution_id,
                    "project_id": project_id,
                    "status": execution["status"],
                    "total_tests": execution["total_tests"],
                    "passed": execution["passed"],
                    "failed": execution["failed"],
                    "warnings": execution["warnings"],
                }
            ).execute()

            for idx, test_result in enumerate(results):
                await supabase.table("test_results").insert(
                    {
                        "execution_id": execution_id,
                        "scenario_id": str(__import__("uuid").uuid4()),
                        "status": test_result["result"]["status"],
                        "error_message": test_result["result"]["error"],
                        "duration_ms": test_result["result"]["duration_ms"],
                        "details": test_result["result"]["details"],
                    }
                ).execute()

            logger.info(f"Test execution {execution_id} completed")
            return execution

        except Exception as e:
            logger.error(f"Test execution failed: {str(e)}")
            await supabase.table("test_executions").insert(
                {
                    "id": execution_id,
                    "project_id": project_id,
                    "status": "failed",
                    "total_tests": 0,
                    "passed": 0,
                    "failed": 1,
                    "warnings": 0,
                }
            ).execute()
            raise


async def main():
    agent = QAAgent(user_id="test-user")
    await agent.initialize()

    try:
        result = await agent.run_test_suite(
            project_id="test-project",
            base_url="https://example.com",
            test_types=[
                TestType.FUNCTIONAL,
                TestType.PERFORMANCE,
                TestType.ACCESSIBILITY,
                TestType.BROKEN_LINKS,
            ],
        )
        print(json.dumps(result, indent=2))
    finally:
        await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
