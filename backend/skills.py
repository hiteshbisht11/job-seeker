"""Skill taxonomy for resume parsing and job matching.

Each entry maps a canonical skill name to a list of regex-friendly aliases that
can appear in resume text or job descriptions. Aliases are matched
case-insensitively with word boundaries.
"""

SKILLS: dict[str, list[str]] = {
    # ---- Programming languages ----
    "Python":      ["python"],
    "Java":        [r"\bjava\b"],
    "JavaScript":  ["javascript", "node.js", "nodejs"],
    "TypeScript":  ["typescript"],
    "Go":          [r"\bgolang\b", r"\bgo\b"],
    "Rust":        [r"\brust\b"],
    "C++":         [r"c\+\+", "cpp"],
    "Scala":       ["scala"],
    "Ruby":        [r"\bruby\b"],
    "Kotlin":      ["kotlin"],
    "PL/SQL":      [r"pl[/\s]?sql", "plsql"],

    # ---- Databases ----
    "PostgreSQL":      ["postgres", "postgresql"],
    "MySQL":           ["mysql"],
    "MongoDB":         ["mongodb", "mongo"],
    "Redis":           ["redis"],
    "Elasticsearch":   ["elasticsearch", "elastic search", r"\belastic\b"],
    "Oracle":          [r"\boracle\b"],
    "Snowflake":       ["snowflake"],
    "BigQuery":        ["bigquery"],
    "DynamoDB":        ["dynamodb"],
    "Cassandra":       ["cassandra"],

    # ---- ML / Data ----
    "PyTorch":         ["pytorch"],
    "TensorFlow":      ["tensorflow"],
    "Scikit-learn":    ["scikit-learn", "sklearn", "scikit learn"],
    "Pandas":          ["pandas"],
    "NumPy":           ["numpy"],
    "LightGBM":        ["lightgbm", "light gbm"],
    "XGBoost":         ["xgboost"],
    "ONNX":            ["onnx"],
    "Hugging Face":    ["hugging face", "huggingface"],
    "MLflow":          ["mlflow"],
    "Feast":           [r"\bfeast\b"],
    "Spark":           [r"\bspark\b", "pyspark"],
    "Databricks":      ["databricks"],
    "Triton":          [r"\btriton\b"],

    # ---- Containerization / Orchestration ----
    "Docker":          ["docker"],
    "Kubernetes":      ["kubernetes", r"\bk8s\b"],
    "Helm":            [r"\bhelm\b"],

    # ---- CI/CD ----
    "GitLab CI":       ["gitlab pipelines", "gitlab ci", "gitlab-ci"],
    "Jenkins":         ["jenkins"],
    "GitHub Actions":  ["github actions"],
    "ArgoCD":          ["argocd", "argo cd"],

    # ---- Workflow orchestration / pipelines ----
    "Airflow":         ["airflow"],
    "Dagster":         ["dagster"],
    "Prefect":         [r"\bprefect\b"],
    "Kubeflow":        ["kubeflow"],

    # ---- Observability ----
    "Prometheus":      ["prometheus"],
    "Grafana":         ["grafana"],
    "OpenTelemetry":   ["opentelemetry", "open telemetry", "otel"],
    "Datadog":         ["datadog"],
    "Loki":            [r"\bloki\b"],
    "Tempo":           [r"\btempo\b"],
    "Alertmanager":    ["alertmanager"],

    # ---- Messaging / Streaming ----
    "Kafka":           ["kafka", "redpanda"],
    "RabbitMQ":        ["rabbitmq", "rabbit mq"],
    "Pub/Sub":         ["pub/sub", "pubsub"],

    # ---- Web / API frameworks ----
    "FastAPI":         ["fastapi"],
    "Flask":           ["flask"],
    "Django":          ["django"],
    "Spring Boot":     ["spring boot", "springboot"],
    "Express":         ["express"],
    "REST APIs":       ["rest api", "rest apis", "restful"],
    "gRPC":            [r"\bgrpc\b"],
    "GraphQL":         ["graphql"],

    # ---- Cloud ----
    "AWS":             [r"\baws\b", "amazon web services"],
    "GCP":             [r"\bgcp\b", "google cloud"],
    "Azure":           [r"\bazure\b"],
    "OCI":             [r"\boci\b", "oracle cloud"],
    "SageMaker":       ["sagemaker"],
    "Vertex AI":       ["vertex ai"],
    "EKS":             [r"\beks\b"],

    # ---- MLOps concepts ----
    "Model serving":   ["model serving", "model deployment", "inference api"],
    "Feature store":   ["feature store", "feature stores"],
    "A/B testing":     [r"a/b testing", "ab testing"],
    "Shadow deployment":["shadow deployment", "shadow deploy"],
    "Canary":          [r"\bcanary\b"],
    "HPA":             [r"\bhpa\b", "horizontal pod autoscal"],

    # ---- Data scraping / automation ----
    "Selenium":        ["selenium"],
    "Playwright":      ["playwright"],
    "BeautifulSoup":   ["beautifulsoup", "beautiful soup"],
    "NetworkX":        ["networkx"],

    # ---- Misc ----
    "Linux":           [r"\blinux\b"],
    "Git":             [r"\bgit\b"],
    "Bash":            [r"\bbash\b", "shell scripting"],
    "Terraform":       ["terraform"],
}


# Title hints — used to detect role aspirations from resume + recent titles.
TITLE_HINTS: dict[str, list[str]] = {
    "MLOps":           ["mlops", "ml ops", "ml platform", "ml infra", "ml infrastructure"],
    "ML Engineer":     ["machine learning engineer", "ml engineer"],
    "Data Engineer":   ["data engineer"],
    "Data Scientist":  ["data scientist"],
    "Backend":         ["backend engineer", "backend developer", "back-end"],
    "SRE":             [r"\bsre\b", "site reliability"],
    "DevOps":          ["devops"],
    "Software Engineer": ["software engineer", "software developer", r"\bsde\b"],
    "AI Engineer":     ["ai engineer"],
}
