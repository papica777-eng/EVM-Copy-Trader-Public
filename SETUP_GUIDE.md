# Autonomous QA Specialist - Setup Guide

## Overview

The Autonomous QA Specialist is a comprehensive web testing and bug detection system designed for uTest Academy. It provides automated testing, bug detection, reporting, and scheduling capabilities for web applications.

## System Architecture

### Core Components

1. **QA Agent** (`qa_agent.py`)
   - Web automation using Playwright
   - Multiple test runners (Functional, Performance, Accessibility, Broken Links, Form Validation)
   - Browser-based testing with console error detection

2. **Bug Detector** (`bug_detector.py`)
   - Detects broken images, console errors, network issues
   - Accessibility violations (WCAG compliance)
   - Layout problems and heading structure issues
   - Saves findings to Supabase database

3. **Report Generator** (`report_generator.py`)
   - Generates JSON, HTML, and Markdown reports
   - Executive summaries with statistics
   - Bug severity breakdown and categorization
   - Performance metrics analysis

4. **Test Scheduler** (`scheduler.py`)
   - Cron-based automated test scheduling
   - Continuous monitoring capabilities
   - Schedule management via Supabase

5. **QA Orchestrator** (`orchestrator.py`)
   - Coordinates all components
   - Manages complete test suites
   - Handles scheduler integration

## Installation

### Prerequisites

- Python 3.10+
- Supabase account and project
- Playwright browser installed

### Setup Steps

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Playwright Browsers**
   ```bash
   playwright install chromium
   ```

3. **Configure Environment**
   Create `.env` file with:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_ANON_KEY=your_supabase_anon_key
   ```

4. **Initialize Database**
   The database schema is automatically created via Supabase migrations.

## Database Schema

### Tables

#### test_projects
- Stores QA project configurations
- Fields: id, name, description, base_url, owner_id, status, created_at, updated_at

#### test_scenarios
- Defines specific test cases
- Fields: id, project_id, name, description, test_type, priority, enabled, created_at, updated_at

#### test_executions
- Tracks individual test run results
- Fields: id, project_id, execution_date, status, total_tests, passed, failed, warnings, duration_seconds, created_at

#### bug_reports
- Stores identified bugs and issues
- Fields: id, project_id, execution_id, title, description, severity, status, bug_type, page_url, steps_to_reproduce, expected_behavior, actual_behavior, browser_info, created_at, updated_at

#### test_results
- Detailed results for each test scenario
- Fields: id, execution_id, scenario_id, status, error_message, duration_ms, details, created_at

#### performance_metrics
- Tracks page load times and performance data
- Fields: id, execution_id, page_url, page_load_time_ms, first_contentful_paint_ms, largest_contentful_paint_ms, total_requests, failed_requests, total_size_kb, resource_details, created_at

#### accessibility_issues
- Stores WCAG compliance violations
- Fields: id, execution_id, page_url, issue_type, wcag_level, element_description, severity, recommendation, created_at

#### screenshots
- Stores test execution screenshots
- Fields: id, execution_id, scenario_id, page_url, screenshot_path, screenshot_data, description, created_at

#### test_schedules
- Stores automated test schedules
- Fields: id, project_id, name, cron_expression, enabled, last_run, next_run, created_at, updated_at

## Usage

### Running a Complete QA Suite

```python
import asyncio
from orchestrator import QAOrchestrator

async def run_tests():
    orchestrator = QAOrchestrator(user_id="your-user-id")
    await orchestrator.initialize()

    try:
        result = await orchestrator.run_complete_qa_suite(
            project_id="project-123",
            base_url="https://example.com",
            test_types=[
                "functional",
                "performance",
                "accessibility",
                "broken_links",
                "form_validation"
            ]
        )
        print(result)
    finally:
        await orchestrator.cleanup()

asyncio.run(run_tests())
```

### Creating a Scheduled Test

```python
import asyncio
from orchestrator import QAOrchestrator

async def create_schedule():
    orchestrator = QAOrchestrator(user_id="your-user-id")

    schedule_id = await orchestrator.create_scheduled_test(
        project_id="project-123",
        name="Daily QA Suite",
        cron_expression="0 9 * * *"  # 9 AM daily
    )
    print(f"Schedule created: {schedule_id}")

asyncio.run(create_schedule())
```

### Generating Reports

```python
from report_generator import ReportGenerator, ReportFormat
import asyncio

