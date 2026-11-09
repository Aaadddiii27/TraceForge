# Architecture Diagrams

This directory contains architecture diagrams for the AI Runtime & Evaluation Platform.

## System Architecture

```mermaid
graph TB
    subgraph Client["Client Layer"]
        Browser["Browser\n(React + TypeScript SPA)"]
        CLI["CLI / curl / SDK"]
    end

    subgraph API["API Layer (FastAPI)"]
        REST["REST API\n/api/v1/*"]
        MW["Middleware\n(CORS, Auth, Rate Limit,\nLogging, OTel)"]
    end

    subgraph Engine["Execution Engine"]
        TaskSvc["Task Service\n(submit, fetch, list)"]
        Executor["Step Executor\n(state machine)"]
        Retry["Retry & Timeout\nManager"]
        Idempotency["Idempotency\nChecker"]
    end

    subgraph Registry["Tool Registry"]
        Calculator["Calculator\nTool"]
        TextProc["Text Processor\nTool"]
        KnowledgeBase["Knowledge Base\nTool (read-only)"]
        MockTool["Mock Tool\n(deterministic)"]
    end

    subgraph Providers["Model Provider Abstraction"]
        MockProv["Mock Provider\n(default, no API key)"]
        OpenAIProv["OpenAI Adapter\n(optional, env-gated)"]
        GeminiProv["Gemini Adapter\n(optional, env-gated)"]
    end

    subgraph Evaluation["Evaluation Engine"]
        DatasetSvc["Dataset Service"]
        RunSvc["Run Service"]
        Assertions["Assertion Engine\n(exact, contains,\nregex, numeric, schema)"]
        Aggregator["Metrics Aggregator\n(pass rate, latency,\nregression diff)"]
    end

    subgraph Observability["Observability"]
        OTel["OpenTelemetry\nTracing"]
        Prom["Prometheus\nMetrics"]
        StructLog["Structured\nLogging (structlog)"]
    end

    subgraph Data["Data Layer"]
        PG[("PostgreSQL\n(primary store)")]
        Redis[("Redis\n(queue, cache, pub/sub)")]
    end

    subgraph Ops["Operations"]
        PromServer["Prometheus\nServer"]
        Grafana["Grafana\nDashboard"]
    end

    Browser -->|HTTP| REST
    CLI -->|HTTP| REST
    REST --> MW
    MW --> TaskSvc
    MW --> DatasetSvc
    MW --> RunSvc
    TaskSvc --> Idempotency
    TaskSvc --> Executor
    Executor --> Retry
    Executor --> Registry
    Executor --> Providers
    Calculator & TextProc & KnowledgeBase & MockTool --> Executor
    MockProv & OpenAIProv & GeminiProv --> Executor
    TaskSvc --> PG
    TaskSvc --> Redis
    Executor --> OTel
    Executor --> Prom
    Executor --> StructLog
    DatasetSvc --> PG
    RunSvc --> Executor
    RunSvc --> Assertions
    Assertions --> Aggregator
    Aggregator --> PG
    Prom --> PromServer
    PromServer --> Grafana
```

## Execution Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Pending: POST /api/v1/tasks

    Pending --> IdempotencyCheck: Task queued
    IdempotencyCheck --> Pending: Duplicate\n(return existing)
    IdempotencyCheck --> Running: Unique task

    Running --> StepExecution: Worker picks up

    state StepExecution {
        [*] --> LookupTool
        LookupTool --> CheckPermission
        CheckPermission --> EnforceTimeout
        EnforceTimeout --> ExecuteTool
        ExecuteTool --> ValidateOutput
        ValidateOutput --> RecordStep
        RecordStep --> [*]
    }

    StepExecution --> Running: Next step
    StepExecution --> Retrying: Tool error\n(retriable)
    Retrying --> StepExecution: Backoff elapsed
    Retrying --> Failed: Max retries\nexceeded

    Running --> Completed: All steps done
    Running --> Failed: Unrecoverable error
    Running --> TimedOut: Task timeout exceeded

    Completed --> [*]
    Failed --> [*]
    TimedOut --> [*]
```

## Data Model

```mermaid
erDiagram
    TASKS {
        uuid id PK
        string request_id UK
        string idempotency_key UK
        string status
        string model_provider
        jsonb tool_ids
        jsonb input_payload
        jsonb output_payload
        timestamp created_at
        timestamp started_at
        timestamp finished_at
        string error_message
        int retry_count
        int token_usage_input
        int token_usage_output
        float estimated_cost_usd
    }

    EXECUTION_STEPS {
        uuid id PK
        uuid task_id FK
        string step_name
        string status
        timestamp started_at
        timestamp finished_at
        jsonb input
        jsonb output
        string error
        int attempt_number
    }

    TOOLS {
        uuid id PK
        string name UK
        string description
        string version
        bool enabled
        jsonb input_schema
        jsonb output_schema
        string permission_level
        int timeout_seconds
    }

    EVALUATION_DATASETS {
        uuid id PK
        string name UK
        string description
        timestamp created_at
        timestamp updated_at
    }

    EVALUATION_CASES {
        uuid id PK
        uuid dataset_id FK
        jsonb input
        jsonb expected_output
        string[] tags
        timestamp created_at
    }

    EVALUATION_RUNS {
        uuid id PK
        uuid dataset_id FK
        string runtime_version
        string model_provider
        string status
        timestamp started_at
        timestamp finished_at
        jsonb config
    }

    EVALUATION_RESULTS {
        uuid id PK
        uuid run_id FK
        uuid case_id FK
        jsonb actual_output
        bool passed
        jsonb assertions
        float latency_ms
        string error
    }

    TASKS ||--o{ EXECUTION_STEPS : "has"
    EVALUATION_DATASETS ||--o{ EVALUATION_CASES : "contains"
    EVALUATION_DATASETS ||--o{ EVALUATION_RUNS : "evaluated by"
    EVALUATION_RUNS ||--o{ EVALUATION_RESULTS : "produces"
    EVALUATION_CASES ||--o{ EVALUATION_RESULTS : "tested by"
```

## Deployment (Docker Compose)

```mermaid
graph LR
    subgraph Host["Host Machine (Docker)"]
        subgraph Net["ai_runtime_net (bridge)"]
            FE["frontend\nnginx:3000"]
            BE["backend\nuvicorn:8000"]
            PG[("postgres\n:5432")]
            Redis[("redis\n:6379")]
            Prom["prometheus\n:9090"]
            Graf["grafana\n:3001"]
        end
    end

    User["User Browser"] -->|:3000| FE
    User -->|:8000| BE
    User -->|:3001| Graf
    FE -->|API calls via browser| BE
    BE --> PG
    BE --> Redis
    Prom -->|scrape :8000/api/v1/metrics| BE
    Graf -->|query| Prom
```
