import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Client-Info, Apikey",
};

interface ReportRequest {
  execution_id: string;
  format: "json" | "html" | "markdown";
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
      const payload: ReportRequest = await req.json();

      if (!payload.execution_id) {
        return new Response(
          JSON.stringify({ error: "Missing execution_id" }),
          {
            status: 400,
            headers: {
              ...corsHeaders,
              "Content-Type": "application/json",
            },
          }
        );
      }

      const format = payload.format || "json";
      const contentType = format === "html" ? "text/html" : "application/json";

      const response = {
        status: "generating",
        execution_id: payload.execution_id,
        format,
        message: "Report generation initiated. Use report_generator.py for full generation.",
        timestamp: new Date().toISOString(),
      };

      return new Response(JSON.stringify(response), {
        status: 202,
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
