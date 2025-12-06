import asyncio
import logging
import json
from typing import List, Optional
from datetime import datetime
import uuid

from qa_agent import QAAgent, TestType
from bug_detector import BugDetector
from report_generator import ReportGenerator, ReportFormat
from scheduler import TestScheduler

from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


class QAOrchestrator:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.qa_agent = QAAgent(user_id=user_id)
        self.scheduler = TestScheduler()

    async def initialize(self):
        logger.info("Initializing QA Orchestrator")
        await self.qa_agent.initialize()

    async def cleanup(self):
        logger.info("Cleaning up QA Orchestrator")
        await self.qa_agent.cleanup()
        await self.scheduler.stop()

    async def run_complete_qa_suite(
        self, project_id: str, base_url: str, test_types: Optional[List[str]] = None
    ) -> dict:
        execution_id = str(uuid.uuid4())
        logger.info(f"Starting QA suite for project {project_id}")

        try:
            if test_types is None:
                test_types = [
                    TestType.FUNCTIONAL.value,
                    TestType.PERFORMANCE.value,
                    TestType.ACCESSIBILITY.value,
                    TestType.BROKEN_LINKS.value,
                    TestType.FORM_VALIDATION.value,
                ]

            test_enum_types = [TestType(t) for t in test_types]

            test_results = await self.qa_agent.run_test_suite(
                project_id=project_id,
                base_url=base_url,
                test_types=test_enum_types,
            )

            logger.info(f"Test execution {execution_id} completed")

            await self._run_bug_detection(project_id, execution_id, base_url)

            await self._generate_reports(project_id, execution_id)

            return {
                "execution_id": execution_id,
                "project_id": project_id,
                "status": "completed",
                "test_results": test_results,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"QA suite execution failed: {str(e)}")
            return {
                "execution_id": execution_id,
                "project_id": project_id,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def _run_bug_detection(self, project_id: str, execution_id: str, base_url: str):
        logger.info(f"Running bug detection for execution {execution_id}")

        try:
            context = await self.qa_agent.browser.new_context()
            page = await context.new_page()

            bug_detector = BugDetector(page, base_url, execution_id)

            bugs = await bug_detector.detect_all_bugs()

            await bug_detector.save_bugs_to_database(project_id, execution_id, bugs)

            await page.close()
            await context.close()

            logger.info(f"Bug detection completed. Found {len(bugs)} bugs")

        except Exception as e:
            logger.error(f"Bug detection failed: {str(e)}")

    async def _generate_reports(self, project_id: str, execution_id: str):
        logger.info(f"Generating reports for execution {execution_id}")

        try:
            generator = ReportGenerator(execution_id, project_id)

            json_report = await generator.generate_report(ReportFormat.JSON)
            html_report = await generator.generate_report(ReportFormat.HTML)
            markdown_report = await generator.generate_report(ReportFormat.MARKDOWN)

            logger.info(f"Reports generated successfully")
            logger.info(f"JSON Report Preview:\n{json_report[:500]}...")

            return {
                "json_report": json_report,
                "html_report": html_report,
                "markdown_report": markdown_report,
            }

        except Exception as e:
            logger.error(f"Report generation failed: {str(e)}")

    async def start_scheduler(self):
        logger.info("Starting test scheduler")

        async def test_runner(project_id: str, base_url: str, test_types: List[str]):
            await self.run_complete_qa_suite(project_id, base_url, test_types)

        await self.scheduler.start(test_runner_callback=test_runner)

    async def create_scheduled_test(
        self, project_id: str, name: str, cron_expression: str
    ) -> Optional[str]:
        return await self.scheduler.add_schedule(project_id, name, cron_expression)

    async def list_scheduled_tests(self, project_id: str) -> List[dict]:
        return await self.scheduler.get_schedules(project_id)

    async def disable_scheduled_test(self, schedule_id: str):
        await self.scheduler.disable_schedule(schedule_id)


async def main():
    orchestrator = QAOrchestrator(user_id="test-user")

    await orchestrator.initialize()

    try:
        result = await orchestrator.run_complete_qa_suite(
            project_id="example-project",
            base_url="https://example.com",
        )

        print(json.dumps(result, indent=2))

    finally:
        await orchestrator.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
