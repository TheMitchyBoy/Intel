import { useEffect, useState } from "react";

interface SetupStatus {
  database_configured: boolean;
  diagnostics: Record<string, string>;
  instructions: string | null;
}

export function SetupBanner() {
  const [status, setStatus] = useState<SetupStatus | null>(null);

  useEffect(() => {
    fetch("/api/v1/setup")
      .then((r) => r.json())
      .then(setStatus)
      .catch(() => null);
  }, []);

  if (!status || status.database_configured) return null;

  return (
    <div className="setup-banner">
      <h2>PostgreSQL not connected</h2>
      <p>Your Railway deploy is running, but the database is not linked yet.</p>
      <ol>
        <li>
          Railway project → <strong>+ New</strong> → <strong>Database</strong> →{" "}
          <strong>PostgreSQL</strong>
        </li>
        <li>
          Open the Postgres service → <strong>Connect</strong> → select{" "}
          <strong>Throughline</strong>
        </li>
        <li>Redeploy Throughline</li>
      </ol>
      <details>
        <summary>Diagnostics</summary>
        <pre>{JSON.stringify(status.diagnostics, null, 2)}</pre>
      </details>
    </div>
  );
}
