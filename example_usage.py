import asyncio
import json
import logging
from orchestrator import QAOrchestrator
from report_generator import ReportGenerator, ReportFormat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_basic_test_suite():
    orchestrator = QAOrchestrator(user_id="demo-user")
    await orchestrator.initialize()

    try:
        logger.info("Running basic QA test suite...")

        result = await orchestrator.run_complete_qa_suite(
            project_id="demo-project",
            base_url="https://example.com",
            test_types=[
                "functional",
                "performance",
                "accessibility",
            ],
        )

        logger.info("Test suite completed:")
        print(json.dumps(result, indent=2))

        return result

    finally:
        await orchestrator.cleanup()


async def example_generate_reports(execution_id: str, project_id: str):
    logger.info(f"Generating reports for execution {execution_id}")

    generator = ReportGenerator(execution_id=execution_id, project_id=project_id)

    json_report = await generator.generate_report(ReportFormat.JSON)
    html_report = await generator.generate_report(ReportFormat.HTML)
    markdown_report = await generator.generate_report(ReportFormat.MARKDOWN)

    logger.info("JSON Report generated")
    print("=" * 80)
    print("JSON REPORT PREVIEW:")
    print("=" * 80)
    print(json_report[:1000])
    print("\n")

    with open(f"report_{execution_id}.html", "w") as f:
        f.write(html_report)
    logger.info(f"HTML report saved to report_{execution_id}.html")

    with open(f"report_{execution_id}.md", "w") as f:
        f.write(markdown_report)
    logger.info(f"Markdown report saved to report_{execution_id}.md")


async def example_create_schedule():
    orchestrator = QAOrchestrator(user_id="demo-user")

    logger.info("Creating scheduled test...")

    schedule_id = await orchestrator.create_scheduled_test(
        project_id="demo-project",
        name="Daily QA Suite",
        cron_expression="0 9 * * *",
    )

    if schedule_id:
        logger.info(f"Schedule created: {schedule_id}")

        schedules = await orchestrator.list_scheduled_tests("demo-project")
        logger.info(f"Project schedules: {json.dumps(schedules, indent=2, default=str)}")

        await orchestrator.disable_scheduled_test(schedule_id)
        logger.info(f"Schedule {schedule_id} disabled")


async def example_continuous_monitoring():
    orchestrator = QAOrchestrator(user_id="demo-user")
    await orchestrator.initialize()

    try:
        logger.info("Setting up continuous monitoring...")

        await orchestrator.create_scheduled_test(
            project_id="demo-project",
            name="Hourly Monitoring",
            cron_expression="0 * * * *",
        )

        await orchestrator.create_scheduled_test(
            project_id="demo-project",
            name="Daily Deep Test",
            cron_expression="0 2 * * *",
        )

        logger.info("Monitoring schedules created")
        logger.info("Start scheduler with: await orchestrator.start_scheduler()")

    finally:
        await orchestrator.cleanup()


async def main():
    print("\n" + "=" * 80)
    print("AUTONOMOUS QA SPECIALIST - EXAMPLE USAGE")
    print("=" * 80 + "\n")

    print("1. Running basic test suite...")
    print("-" * 80)
    result = await example_basic_test_suite()
    execution_id = result.get("execution_id")

    if execution_id:
        print("\n2. Generating reports...")
        print("-" * 80)
        await example_generate_reports(execution_id, "demo-project")

    print("\n3. Creating test schedule...")
    print("-" * 80)
    await example_create_schedule()

    print("\n4. Setting up continuous monitoring...")
    print("-" * 80)
    await example_continuous_monitoring()

    print("\n" + "=" * 80)
    print("EXAMPLES COMPLETED")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Check the database for test results and bug reports")
    print("2. Review generated HTML reports in the current directory")
    print("3. Customize test scenarios for your specific needs")
    print("4. Deploy the orchestrator for production use")


if __name__ == "__main__":
    asyncio.run(main())
