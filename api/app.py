from fastapi import FastAPI
from pydantic import BaseModel
from feast import FeatureStore
import mlflow.pyfunc
import pandas as pd
import os
import time

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

app = FastAPI(title="StreamFlow Churn Prediction API")

# --- Config ---
REPO_PATH = "/repo"
MODEL_NAME = "streamflow_churn"
# TODO 1: complétez avec le nom de votre modèle
MODEL_URI = f"models:/streamflow_churn/Production"

# --- Prometheus metrics ---
# TODO: Créez les métriques avec les noms suivants:
# un Counter: "api_requests_total"
# un Histogram: "api_request_latency_seconds"
REQUEST_COUNT = Counter("api_requests_total", "Total number of API requests")
REQUEST_LATENCY = Histogram("api_request_latency_seconds", "Latency of API requests in seconds")

try:
    store = FeatureStore(repo_path=REPO_PATH)
    model = mlflow.pyfunc.load_model(MODEL_URI)
except Exception as e:
    print(f"Warning: init failed: {e}")
    store = None
    model = None


class UserPayload(BaseModel):
    user_id: str


@app.get("/health")
def health():
    return {"status": "ok"}


# TODO 2: Mettre une requête POST
@app.post("/predict")
def predict(payload: UserPayload):
    start_time = time.time()
    REQUEST_COUNT.inc()

    if store is None or model is None:
        REQUEST_LATENCY.observe(time.time() - start_time)
        return {"error": "Model or feature store not initialized"}

    features_request = [
        "subs_profile_fv:months_active",
        "subs_profile_fv:monthly_fee",
        "subs_profile_fv:paperless_billing",
        "subs_profile_fv:plan_stream_tv",
        "subs_profile_fv:plan_stream_movies",
        "subs_profile_fv:net_service",
        "usage_agg_30d_fv:watch_hours_30d",
        "usage_agg_30d_fv:avg_session_mins_7d",
        "usage_agg_30d_fv:unique_devices_30d",
        "usage_agg_30d_fv:skips_7d",
        "usage_agg_30d_fv:rebuffer_events_7d",
        "payments_agg_90d_fv:failed_payments_90d",
        "support_agg_90d_fv:support_tickets_90d",
        "support_agg_90d_fv:ticket_avg_resolution_hrs_90d",
    ]

    # 1) Récupérer les features online
    feature_dict = store.get_online_features(
        features=features_request,
        entity_rows=[{"user_id": payload.user_id}],
    ).to_dict()

    # 2) Construire X (1 ligne)
    X = pd.DataFrame({k: [v[0]] for k, v in feature_dict.items()})

    # 3) Gestion features manquantes
    if X.isnull().any().any():
        missing = X.columns[X.isnull().any()].tolist()
        REQUEST_LATENCY.observe(time.time() - start_time)
        return {
            "error": f"Missing features for user_id={payload.user_id}",
            "missing_features": missing,
        }

    # 4) Nettoyage: on enlève user_id si présent
    X = X.drop(columns=["user_id"], errors="ignore")

    # 5) Prédiction
    y_pred = model.predict(X)

    REQUEST_LATENCY.observe(time.time() - start_time)
    return {
        "user_id": payload.user_id,
        "prediction": int(y_pred[0]),
        "features_used": X.to_dict(orient="records")[0],
    }

@app.get("/metrics")
def metrics():
    # TODO: returnez une Response avec generate_latest() et CONTENT_TYPE_LATEST comme type de media
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)