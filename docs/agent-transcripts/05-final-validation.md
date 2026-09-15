# Agent Development Transcript — Final Validation

This entry records the important failures and corrections encountered during final integration testing. Secrets and credentials are intentionally omitted.

## 2026-09-15 — Docker transcript mount failure

### Symptom

Ingestion reported:

```text
Transcript directory not found: /data/transcripts
```

### Diagnosis

The host directory existed, but Docker had not mounted it into the backend container.

### Correction

Added the backend volume:

```yaml
volumes:
  - ./data/transcripts:/data/transcripts:ro
```

and configured the Docker environment to use:

```text
TRANSCRIPTS_DIR=/data/transcripts
```

### Verification

```bash
docker compose exec backend ls -la /data/transcripts
```

showed the transcript fixture.

Ingestion then completed successfully:

```text
Discovered 1 transcript file(s)
Inserted sample/lenny PMF source material
2 chunks created
0 embedding failures
```

## 2026-09-15 — Stale browser session

### Symptom

The UI showed:

```text
Session not found.
```

### Diagnosis

The browser retained a session UUID from a previous database state after Docker recreation.

### Correction

The frontend's New conversation flow clears the stale local session and creates a fresh server-side session.

### Verification

A new conversation could be created and messages persisted with a new UUID.

## 2026-09-15 — Ship 30 timeout

### Symptom

The Ship 30 endpoint returned:

```text
503 Service Unavailable
Chat request failed: timeout
provider=ollama
model=phi3:latest
timeout_seconds=60.0
```

### Diagnosis

Normal grounded answers were completing within the default provider timeout, but the Ship 30 request asks the local model to generate a much longer artifact.

### Correction

The provider contract was extended with an optional per-request timeout:

```python
timeout_seconds: float | None = None
```

Normal chat retains the default timeout.

Ship 30 explicitly requests:

```python
timeout_seconds=300.0
```

The backend image was rebuilt without cache to ensure the running container contained the change.

### Verification

The running Docker container was checked directly:

```bash
docker compose exec backend \
  grep -n -A6 "chat_provider.generate" \
  /app/app/services/ship30.py
```

and showed:

```text
timeout_seconds=300.0
```

The Ollama provider inside the container also accepts the optional timeout.

## 2026-09-15 — Pi executable availability

### Symptom

Docker logs showed:

```text
Pi invocation failed: executable unavailable
Pi unavailable; using grounded fallback
```

### Diagnosis

The local development environment had Pi-related code, but the backend Docker image did not contain an executable named `pi`.

### Current behavior

The application keeps the agent boundary explicit and falls back to the deterministic grounded service when Pi is unavailable. The condition is logged rather than hidden.

### Submission note

Before final submission, verify the agent requirement against the actual runtime. If Pi is used as the required agent implementation, package/configure it in the reproducible environment rather than relying on a developer-machine installation.

## Test checkpoint

The backend development suite reached:

```text
97 passed
```

The Docker stack reached:

```text
lenny-backend   Up
lenny-db       Up (healthy)
lenny-frontend Up
```
