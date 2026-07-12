"""Generate and persist metric semantic embeddings with DashScope."""

from app.db.session import SessionLocal
from app.services.metric_vector_index import rebuild_metric_vector_index


def main() -> None:
    with SessionLocal() as session:
        result = rebuild_metric_vector_index(session)
    print(
        f"Indexed {result['documents']} semantic documents for {result['metrics']} metrics "
        f"and {result['scope_examples']} scope examples "
        f"with {result['total_tokens']} input tokens"
    )


if __name__ == "__main__":
    main()
