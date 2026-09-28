"use client";

/** Last resort when the root layout itself fails. */
export default function GlobalError({ error }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif", background: "#F2F8FC", color: "#0B2239", padding: "4rem 1rem", textAlign: "center" }}>
        <h1>Nexus hit an error</h1>
        <p>Reload the page. If it keeps happening, sign out and back in.</p>
        {error?.digest && <p style={{ fontSize: "0.8rem" }}>Reference: {error.digest}</p>}
        <button type="button" onClick={() => window.location.reload()} style={{ minHeight: 44, padding: "0 1rem", borderRadius: 8, border: 0, background: "#0369A8", color: "#fff", fontWeight: 600 }}>Reload</button>
      </body>
    </html>
  );
}
