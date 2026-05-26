"""Mock in-memory knowledge base used by the knowledge_base_search tool.

In a real production research bot this would be backed by a vector store
(e.g. pgvector, Pinecone, OpenAI File Search). For demo/trace purposes we
ship a small corpus and score documents with simple keyword overlap.
"""

KB_DOCS: list[dict[str, str]] = [
    {
        "id": "kb-001",
        "title": "Internal: Programming language adoption survey 2024",
        "content": (
            "Annual internal developer survey covering 14,000 engineers. "
            "Python remained the most-used language (62% daily use), followed by "
            "JavaScript/TypeScript (58%) and Go (24%). Rust adoption grew "
            "fastest year-over-year (+9pp). C++ usage declined slightly. "
            "Top reasons cited for Python: data/AI workloads, scripting, and "
            "library ecosystem."
        ),
    },
    {
        "id": "kb-002",
        "title": "Internal: AI/ML infra stack 2025",
        "content": (
            "Most teams run inference on a mix of GPU and CPU. PyTorch is the "
            "dominant framework (78% of teams). JAX usage is concentrated in "
            "research orgs (12%). TensorFlow is in maintenance mode for most "
            "new projects. Quantization (int8, fp8) is now standard in "
            "production serving."
        ),
    },
    {
        "id": "kb-003",
        "title": "Internal: Web framework usage",
        "content": (
            "React continues to lead among frontend frameworks. Next.js is "
            "the default meta-framework for new projects. Svelte and Solid "
            "are growing in early-stage teams. On the backend, FastAPI "
            "(Python) and Hono (TypeScript) are the fastest-growing choices."
        ),
    },
    {
        "id": "kb-004",
        "title": "Internal: Cloud cost trends",
        "content": (
            "AWS remains the dominant cloud (62% of spend). GPU compute is "
            "the single largest line item for AI teams. Cost-per-token for "
            "frontier LLMs dropped ~70% between Q1 2024 and Q1 2025. "
            "Inference fleets are migrating toward smaller distilled models "
            "where quality permits."
        ),
    },
    {
        "id": "kb-005",
        "title": "Internal: Developer productivity tools",
        "content": (
            "AI coding assistants are now used by 84% of engineers weekly. "
            "Most-cited benefits: boilerplate generation, test scaffolding, "
            "and code review. Reported time savings: 10-25% on greenfield "
            "code, smaller on legacy maintenance. Trust calibration remains "
            "the top concern."
        ),
    },
    {
        "id": "kb-006",
        "title": "Internal: Data engineering stack",
        "content": (
            "Snowflake and BigQuery dominate warehousing. dbt is the "
            "near-universal transformation layer. Apache Iceberg adoption is "
            "rising for open table formats. DuckDB has emerged as a default "
            "for local analytics and prototyping."
        ),
    },
]
