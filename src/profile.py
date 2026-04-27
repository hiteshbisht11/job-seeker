"""Candidate profile — drives fit scoring and Excel summary sheet."""

PROFILE = {
    "name": "Hitesh Bisht",
    "current_role": "MLOps Engineer @ Zzazz.ai (Bangalore)",
    "experience_years": 2.0,
    "education": "B.Tech CSE, Graphic Era Hill University, 2024 (CGPA 8.5)",
    "location": "Bangalore, India (open to Hyderabad / Pune / Gurgaon / Remote)",
    "core_strengths": [
        "Production MLOps: 30+ models, ~500K inference req/day, 99.5% availability",
        "Observability: Prometheus, Grafana, OpenTelemetry, Alertmanager",
        "Containerization: Docker, Kubernetes (HPA, autoscaling 2->20 pods)",
        "Inference optimization: 75% latency reduction, 42% infra cost cut (GPU->CPU)",
        "ML systems: PyTorch, TensorFlow, scikit-learn, LightGBM, XGBoost, ONNX",
        "Data infra: Kafka/Redpanda, RabbitMQ, Redis, Feast feature store, Airflow",
        "Backend: Python (FastAPI), Java (Spring Boot), REST APIs, PL/SQL",
        "Web crawling at scale: Selenium, NetworkX, 50K-70K docs/week",
    ],
    "target_roles": [
        "MLOps Engineer / ML Platform Engineer (I / II / Associate)",
        "ML Infrastructure Engineer",
        "ML Engineer (production / applied)",
        "Backend Engineer (data / ML-adjacent teams)",
        "Site Reliability Engineer (ML / data platforms)",
        "Data Platform Engineer",
    ],
    "fit_scoring_rubric": {
        "exact_mlops_match": "85-95 — direct MLOps/ML platform role, 0-3 yrs, India",
        "strong_adjacent": "75-84 — ML infra, applied ML, backend on ML team",
        "good_transfer": "65-74 — backend / SRE / data eng with ML adjacency",
        "stretch": "50-64 — top-tier brand, very competitive bar, or partial stack overlap",
    },
}
