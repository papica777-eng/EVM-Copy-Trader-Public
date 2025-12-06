/*
  # QA Testing System Schema

  1. New Tables
    - `test_projects` - Store QA testing projects/configurations
    - `test_scenarios` - Define specific test cases to execute
    - `test_executions` - Track individual test run results
    - `bug_reports` - Store identified bugs and issues
    - `test_results` - Detailed results for each test scenario
    - `performance_metrics` - Track page load times and performance data
    - `accessibility_issues` - Store WCAG compliance violations
    - `screenshots` - Store test execution screenshots
    - `test_schedules` - Configure automated test scheduling

  2. Security
    - Enable RLS on all tables
    - Add policies for project-based access control
    - Policies ensure users only see their own projects and reports

  3. Key Features
    - Comprehensive bug tracking with severity levels
    - Performance monitoring and historical trends
    - Accessibility compliance checking
    - Screenshot capture for visual regression detection
    - Automated scheduling and continuous monitoring
*/

-- Test Projects Table
CREATE TABLE IF NOT EXISTS test_projects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  description text,
  base_url text NOT NULL,
  owner_id uuid NOT NULL,
  status text DEFAULT 'active',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE test_projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own projects"
  ON test_projects FOR SELECT
  TO authenticated
  USING (owner_id = auth.uid());

CREATE POLICY "Users can create projects"
  ON test_projects FOR INSERT
  TO authenticated
  WITH CHECK (owner_id = auth.uid());

CREATE POLICY "Users can update own projects"
  ON test_projects FOR UPDATE
  TO authenticated
  USING (owner_id = auth.uid())
  WITH CHECK (owner_id = auth.uid());

-- Test Scenarios Table
CREATE TABLE IF NOT EXISTS test_scenarios (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES test_projects(id) ON DELETE CASCADE,
  name text NOT NULL,
  description text,
  test_type text NOT NULL,
  priority text DEFAULT 'medium',
  enabled boolean DEFAULT true,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE test_scenarios ENABLE ROW LEVEL SECURITY;

CREATE POLICY "View project scenarios"
  ON test_scenarios FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM test_projects
      WHERE test_projects.id = test_scenarios.project_id
      AND test_projects.owner_id = auth.uid()
    )
  );

CREATE POLICY "Create project scenarios"
  ON test_scenarios FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM test_projects
      WHERE test_projects.id = project_id
      AND test_projects.owner_id = auth.uid()
    )
  );

CREATE POLICY "Update project scenarios"
  ON test_scenarios FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM test_projects
      WHERE test_projects.id = project_id
      AND test_projects.owner_id = auth.uid()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM test_projects
      WHERE test_projects.id = project_id
      AND test_projects.owner_id = auth.uid()
    )
  );

-- Test Executions Table
CREATE TABLE IF NOT EXISTS test_executions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES test_projects(id) ON DELETE CASCADE,
  execution_date timestamptz DEFAULT now(),
  status text DEFAULT 'running',
  total_tests integer DEFAULT 0,
  passed integer DEFAULT 0,
  failed integer DEFAULT 0,
  warnings integer DEFAULT 0,
  duration_seconds integer,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE test_executions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "View execution results"
  ON test_executions FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM test_projects
      WHERE test_projects.id = test_executions.project_id
      AND test_projects.owner_id = auth.uid()
    )
  );

CREATE POLICY "Create executions"
  ON test_executions FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM test_projects
      WHERE test_projects.id = project_id
      AND test_projects.owner_id = auth.uid()
    )
  );

CREATE POLICY "Update executions"
  ON test_executions FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM test_projects
      WHERE test_projects.id = project_id
      AND test_projects.owner_id = auth.uid()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM test_projects
      WHERE test_projects.id = project_id
      AND test_projects.owner_id = auth.uid()
    )
  );

-- Test Results Table
CREATE TABLE IF NOT EXISTS test_results (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  execution_id uuid NOT NULL REFERENCES test_executions(id) ON DELETE CASCADE,
  scenario_id uuid NOT NULL REFERENCES test_scenarios(id) ON DELETE CASCADE,
  status text NOT NULL,
  error_message text,
  duration_ms integer,
  details jsonb,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE test_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY "View test results"
  ON test_results FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM test_executions
      JOIN test_projects ON test_projects.id = test_executions.project_id
      WHERE test_executions.id = test_results.execution_id
      AND test_projects.owner_id = auth.uid()
    )
  );

CREATE POLICY "Create test results"
  ON test_results FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM test_executions
      JOIN test_projects ON test_projects.id = test_executions.project_id
      WHERE test_executions.id = execution_id
      AND test_projects.owner_id = auth.uid()
    )
  );

-- Bug Reports Table
CREATE TABLE IF NOT EXISTS bug_reports (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES test_projects(id) ON DELETE CASCADE,
  execution_id uuid REFERENCES test_executions(id) ON DELETE SET NULL,
  title text NOT NULL,
  description text,
  severity text NOT NULL,
  status text DEFAULT 'open',
  bug_type text,
  page_url text,
  steps_to_reproduce text,
  expected_behavior text,
  actual_behavior text,
  browser_info jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE bug_reports ENABLE ROW LEVEL SECURITY;

CREATE POLICY "View bug reports"
  ON bug_reports FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM test_projects
      WHERE test_projects.id = bug_reports.project_id
      AND test_projects.owner_id = auth.uid()
    )
  );

