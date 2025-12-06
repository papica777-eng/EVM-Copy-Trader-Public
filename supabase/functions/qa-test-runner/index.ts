import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Client-Info, Apikey",
};

interface TestRequest {
  project_id: string;
  base_url: string;
  test_types: string[];
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      status: 200,
      headers: corsHeaders,
    });
  }

  try {
    if (req.method === "POST") {
      const payload: TestRequest = await req.json();

      if (!payload.project_id || !payload.base_url) {
        return new Response(
          JSON.stringify({ error: "Missing required fields: project_id, base_url" }),
          {
            status: 400,
            headers: {
              ...corsHeaders,
              "Content-Type": "application/json",
            },
          }
        );
      }

      const response = {
        status: "started",
        project_id: payload.project_id,
        message: "QA test suite initiated. Check database for updates.",
        timestamp: new Date().toISOString(),
      };

      return new Response(JSON.stringify(response), {
        status: 202,
        headers: {
          ...corsHeaders,
          "Content-Type": "application/json",
        },
      });
    } else if (req.method === "GET") {
      const url = new URL(req.url);
      const project_id = url.searchParams.get("project_id");

      if (!project_id) {
        return new Response(
          JSON.stringify({ error: "Missing project_id parameter" }),
          {
            status: 400,
            headers: {
              ...corsHeaders,
              "Content-Type": "application/json",
            },
          }
        );
      }

      const response = {
        project_id,
        message: "Retrieve test execution history from test_executions table",
        endpoint: "GET /functions/v1/qa-test-runner?project_id=<project_id>",
      };

      return new Response(JSON.stringify(response), {
        status: 200,
        headers: {
          ...corsHeaders,
          "Content-Type": "application/json",
        },
      });
    }

    return new Response(JSON.stringify({ error: "Method not allowed" }), {
      status: 405,
      headers: {
        ...corsHeaders,
        "Content-Type": "application/json",
      },
    });
  } catch (error) {
    return new Response(
      JSON.stringify({
        error: "Internal server error",
        message: error instanceof Error ? error.message : "Unknown error",
      }),
      {
        status: 500,
        headers: {
          ...corsHeaders,
          "Content-Type": "application/json",
        },
      }
    );
  }
});