async def generate_report():
    generator = ReportGenerator(execution_id="exec-123", project_id="project-123")

    # Generate JSON report
    json_report = await generator.generate_report(ReportFormat.JSON)

    # Generate HTML report
    html_report = await generator.generate_report(ReportFormat.HTML)

    # Generate Markdown report
    md_report = await generator.generate_report(ReportFormat.MARKDOWN)

asyncio.run(generate_report())
```

## API Endpoints

### Edge Functions

#### 1. qa-test-runner
**POST** `/functions/v1/qa-test-runner`

Initiate a new test execution.

Request Body:
```json
{
  "project_id": "project-123",
  "base_url": "https://example.com",
  "test_types": ["functional", "performance", "accessibility"]
}
```

Response:
```json
{
  "status": "started",
  "project_id": "project-123",
  "message": "QA test suite initiated",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### 2. bug-report-query
**GET** `/functions/v1/bug-report-query?execution_id=exec-123&severity=critical`

Query bug reports with filters.

Parameters:
- `execution_id` - Filter by execution ID
- `project_id` - Filter by project ID
- `severity` - Filter by severity (critical, high, medium, low, info)

#### 3. report-generator
**POST** `/functions/v1/report-generator`

Generate test reports.

Request Body:
```json
{
  "execution_id": "exec-123",
  "format": "html"
}
```

## Test Types

### Functional Testing
- Page load verification
- Interactive element detection
- Navigation testing

### Performance Testing
- Page load time measurement
- First Contentful Paint (FCP)
- Largest Contentful Paint (LCP)
- Resource timing analysis

### Accessibility Testing
- Missing alt text detection
- Label association checking
- Heading hierarchy validation
- Link text verification

### Broken Links Testing
- HTTP status code verification
- Redirect handling
- 404 detection

### Form Validation Testing
- Form structure validation
- Required field checking
- Submit button verification
- Input name attribute validation

## Bug Categories

- **broken_image** - Images that failed to load
- **broken_link** - Links returning HTTP errors
- **console_error** - JavaScript console errors
- **network_error** - Failed network requests
- **missing_alt_text** - Images without alt attributes
- **form_validation_error** - Form field issues
- **performance_issue** - Slow page loads
- **security_issue** - Potential security problems
- **layout_issue** - Layout and positioning problems
- **missing_heading** - Missing or improper heading structure
- **missing_label** - Form fields without labels
- **insufficient_contrast** - Color contrast accessibility issues
- **javascript_error** - JavaScript runtime errors

## Severity Levels

- **CRITICAL** - System breaking issues, blocked functionality
- **HIGH** - Major features broken, significant user impact
- **MEDIUM** - Noticeable issues affecting user experience
- **LOW** - Minor issues, cosmetic problems
- **INFO** - Informational findings

## Row Level Security (RLS)

All tables use RLS with auth.uid() to ensure users only access their own projects and data. Access is controlled at the project level through foreign key relationships.

## Cron Expression Examples

```
"0 9 * * *"          # Daily at 9 AM
"0 */4 * * *"        # Every 4 hours
"0 0 * * 1"          # Weekly on Monday at midnight
"0 0 1 * *"          # Monthly on the 1st
"*/30 * * * *"       # Every 30 minutes
```

## Performance Considerations

- Playwright browser instances are created per test execution
- Tests run sequentially to avoid resource conflicts
- Network timeout: 5 seconds per request
- Page navigation timeout: 30 seconds (default)
- Console/network monitoring runs continuously during page navigation

## Error Handling

All components include comprehensive error handling with:
- Detailed logging
- Graceful degradation
- Database transaction safety
- Automatic cleanup of resources

## Security

- Supabase RLS ensures data isolation
- Edge Functions verify JWT tokens
- No credentials stored in logs
- Browser instances sandboxed per execution
- CORS headers properly configured

## Troubleshooting

### Browser Connection Issues
- Verify Playwright installation: `playwright install chromium`
- Check system has required dependencies

### Database Connection Errors
- Verify `.env` file has correct Supabase credentials
- Check Supabase project is active

### Timeout Issues
- Increase page timeout for slow websites
- Check network connectivity

### Missing Bug Reports
- Verify accessibility detection is enabled
- Check console errors are being captured

## Support

For issues or feature requests, contact your uTest Academy administrator.