CREATE POLICY "Create bug reports"
  ON bug_reports FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM test_projects
      WHERE test_projects.id = project_id
      AND test_projects.owner_id = auth.uid()
    )
  );

CREATE POLICY "Update bug reports"
  ON bug_reports FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM test_projects
      WHERE test_projects.id = project_id
      AND test_projects.owner_id = auth.uid()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM test_projects
      WHERE test_projects.id = project_id
      AND test_projects.owner_id = auth.uid()
    )
  );

-- Performance Metrics Table
CREATE TABLE IF NOT EXISTS performance_metrics (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  execution_id uuid NOT NULL REFERENCES test_executions(id) ON DELETE CASCADE,
  page_url text NOT NULL,
  page_load_time_ms integer,
  first_contentful_paint_ms integer,
  largest_contentful_paint_ms integer,
  total_requests integer,
  failed_requests integer,
  total_size_kb numeric,
  resource_details jsonb,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE performance_metrics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "View performance metrics"
  ON performance_metrics FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM test_executions
      JOIN test_projects ON test_projects.id = test_executions.project_id
      WHERE test_executions.id = performance_metrics.execution_id
      AND test_projects.owner_id = auth.uid()
    )
  );

CREATE POLICY "Create performance metrics"
  ON performance_metrics FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM test_executions
      JOIN test_projects ON test_projects.id = test_executions.project_id
      WHERE test_executions.id = execution_id
      AND test_projects.owner_id = auth.uid()
    )
  );

-- Accessibility Issues Table
CREATE TABLE IF NOT EXISTS accessibility_issues (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  execution_id uuid NOT NULL REFERENCES test_executions(id) ON DELETE CASCADE,
  page_url text NOT NULL,
  issue_type text NOT NULL,
  wcag_level text,
  element_description text,
  severity text DEFAULT 'medium',
  recommendation text,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE accessibility_issues ENABLE ROW LEVEL SECURITY;

CREATE POLICY "View accessibility issues"
  ON accessibility_issues FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM test_executions
      JOIN test_projects ON test_projects.id = test_executions.project_id
      WHERE test_executions.id = accessibility_issues.execution_id
      AND test_projects.owner_id = auth.uid()
    )
  );

CREATE POLICY "Create accessibility issues"
  ON accessibility_issues FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM test_executions
      JOIN test_projects ON test_projects.id = test_executions.project_id
      WHERE test_executions.id = execution_id
      AND test_projects.owner_id = auth.uid()
    )
  );

-- Screenshots Table
CREATE TABLE IF NOT EXISTS screenshots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  execution_id uuid NOT NULL REFERENCES test_executions(id) ON DELETE CASCADE,
  scenario_id uuid REFERENCES test_scenarios(id) ON DELETE SET NULL,
  page_url text,
  screenshot_path text,
  screenshot_data text,
  description text,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE screenshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "View screenshots"
  ON screenshots FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM test_executions
      JOIN test_projects ON test_projects.id = test_executions.project_id
      WHERE test_executions.id = screenshots.execution_id
      AND test_projects.owner_id = auth.uid()
    )
  );

CREATE POLICY "Create screenshots"
  ON screenshots FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM test_executions
      JOIN test_projects ON test_projects.id = test_executions.project_id
      WHERE test_executions.id = execution_id
      AND test_projects.owner_id = auth.uid()
    )
  );

-- Test Schedules Table
CREATE TABLE IF NOT EXISTS test_schedules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES test_projects(id) ON DELETE CASCADE,
  name text NOT NULL,
  cron_expression text NOT NULL,
  enabled boolean DEFAULT true,
  last_run timestamptz,
  next_run timestamptz,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE test_schedules ENABLE ROW LEVEL SECURITY;

CREATE POLICY "View schedules"
  ON test_schedules FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM test_projects
      WHERE test_projects.id = test_schedules.project_id
      AND test_projects.owner_id = auth.uid()
    )
  );

CREATE POLICY "Create schedules"
  ON test_schedules FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM test_projects
      WHERE test_projects.id = project_id
      AND test_projects.owner_id = auth.uid()
    )
  );

CREATE POLICY "Update schedules"
  ON test_schedules FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM test_projects
      WHERE test_projects.id = project_id
      AND test_projects.owner_id = auth.uid()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM test_projects
      WHERE test_projects.id = project_id
      AND test_projects.owner_id = auth.uid()
    )
  );

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_test_projects_owner ON test_projects(owner_id);
CREATE INDEX IF NOT EXISTS idx_test_scenarios_project ON test_scenarios(project_id);
CREATE INDEX IF NOT EXISTS idx_test_executions_project ON test_executions(project_id);
CREATE INDEX IF NOT EXISTS idx_test_results_execution ON test_results(execution_id);
CREATE INDEX IF NOT EXISTS idx_bug_reports_project ON bug_reports(project_id);
CREATE INDEX IF NOT EXISTS idx_bug_reports_status ON bug_reports(status);
CREATE INDEX IF NOT EXISTS idx_bug_reports_severity ON bug_reports(severity);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_execution ON performance_metrics(execution_id);
CREATE INDEX IF NOT EXISTS idx_accessibility_issues_execution ON accessibility_issues(execution_id);
CREATE INDEX IF NOT EXISTS idx_screenshots_execution ON screenshots(execution_id);
CREATE INDEX IF NOT EXISTS idx_test_schedules_project ON test_schedules(project_id);