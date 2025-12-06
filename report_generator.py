import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import asdict
import logging
from enum import Enum

from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


class ReportFormat(str, Enum):
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"
    PDF = "pdf"


class ReportGenerator:
    def __init__(self, execution_id: str, project_id: str):
        self.execution_id = execution_id
        self.project_id = project_id
        self.execution_data = None
        self.test_results = []
        self.bug_reports = []
        self.performance_metrics = []

    async def load_execution_data(self):
        try:
            response = await supabase.table("test_executions").select("*").eq("id", self.execution_id).single().execute()
            self.execution_data = response.data
        except Exception as e:
            logger.error(f"Failed to load execution data: {str(e)}")

    async def load_test_results(self):
        try:
            response = (
                await supabase.table("test_results")
                .select("*")
                .eq("execution_id", self.execution_id)
                .execute()
            )
            self.test_results = response.data or []
        except Exception as e:
            logger.error(f"Failed to load test results: {str(e)}")

    async def load_bug_reports(self):
        try:
            response = (
                await supabase.table("bug_reports")
                .select("*")
                .eq("execution_id", self.execution_id)
                .execute()
            )
            self.bug_reports = response.data or []
        except Exception as e:
            logger.error(f"Failed to load bug reports: {str(e)}")

    async def load_performance_metrics(self):
        try:
            response = (
                await supabase.table("performance_metrics")
                .select("*")
                .eq("execution_id", self.execution_id)
                .execute()
            )
            self.performance_metrics = response.data or []
        except Exception as e:
            logger.error(f"Failed to load performance metrics: {str(e)}")

    async def load_all_data(self):
        await self.load_execution_data()
        await self.load_test_results()
        await self.load_bug_reports()
        await self.load_performance_metrics()

    def generate_summary(self) -> Dict[str, Any]:
        if not self.execution_data:
            return {}

        return {
            "execution_id": self.execution_id,
            "execution_date": self.execution_data.get("execution_date"),
            "status": self.execution_data.get("status"),
            "duration_seconds": self.execution_data.get("duration_seconds"),
            "total_tests": self.execution_data.get("total_tests", 0),
            "passed": self.execution_data.get("passed", 0),
            "failed": self.execution_data.get("failed", 0),
            "warnings": self.execution_data.get("warnings", 0),
            "pass_rate": (
                (self.execution_data.get("passed", 0) / max(1, self.execution_data.get("total_tests", 1)))
                * 100
            ),
        }

    def generate_bug_summary(self) -> Dict[str, Any]:
        severity_counts = {
            "critical": len([b for b in self.bug_reports if b.get("severity") == "critical"]),
            "high": len([b for b in self.bug_reports if b.get("severity") == "high"]),
            "medium": len([b for b in self.bug_reports if b.get("severity") == "medium"]),
            "low": len([b for b in self.bug_reports if b.get("severity") == "low"]),
            "info": len([b for b in self.bug_reports if b.get("severity") == "info"]),
        }

        bug_type_counts = {}
        for bug in self.bug_reports:
            bug_type = bug.get("bug_type", "unknown")
            bug_type_counts[bug_type] = bug_type_counts.get(bug_type, 0) + 1

        return {
            "total_bugs": len(self.bug_reports),
            "severity_breakdown": severity_counts,
            "type_breakdown": bug_type_counts,
            "bugs": self.bug_reports,
        }

    def generate_performance_summary(self) -> Dict[str, Any]:
        if not self.performance_metrics:
            return {"total_pages_tested": 0, "metrics": []}

        avg_load_time = sum(m.get("page_load_time_ms", 0) for m in self.performance_metrics) / len(
            self.performance_metrics
        )
        avg_fcp = sum(m.get("first_contentful_paint_ms", 0) for m in self.performance_metrics) / len(
            self.performance_metrics
        )

        return {
            "total_pages_tested": len(self.performance_metrics),
            "average_load_time_ms": int(avg_load_time),
            "average_fcp_ms": int(avg_fcp),
            "metrics": self.performance_metrics,
        }

    def generate_json_report(self) -> str:
        report = {
            "execution_summary": self.generate_summary(),
            "bug_summary": self.generate_bug_summary(),
            "performance_summary": self.generate_performance_summary(),
            "test_results": self.test_results,
            "generated_at": datetime.now().isoformat(),
        }

        return json.dumps(report, indent=2, default=str)

    def generate_html_report(self) -> str:
        summary = self.generate_summary()
        bug_summary = self.generate_bug_summary()
        perf_summary = self.generate_performance_summary()

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QA Test Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f7fa;
            padding: 20px;
            color: #333;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 40px; }}
        h1 {{ color: #1a1a1a; margin-bottom: 30px; font-size: 28px; }}
        h2 {{ color: #2c3e50; margin-top: 30px; margin-bottom: 15px; font-size: 22px; border-bottom: 2px solid #e1e8ed; padding-bottom: 10px; }}
        h3 {{ color: #34495e; margin-top: 20px; margin-bottom: 10px; font-size: 16px; }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-card.passed {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }}
        .stat-card.failed {{ background: linear-gradient(135deg, #ee0979 0%, #ff6a00 100%); }}
        .stat-card.warnings {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }}
        .stat-value {{ font-size: 32px; font-weight: bold; margin-bottom: 5px; }}
        .stat-label {{ font-size: 14px; opacity: 0.9; }}
        .bug-list {{ margin-top: 20px; }}
        .bug-item {{
            background: #f8f9fa;
            border-left: 4px solid #e1e8ed;
            padding: 15px;
            margin-bottom: 12px;
            border-radius: 4px;
            transition: all 0.3s ease;
        }}
        .bug-item:hover {{ box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .bug-item.critical {{ border-left-color: #e74c3c; }}
        .bug-item.high {{ border-left-color: #e67e22; }}
        .bug-item.medium {{ border-left-color: #f39c12; }}
        .bug-item.low {{ border-left-color: #3498db; }}
        .bug-title {{ font-weight: 600; color: #2c3e50; margin-bottom: 8px; }}
        .bug-severity {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: 600;
            margin-top: 8px;
        }}
        .bug-severity.critical {{ background: #e74c3c; color: white; }}
        .bug-severity.high {{ background: #e67e22; color: white; }}
        .bug-severity.medium {{ background: #f39c12; color: white; }}
        .bug-severity.low {{ background: #3498db; color: white; }}
        .performance-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        .performance-table th {{
            background: #ecf0f1;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #bdc3c7;
        }}
        .performance-table td {{
            padding: 12px;
            border-bottom: 1px solid #ecf0f1;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ecf0f1;
            font-size: 12px;
            color: #7f8c8d;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>QA Test Execution Report</h1>

        <h2>Execution Summary</h2>
        <div class="summary-grid">
            <div class="stat-card">
                <div class="stat-value">{summary.get('total_tests', 0)}</div>
                <div class="stat-label">Total Tests</div>
            </div>
            <div class="stat-card passed">
                <div class="stat-value">{summary.get('passed', 0)}</div>
                <div class="stat-label">Passed</div>
            </div>
            <div class="stat-card failed">
                <div class="stat-value">{summary.get('failed', 0)}</div>
                <div class="stat-label">Failed</div>
            </div>
            <div class="stat-card warnings">
                <div class="stat-value">{summary.get('warnings', 0)}</div>
                <div class="stat-label">Warnings</div>
            </div>
        </div>
        <p><strong>Pass Rate:</strong> {summary.get('pass_rate', 0):.1f}%</p>

        <h2>Bug Report Summary</h2>
        <p><strong>Total Bugs Found:</strong> {bug_summary.get('total_bugs', 0)}</p>
        <div class="summary-grid">
            <div style="background: #e74c3c; color: white; padding: 15px; border-radius: 4px; text-align: center;">
                <div style="font-size: 24px; font-weight: bold;">{bug_summary.get('severity_breakdown', {}).get('critical', 0)}</div>
                <div>Critical</div>
            </div>
            <div style="background: #e67e22; color: white; padding: 15px; border-radius: 4px; text-align: center;">
                <div style="font-size: 24px; font-weight: bold;">{bug_summary.get('severity_breakdown', {}).get('high', 0)}</div>
                <div>High</div>
            </div>
            <div style="background: #f39c12; color: white; padding: 15px; border-radius: 4px; text-align: center;">
                <div style="font-size: 24px; font-weight: bold;">{bug_summary.get('severity_breakdown', {}).get('medium', 0)}</div>
                <div>Medium</div>
            </div>
            <div style="background: #3498db; color: white; padding: 15px; border-radius: 4px; text-align: center;">
                <div style="font-size: 24px; font-weight: bold;">{bug_summary.get('severity_breakdown', {}).get('low', 0)}</div>
                <div>Low</div>
            </div>
        </div>

        <h2>Bugs Detected</h2>
        <div class="bug-list">
"""

        for bug in bug_summary.get("bugs", [])[:20]:
            html += f"""
            <div class="bug-item {bug.get('severity', 'info')}">
                <div class="bug-title">{bug.get('title', 'Unknown')}</div>
                <div>{bug.get('description', '')}</div>
                <span class="bug-severity {bug.get('severity', 'info')}">{bug.get('severity', 'info').upper()}</span>
            </div>
"""

        html += """
        </div>

        <h2>Performance Metrics</h2>
"""

        if perf_summary.get("total_pages_tested", 0) > 0:
            html += f"""
        <p><strong>Pages Tested:</strong> {perf_summary.get('total_pages_tested', 0)}</p>
        <p><strong>Average Load Time:</strong> {perf_summary.get('average_load_time_ms', 0)}ms</p>
        <p><strong>Average FCP:</strong> {perf_summary.get('average_fcp_ms', 0)}ms</p>
"""
        else:
            html += "<p>No performance metrics available.</p>"

        html += f"""
        <div class="footer">
            <p>Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Execution ID: {self.execution_id}</p>
        </div>
    </div>
</body>
</html>
"""

        return html

    def generate_markdown_report(self) -> str:
        summary = self.generate_summary()
        bug_summary = self.generate_bug_summary()
        perf_summary = self.generate_performance_summary()

        md = f"""# QA Test Execution Report

## Execution Summary

- **Execution ID:** {self.execution_id}
- **Status:** {summary.get('status', 'unknown')}
- **Total Tests:** {summary.get('total_tests', 0)}
- **Passed:** {summary.get('passed', 0)}
- **Failed:** {summary.get('failed', 0)}
- **Warnings:** {summary.get('warnings', 0)}
- **Pass Rate:** {summary.get('pass_rate', 0):.1f}%

## Bug Report Summary

- **Total Bugs Found:** {bug_summary.get('total_bugs', 0)}

### Severity Breakdown

| Severity | Count |
|----------|-------|
| Critical | {bug_summary.get('severity_breakdown', {}).get('critical', 0)} |
| High | {bug_summary.get('severity_breakdown', {}).get('high', 0)} |
| Medium | {bug_summary.get('severity_breakdown', {}).get('medium', 0)} |
| Low | {bug_summary.get('severity_breakdown', {}).get('low', 0)} |

## Bugs Detected

"""

        for bug in bug_summary.get("bugs", []):
            md += f"""### {bug.get('title', 'Unknown')}

**Severity:** {bug.get('severity', 'info').upper()}
**Type:** {bug.get('bug_type', 'unknown')}
**Page:** {bug.get('page_url', 'unknown')}

{bug.get('description', '')}

"""

        md += f"""
## Performance Metrics

- **Pages Tested:** {perf_summary.get('total_pages_tested', 0)}
- **Average Load Time:** {perf_summary.get('average_load_time_ms', 0)}ms
- **Average FCP:** {perf_summary.get('average_fcp_ms', 0)}ms

---

*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        return md

    async def generate_report(self, format: ReportFormat = ReportFormat.JSON) -> str:
        await self.load_all_data()

        if format == ReportFormat.JSON:
            return self.generate_json_report()
        elif format == ReportFormat.HTML:
            return self.generate_html_report()
        elif format == ReportFormat.MARKDOWN:
            return self.generate_markdown_report()
        else:
            return self.generate_json_report()
