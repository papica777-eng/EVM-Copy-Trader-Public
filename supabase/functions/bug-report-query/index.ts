import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Client-Info, Apikey",
};

interface QueryParams {
  execution_id?: string;
  project_id?: string;
  severity?: string;
  status?: string;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      status: 200,
      headers: corsHeaders,
    });
  }

  try {
    if (req.method === "GET") {
      const url = new URL(req.url);
      const execution_id = url.searchParams.get("execution_id");
      const project_id = url.searchParams.get("project_id");
      const severity = url.searchParams.get("severity");

      if (!execution_id && !project_id) {
        return new Response(
          JSON.stringify({ error: "Missing execution_id or project_id parameter" }),
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
        query: {
          execution_id,
          project_id,
          severity,
        },
        message: "Query bug reports using the database directly",
        example: "GET /functions/v1/bug-report-query?execution_id=<id>&severity=critical",
      };

      return new Response(JSON.stringify(response), {
        status: 200,
        headers: {
          ...corsHeaders,
          "Content-Type": "application/json",
        },
      });
    } else if (req.method === "POST") {
      const payload = await req.json();

      const response = {
        status: "received",
        message: "Bug report query processed",
        query: payload,
        timestamp: new Date().toISOString(),
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
