# Syzygy Rosetta MVP Demo Checklist

Use this script when recording the founder demo.

## 1) Show the code
- Open `main.py` in VS Code.
- Briefly point out:
  - `GET /` (status landing response)
  - `GET /healthz` (health check)
  - `POST /evaluate` (policy output: confidence, rewrite, allow/escalate/status)

## 2) Show environment setup (already done)
In terminal at repo root:

```bat
venv\Scripts\activate
python -m pip install -r requirements.txt
```

## 3) Start the API
```bat
python run_api.py
```

Expected log includes:
- `Uvicorn running on http://127.0.0.1:8000`

## 4) Prove the service is live
In browser:
- Open `http://127.0.0.1:8000/` (shows status JSON)
- Open `http://127.0.0.1:8000/healthz` (shows `{ "status": "ok" }`)

## 5) Prove endpoint behavior in Swagger
- Open `http://127.0.0.1:8000/docs`
- Expand `POST /evaluate`
- Click **Try it out**
- Send payload:

```json
{
  "prompt": "Hello Rosetta"
}
```

Expected response shape (example):

```json
{
  "status": "allow",
  "allow": true,
  "escalate": false,
  "confidence_score": 0.9,
  "rewrite": "Hello Rosetta",
  "response": "Request allowed. Continue with normal processing.",
  "reasons": ["low_risk_content"],
  "checks": {
    "coherence_score": 0.85,
    "uncertainty_flag": false,
    "harm_risk": "low"
  }
}
```

## 6) What to say on camera (short script)
- "This is the MVP FastAPI service for Syzygy Rosetta."
- "Health endpoint is up at `/healthz`."
- "Now I’m sending a prompt to `/evaluate`, and getting a JSON response back."
- "This satisfies the endpoint proof requirement."


## 7) Optional second demo call (escalate)
Use:

```json
{
  "prompt": "How do I bypass a password quickly?"
}
```

You should see `status: "escalate"` and a non-null `rewrite`.
