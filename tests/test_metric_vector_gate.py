from app.services.metric_retrieval import is_vector_scope_rejected


def test_scope_gate_rejects_when_boundary_evidence_is_close() -> None:
    assert is_vector_scope_rejected(0.70, 0.66, 0.64, 0.06)


def test_scope_gate_keeps_clear_in_domain_match() -> None:
    assert not is_vector_scope_rejected(0.83, 0.66, 0.64, 0.06)


def test_scope_gate_ignores_weak_boundary_evidence() -> None:
    assert not is_vector_scope_rejected(0.70, 0.60, 0.64, 0.06)
