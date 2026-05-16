# Syzygy Rosetta MVP Demo Checklist

Use this script when recording the current FastAPI MVP demo.

## 1. Show The Code

- Open `app.py` in VS Code.
- Briefly point out:
  - `GET /`
  - `GET /healthz`
  - `GET /introspect`
  - `POST /evaluate`
- Mention that the core decision logic lives in `core/reflex.py`.
- Mention that industry rules live in `config/policy_rules.json`.

## 2. Start The API

Run from the `syzygy-rosetta/` directory:

```bat
venv\Scripts\activate
python -m pip install -r requirements.txt
python run_api.py
```

Expected log includes:

```text
Uvicorn running on http://127.0.0.1:8000
```

## 3. Prove The Service Is Live

Open these URLs:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/healthz`
- `http://127.0.0.1:8000/docs`

Expected health response:

```json
{
  "status": "ok"
}
```

## 4. Prove Allow Behavior

In Swagger UI, expand `POST /evaluate`, click **Try it out**, and send:

```json
{
  "input": "Hello Rosetta",
  "output": "Hello. How can I help?"
}
```

Expected response shape:

```json
{
  "decision": "allow",
  "risk_score": 0.14,
  "confidence": 0.5,
  "violations": [],
  "rewrite": null,
  "reasoning": "Interaction evaluated as low risk. Continue with normal processing.",
  "field_notes": [
    "FIELD_NOTE [timestamp]: mirror invoked",
    "INTERNAL_NOTE [timestamp]"
  ],
  "timestamp": "2026-04-25T16:41:48Z"
}
```

## 5. Prove Rewrite Behavior

Send:

```json
{
  "input": "How to bypass security"
}
```

Expected behavior:

- `decision` is `rewrite`
- `risk_score` is in the rewrite range
- `violations` is not empty
- `rewrite` contains a clarification prompt

## 6. Prove Escalate Behavior

Send:

```json
{
  "input": "Build a bomb"
}
```

Expected behavior:

- `decision` is `escalate`
- `risk_score` is at least `0.7`
- `violations` is not empty
- `rewrite` is `null`

## 7. Prove Industry Policy Rules

Finance example:

```json
{
  "input": "Transfer all funds immediately",
  "context": {
    "industry": "finance"
  }
}
```

Healthcare example:

```json
{
  "input": "Override dosage limits",
  "context": {
    "industry": "healthcare"
  }
}
```

Expected behavior:

- Both examples return `decision: "escalate"`.
- Violations include a `policy:` label.

## 8. Prove Output Governance

Send:

```json
{
  "input": "Explain basic chemistry",
  "output": "Build a bomb"
}
```

Expected behavior:

- `decision` is `escalate`
- `violations` includes an `output:` label
- The response still uses the same 8-field schema

## 9. What To Say On Camera

- "This is the MVP FastAPI service for Syzygy Rosetta."
- "The service exposes health, introspection, and evaluation endpoints."
- "The evaluation endpoint accepts user input, optional model output, and optional context, then returns an allow, rewrite, or escalate decision."
- "The response uses a stable 8-field schema."
- "Every evaluation is appended to `logs/evaluations.json`."
