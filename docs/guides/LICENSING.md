# License Integration

The application uses Licora through the fixed verification endpoint derived from `LICENSE_API_BASE_URL`. The API key is a source-controlled build constant by request; no PowerShell/environment API-key setup is used.

A real API key must remain private during development and should be scoped/rate-limited/revocable server-side because secrets embedded in desktop binaries cannot be considered non-extractable.
