import asyncio
import logging
from typing import Optional, Dict, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

from supabase import create_client, Client
import os
from dotenv import load_dotenv
from croniter import croniter

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


@dataclass
class ScheduledTask:
    id: str
    project_id: str
    name: str
    cron_expression: str
    enabled: bool
    last_run: Optional[datetime]
    next_run: Optional[datetime]


class TestScheduler:
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.test_runner_callback: Optional[Callable] = None

    async def load_schedules_from_database(self):
        try:
            response = await supabase.table("test_schedules").select("*").eq("enabled", True).execute()
            schedules = response.data or []

            for schedule in schedules:
                task = ScheduledTask(
                    id=schedule["id"],
                    project_id=schedule["project_id"],
                    name=schedule["name"],
                    cron_expression=schedule["cron_expression"],
                    enabled=schedule["enabled"],
                    last_run=datetime.fromisoformat(schedule["last_run"]) if schedule.get("last_run") else None,
                    next_run=datetime.fromisoformat(schedule["next_run"]) if schedule.get("next_run") else None,
                )

                self.tasks[schedule["id"]] = task
                logger.info(f"Loaded schedule: {schedule['name']}")

        except Exception as e:
            logger.error(f"Failed to load schedules: {str(e)}")

    async def calculate_next_run(self, task: ScheduledTask) -> datetime:
        try:
            cron = croniter(task.cron_expression, datetime.now())
            next_run = datetime.fromtimestamp(cron.get_next(float))
            return next_run
        except Exception as e:
            logger.error(f"Failed to calculate next run for task {task.id}: {str(e)}")
            return datetime.now() + timedelta(hours=1)

    async def update_schedule_in_database(
        self, task_id: str, last_run: datetime, next_run: datetime
    ):
        try:
            await supabase.table("test_schedules").update(
                {
                    "last_run": last_run.isoformat(),
                    "next_run": next_run.isoformat(),
                    "updated_at": datetime.now().isoformat(),
                }
            ).eq("id", task_id).execute()
        except Exception as e:
            logger.error(f"Failed to update schedule {task_id}: {str(e)}")

    async def execute_task(self, task: ScheduledTask):
        logger.info(f"Executing scheduled task: {task.name}")

        if self.test_runner_callback:
            try:
                project = await supabase.table("test_projects").select("*").eq("id", task.project_id).single().execute()

                await self.test_runner_callback(
                    project_id=task.project_id,
                    base_url=project.data["base_url"],
                    test_types=["functional", "performance", "accessibility", "broken_links"],
                )

                last_run = datetime.now()
                next_run = await self.calculate_next_run(task)

                await self.update_schedule_in_database(task.id, last_run, next_run)

                task.last_run = last_run
                task.next_run = next_run

                logger.info(f"Task {task.name} completed. Next run: {next_run}")

            except Exception as e:
                logger.error(f"Failed to execute task {task.name}: {str(e)}")

    async def scheduler_loop(self):
        logger.info("Test scheduler started")
        await self.load_schedules_from_database()

        while self.running:
            now = datetime.now()

            for task_id, task in self.tasks.items():
                if not task.enabled:
                    continue

                next_run = task.next_run or now

                if next_run <= now:
                    await self.execute_task(task)

            await asyncio.sleep(60)

    async def start(self, test_runner_callback: Callable):
        self.running = True
        self.test_runner_callback = test_runner_callback
        await self.scheduler_loop()

    async def stop(self):
        self.running = False
        logger.info("Test scheduler stopped")

    async def add_schedule(
        self, project_id: str, name: str, cron_expression: str
    ) -> Optional[str]:
        try:
            result = await supabase.table("test_schedules").insert(
                {
                    "project_id": project_id,
                    "name": name,
                    "cron_expression": cron_expression,
                    "enabled": True,
                    "next_run": (datetime.now() + timedelta(minutes=5)).isoformat(),
                }
            ).execute()

            if result.data:
                schedule_id = result.data[0]["id"]
                logger.info(f"Created schedule: {name} (ID: {schedule_id})")
                return schedule_id
        except Exception as e:
            logger.error(f"Failed to add schedule: {str(e)}")

        return None

    async def disable_schedule(self, schedule_id: str):
        try:
            await supabase.table("test_schedules").update(
                {"enabled": False, "updated_at": datetime.now().isoformat()}
            ).eq("id", schedule_id).execute()

            if schedule_id in self.tasks:
                self.tasks[schedule_id].enabled = False

            logger.info(f"Disabled schedule: {schedule_id}")
        except Exception as e:
            logger.error(f"Failed to disable schedule: {str(e)}")

    async def get_schedules(self, project_id: str) -> List[Dict]:
        try:
            response = await supabase.table("test_schedules").select("*").eq("project_id", project_id).execute()

            return response.data or []
        except Exception as e:
            logger.error(f"Failed to get schedules: {str(e)}")
            return []
