# Persisting analysis results

The worker now registers \`analysis.persist_result\`. Its payload is:

\`\`\`json
{
  "analysis_id": "existing-analysis-id",
  "owner_id": "authenticated-owner-id",
  "result": {
    "summary": "Summary text",
    "provider": "gemini",
    "model": "gemini-flash",
    "clips": [
      {"title":"Example","start_time":12.0,"end_time":38.0,"virality_score":82}
    ],
    "transcript": [
      {"start":12.0,"end":15.0,"text":"Transcript segment"}
    ]
  }
}
\`\`\`

The handler verifies that both the Analysis and MediaAsset belong to the supplied owner. It updates the Analysis JSON, replaces clip candidates on replay (idempotent derived rows), and appends a transcript revision. It commits the database transaction before the worker acknowledges the Redis message.

This is the persistence stage, not yet the full AI-analysis execution pipeline. The current \`POST /api/analyze\` route remains unchanged and streams results to existing clients. The next step is to create an authenticated analysis-job endpoint that creates the Analysis record, extracts a reusable engine service from the streaming route, and enqueues only after that service is callable by a worker. Do not enqueue a placeholder job.
