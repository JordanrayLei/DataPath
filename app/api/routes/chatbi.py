from __future__ import annotations

import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_service_token
from app.config import get_settings
from app.db.models import ConversationContext, Metric
from app.db.session import get_db
from app.schemas.chatbi import (
    ChatbiAskRequest,
    ChatbiAskResponse,
    CompileRequest,
    CompileResponse,
    ContextLoadRequest,
    ContextLoadResponse,
    ContextSaveRequest,
    ContextSaveResponse,
    DslValidateRequest,
    DslValidateResponse,
    ExecuteRequest,
    ExecuteResponse,
    FeedbackSubmitRequest,
    FeedbackSubmitResponse,
    FeedbackListResponse,
    FeedbackStatusUpdateRequest,
    FeedbackStatusUpdateResponse,
    GoldenQuestionCreateFromFeedbackRequest,
    GoldenQuestionCreateResponse,
    GoldenQuestionEvaluationRequest,
    GoldenQuestionEvaluationResponse,
    GoldenQuestionListResponse,
    InterpretationGenerateRequest,
    InterpretationGenerateResponse,
    MetricCatalogDetailResponse,
    MetricCatalogListResponse,
    MetricDraftListResponse,
    MetricDraftResponse,
    MetricDraftUpsertRequest,
    MetricClosureValidationRequest,
    MetricClosureValidationResponse,
    MetricManagementOptionsResponse,
    MetricPublishRequest,
    MetricPublishResponse,
    MetricAdjudicationValidateRequest,
    MetricSemanticIndexResponse,
    SemanticScopeExampleListResponse,
    SemanticScopeExampleReplaceRequest,
    SemanticScopePreviewRequest,
    SemanticScopePreviewResponse,
    SemanticAmbiguityPolicyRequest,
    SemanticAmbiguityPolicyResponse,
    MetricRetrieveRequest,
    MetricRetrieveResponse,
    ProfileRequest,
    ProfileResponse,
    QueryDsl,
    ProductInteractionRequest,
    ReflectionRequest,
    ReflectionResponse,
)
from app.schemas.governance import (
    BusinessDomainModelUpdateRequest,
    BusinessDomainListResponse,
    BusinessDomainResponse,
    BusinessDomainTableBindingListResponse,
    BusinessDomainTableBindingRequest,
    BusinessDomainTableSelectionRequest,
    BusinessDomainUpsertRequest,
    MetricPreheatApplyRequest,
    MetricPreheatGenerateRequest,
    MetricPreheatResponse,
    PhysicalTableAssetListResponse,
    SchemaChangeImpactListResponse,
    WarehouseGovernanceRequest,
    WarehouseSourceListResponse,
    WarehouseSourceResponse,
    WarehouseSourceUpsertRequest,
)
from app.services.dsl_validator import validate_dsl
from app.services.metric_retrieval import retrieve_metrics
from app.services.query_policy import classify_safety_intent
from app.services.metric_adjudication import (
    issue_adjudication_token,
    validate_dify_metric_adjudication,
)
from app.services.query_compiler import CompilationError, compile_query
from app.services.query_executor import ExecutionError, execute_query
from app.services.result_profiler import ProfileError, profile_result
from app.services.interpretation_generator import (
    InterpretationGenerationError,
    generate_interpretation,
)
from app.services.reflection_validator import ReflectionError, validate_interpretation
from app.services.signing import sign_value
from app.services.chatbi_entrypoint import answer_chatbi_question
from app.services.feedback import (
    FeedbackError,
    list_feedback,
    submit_feedback,
    update_feedback_status,
)
from app.services.golden_questions import (
    GoldenQuestionError,
    create_golden_question_from_feedback,
    evaluate_golden_questions,
    list_golden_questions,
)
from app.services.metric_catalog import (
    MetricCatalogError,
    get_metric_detail,
    list_metric_catalog,
)
from app.services.metric_management import (
    MetricManagementError,
    list_metric_drafts,
    management_options,
    publish_metric_draft,
    save_metric_draft,
)
from app.services.metric_preheat import (
    MetricPreheatError,
    apply_preheat_proposal,
    generate_preheat_proposal,
)
from app.services.warehouse_governance import (
    WarehouseGovernanceError,
    list_business_domains,
    list_domain_table_bindings,
    list_physical_assets,
    list_schema_change_impacts,
    list_sources,
    publish_domain_table_bindings,
    publish_domain_semantic_model,
    publish_governance,
    save_governance,
    save_source,
    save_business_domain,
    save_domain_table_bindings,
    save_domain_table_selection,
    scan_source,
    update_domain_semantic_model,
)
from app.services.semantic_scope_management import (
    SemanticScopeManagementError,
    list_scope_examples,
    preview_scope_examples,
    replace_scope_examples,
    list_ambiguity_policy,
    replace_ambiguity_policy,
)
from app.services.metric_vector_index import refresh_metric_vector_index
from app.services.metric_closed_loop import (
    MetricClosureError,
    validate_metric_closure,
)
from app.services.join_graph_management import (
    JoinGraphManagementError, deprecate_relation, graph_snapshot, publish_draft,
    save_draft, scan_candidates, update_model, validate_draft,
)
from app.services.evaluation_reports import (
    EvaluationReportError,
    load_evaluation_report,
    load_evaluation_trends,
)
from app.services.product_analytics import (
    operations_summary,
    record_ask_events,
    record_product_interaction,
)
from app.services.access_policy import (
    POLICY_VERSION,
    issue_demo_identity_token,
    policy_for_operator,
    resolve_identity_token,
)


public_router = APIRouter(prefix="/api/chatbi")

router = APIRouter(
    prefix="/api/chatbi",
    dependencies=[Depends(require_service_token)],
)


def trace(request: Request) -> tuple[str, str]:
    return request.state.request_id, request.state.trace_id


def _operator_can_use_metrics(
    session: Session,
    workspace_id: str,
    operator_id: str,
    metric_ids: list[str],
) -> bool:
    settings = get_settings()
    identity = policy_for_operator(operator_id)
    if (
        workspace_id != settings.default_workspace_id
        or identity is None
        or not identity.can_query_business_data
        or not metric_ids
    ):
        return False
    domains = set(
        session.scalars(
            select(Metric.business_domain_id).where(Metric.id.in_(metric_ids))
        ).all()
    )
    return bool(domains) and len(domains) == 1 and domains.issubset(identity.allowed_domains)


@public_router.post("/ask", response_model=ChatbiAskResponse, tags=["Frontend"])
def ask_chatbi(
    payload: ChatbiAskRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> ChatbiAskResponse:
    request_id, trace_id = trace(request)
    started = time.perf_counter()
    try:
        response = answer_chatbi_question(session, payload, request_id, trace_id)
        record_ask_events(
            session,
            payload,
            response,
            round((time.perf_counter() - started) * 1000),
        )
        return response
    except CompilationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "QUERY_COMPILATION_FAILED", "message": str(error)},
        ) from error
    except ExecutionError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "QUERY_EXECUTION_FAILED", "message": str(error)},
        ) from error


@public_router.post("/feedback", response_model=FeedbackSubmitResponse, tags=["Frontend"])
def submit_chatbi_feedback(
    payload: FeedbackSubmitRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> FeedbackSubmitResponse:
    request_id, trace_id = trace(request)
    try:
        return submit_feedback(session, payload, request_id, trace_id)
    except FeedbackError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "FEEDBACK_NOT_ACCEPTED", "message": str(error)},
        ) from error


@public_router.get("/feedback", response_model=FeedbackListResponse, tags=["Frontend"])
def list_chatbi_feedback(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    workspace_id: str = "demo",
    feedback_status: Annotated[str, Query(alias="status")] = "ALL",
    limit: int = 50,
) -> FeedbackListResponse:
    request_id, trace_id = trace(request)
    try:
        return list_feedback(
            session,
            request_id,
            trace_id,
            workspace_id=workspace_id,
            feedback_status=feedback_status,
            limit=limit,
        )
    except FeedbackError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "FEEDBACK_LIST_FAILED", "message": str(error)},
        ) from error


@public_router.patch(
    "/feedback/{feedback_id}/status",
    response_model=FeedbackStatusUpdateResponse,
    tags=["Frontend"],
)
def update_chatbi_feedback_status(
    feedback_id: str,
    payload: FeedbackStatusUpdateRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> FeedbackStatusUpdateResponse:
    request_id, trace_id = trace(request)
    try:
        return update_feedback_status(
            session,
            feedback_id,
            payload.status,
            request_id,
            trace_id,
        )
    except FeedbackError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "FEEDBACK_STATUS_UPDATE_FAILED", "message": str(error)},
        ) from error


@public_router.get(
    "/golden-questions",
    response_model=GoldenQuestionListResponse,
    tags=["Frontend"],
)
def list_chatbi_golden_questions(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    workspace_id: str = "demo",
    golden_status: Annotated[str, Query(alias="status")] = "ACTIVE",
    limit: int = 50,
) -> GoldenQuestionListResponse:
    request_id, trace_id = trace(request)
    try:
        return list_golden_questions(
            session,
            request_id,
            trace_id,
            workspace_id=workspace_id,
            golden_status=golden_status,
            limit=limit,
        )
    except GoldenQuestionError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "GOLDEN_QUESTION_LIST_FAILED", "message": str(error)},
        ) from error


@public_router.post(
    "/golden-questions/from-feedback/{feedback_id}",
    response_model=GoldenQuestionCreateResponse,
    tags=["Frontend"],
)
def create_chatbi_golden_question_from_feedback(
    feedback_id: str,
    payload: GoldenQuestionCreateFromFeedbackRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> GoldenQuestionCreateResponse:
    request_id, trace_id = trace(request)
    try:
        return create_golden_question_from_feedback(
            session,
            feedback_id,
            payload,
            request_id,
            trace_id,
        )
    except GoldenQuestionError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "GOLDEN_QUESTION_CREATE_FAILED", "message": str(error)},
        ) from error


@public_router.post(
    "/golden-questions/evaluate",
    response_model=GoldenQuestionEvaluationResponse,
    tags=["Frontend"],
)
def evaluate_chatbi_golden_questions(
    payload: GoldenQuestionEvaluationRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> GoldenQuestionEvaluationResponse:
    request_id, trace_id = trace(request)
    try:
        return evaluate_golden_questions(session, payload, request_id, trace_id)
    except GoldenQuestionError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "GOLDEN_QUESTION_EVALUATION_FAILED", "message": str(error)},
        ) from error


@public_router.get(
    "/metrics/catalog",
    response_model=MetricCatalogListResponse,
    tags=["Frontend"],
)
def list_chatbi_metric_catalog(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    workspace_id: str = "demo",
    domain: str = "ALL",
    limit: int = 50,
    visibility: str = "runtime",
) -> MetricCatalogListResponse:
    request_id, trace_id = trace(request)
    try:
        return list_metric_catalog(
            session,
            request_id,
            trace_id,
            workspace_id=workspace_id,
            domain=domain,
            limit=limit,
            visibility=visibility,
        )
    except MetricCatalogError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "METRIC_CATALOG_LIST_FAILED", "message": str(error)},
        ) from error


@public_router.get(
    "/metrics/catalog/{metric_id}",
    response_model=MetricCatalogDetailResponse,
    tags=["Frontend"],
)
def get_chatbi_metric_detail(
    metric_id: str,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    workspace_id: str = "demo",
    visibility: str = "runtime",
) -> MetricCatalogDetailResponse:
    request_id, trace_id = trace(request)
    try:
        return get_metric_detail(
            session,
            metric_id,
            request_id,
            trace_id,
            workspace_id=workspace_id,
            visibility=visibility,
        )
    except MetricCatalogError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "METRIC_CATALOG_DETAIL_FAILED", "message": str(error)},
        ) from error


@public_router.get(
    "/metrics/manage/options",
    response_model=MetricManagementOptionsResponse,
    tags=["Metric Management"],
)
def get_metric_management_options(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    workspace_id: str = "demo",
) -> MetricManagementOptionsResponse:
    request_id, trace_id = trace(request)
    try:
        return management_options(session, request_id, trace_id, workspace_id)
    except MetricManagementError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "METRIC_OPTIONS_FAILED", "message": str(error)},
        ) from error


@public_router.get(
    "/governance/domains",
    response_model=BusinessDomainListResponse,
    tags=["Warehouse Governance"],
)
def get_business_domains(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    workspace_id: str = "demo",
) -> BusinessDomainListResponse:
    request_id, trace_id = trace(request)
    try:
        items = list_business_domains(session, workspace_id)
    except WarehouseGovernanceError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "DOMAIN_LIST_FAILED", "message": str(error)},
        ) from error
    return BusinessDomainListResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="SUCCESS",
        items=items,
    )


@public_router.put(
    "/governance/domains/{domain_id}",
    response_model=BusinessDomainResponse,
    tags=["Warehouse Governance"],
)
def put_business_domain(
    domain_id: str,
    payload: BusinessDomainUpsertRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> BusinessDomainResponse:
    request_id, trace_id = trace(request)
    try:
        domain = save_business_domain(session, domain_id, payload)
    except WarehouseGovernanceError as error:
        session.rollback()
        raise HTTPException(
            status_code=422,
            detail={"code": "DOMAIN_SAVE_FAILED", "message": str(error)},
        ) from error
    return BusinessDomainResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="SUCCESS",
        domain=domain,
    )


@public_router.get(
    "/governance/assets",
    response_model=PhysicalTableAssetListResponse,
    tags=["Warehouse Governance"],
)
def get_physical_table_assets(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    workspace_id: str = "demo",
) -> PhysicalTableAssetListResponse:
    request_id, trace_id = trace(request)
    try:
        items = list_physical_assets(session, workspace_id)
    except WarehouseGovernanceError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "PHYSICAL_ASSET_LIST_FAILED", "message": str(error)},
        ) from error
    return PhysicalTableAssetListResponse(
        request_id=request_id, trace_id=trace_id, status="SUCCESS", items=items
    )


@public_router.get(
    "/governance/schema-impacts",
    response_model=SchemaChangeImpactListResponse,
    tags=["Warehouse Governance"],
)
def get_schema_change_impacts(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    workspace_id: str = "demo",
    event_status: str = "ALL",
) -> SchemaChangeImpactListResponse:
    request_id, trace_id = trace(request)
    try:
        items = list_schema_change_impacts(session, workspace_id, event_status)
    except WarehouseGovernanceError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "SCHEMA_IMPACT_LIST_FAILED", "message": str(error)},
        ) from error
    return SchemaChangeImpactListResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="SUCCESS",
        items=items,
        summary={
            "total": len(items),
            "open": sum(item.status == "OPEN" for item in items),
            "critical": sum(item.severity == "CRITICAL" for item in items),
            "affected_models": len(
                {
                    model_id
                    for item in items
                    for model_id in item.impact.get("model_ids", [])
                }
            ),
            "affected_metrics": len(
                {
                    metric_id
                    for item in items
                    for metric_id in item.impact.get("metric_ids", [])
                }
            ),
        },
    )


@public_router.get(
    "/governance/domains/{domain_id}/table-bindings",
    response_model=BusinessDomainTableBindingListResponse,
    tags=["Warehouse Governance"],
)
def get_domain_table_bindings(
    domain_id: str,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    workspace_id: str = "demo",
) -> BusinessDomainTableBindingListResponse:
    request_id, trace_id = trace(request)
    try:
        items = list_domain_table_bindings(session, domain_id, workspace_id)
    except WarehouseGovernanceError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "DOMAIN_TABLE_BINDING_LIST_FAILED", "message": str(error)},
        ) from error
    return BusinessDomainTableBindingListResponse(
        request_id=request_id, trace_id=trace_id, status="SUCCESS", items=items
    )


@public_router.put(
    "/governance/domains/{domain_id}/table-bindings",
    response_model=BusinessDomainTableBindingListResponse,
    tags=["Warehouse Governance"],
)
def put_domain_table_bindings(
    domain_id: str,
    payload: BusinessDomainTableBindingRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> BusinessDomainTableBindingListResponse:
    request_id, trace_id = trace(request)
    try:
        items = save_domain_table_bindings(session, domain_id, payload)
    except WarehouseGovernanceError as error:
        session.rollback()
        raise HTTPException(
            status_code=422,
            detail={"code": "DOMAIN_TABLE_BINDING_SAVE_FAILED", "message": str(error)},
        ) from error
    return BusinessDomainTableBindingListResponse(
        request_id=request_id, trace_id=trace_id, status="SUCCESS", items=items
    )


@public_router.put(
    "/governance/domains/{domain_id}/table-selections",
    response_model=BusinessDomainTableBindingListResponse,
    tags=["Warehouse Governance"],
)
def put_domain_table_selections(
    domain_id: str,
    payload: BusinessDomainTableSelectionRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> BusinessDomainTableBindingListResponse:
    request_id, trace_id = trace(request)
    try:
        items = save_domain_table_selection(session, domain_id, payload)
    except WarehouseGovernanceError as error:
        session.rollback()
        raise HTTPException(
            status_code=422,
            detail={"code": "DOMAIN_TABLE_SELECTION_SAVE_FAILED", "message": str(error)},
        ) from error
    return BusinessDomainTableBindingListResponse(
        request_id=request_id, trace_id=trace_id, status="SUCCESS", items=items
    )


@public_router.put(
    "/governance/domains/{domain_id}/models/{binding_id}",
    response_model=BusinessDomainTableBindingListResponse,
    tags=["Warehouse Governance"],
)
def put_domain_semantic_model(
    domain_id: str,
    binding_id: str,
    payload: BusinessDomainModelUpdateRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> BusinessDomainTableBindingListResponse:
    request_id, trace_id = trace(request)
    try:
        update_domain_semantic_model(session, domain_id, binding_id, payload)
        items = list_domain_table_bindings(session, domain_id, payload.workspace_id)
    except WarehouseGovernanceError as error:
        session.rollback()
        raise HTTPException(
            status_code=422,
            detail={"code": "DOMAIN_MODEL_SAVE_FAILED", "message": str(error)},
        ) from error
    return BusinessDomainTableBindingListResponse(
        request_id=request_id, trace_id=trace_id, status="SUCCESS", items=items
    )


@public_router.post(
    "/governance/domains/{domain_id}/models/{binding_id}/publish",
    response_model=BusinessDomainTableBindingListResponse,
    tags=["Warehouse Governance"],
)
def post_domain_semantic_model_publish(
    domain_id: str,
    binding_id: str,
    payload: MetricPreheatGenerateRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> BusinessDomainTableBindingListResponse:
    request_id, trace_id = trace(request)
    try:
        publish_domain_semantic_model(
            session, domain_id, binding_id, payload.workspace_id
        )
        items = list_domain_table_bindings(session, domain_id, payload.workspace_id)
    except WarehouseGovernanceError as error:
        session.rollback()
        raise HTTPException(
            status_code=422,
            detail={"code": "DOMAIN_MODEL_PUBLISH_FAILED", "message": str(error)},
        ) from error
    return BusinessDomainTableBindingListResponse(
        request_id=request_id, trace_id=trace_id, status="SUCCESS", items=items
    )


@public_router.post(
    "/governance/domains/{domain_id}/table-bindings/publish",
    response_model=BusinessDomainTableBindingListResponse,
    tags=["Warehouse Governance"],
)
def post_domain_table_bindings_publish(
    domain_id: str,
    payload: MetricPreheatGenerateRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> BusinessDomainTableBindingListResponse:
    request_id, trace_id = trace(request)
    try:
        items = publish_domain_table_bindings(session, domain_id, payload.workspace_id)
    except WarehouseGovernanceError as error:
        session.rollback()
        raise HTTPException(
            status_code=422,
            detail={"code": "DOMAIN_TABLE_BINDING_PUBLISH_FAILED", "message": str(error)},
        ) from error
    return BusinessDomainTableBindingListResponse(
        request_id=request_id, trace_id=trace_id, status="SUCCESS", items=items
    )


@public_router.get(
    "/governance/sources",
    response_model=WarehouseSourceListResponse,
    tags=["Warehouse Governance"],
)
def get_warehouse_sources(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    workspace_id: str = "demo",
) -> WarehouseSourceListResponse:
    request_id, trace_id = trace(request)
    return WarehouseSourceListResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="SUCCESS",
        items=list_sources(session, workspace_id),
    )


@public_router.put(
    "/governance/sources/{source_id}",
    response_model=WarehouseSourceResponse,
    tags=["Warehouse Governance"],
)
def put_warehouse_source(
    source_id: str,
    payload: WarehouseSourceUpsertRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> WarehouseSourceResponse:
    request_id, trace_id = trace(request)
    try:
        source = save_source(session, source_id, payload)
    except WarehouseGovernanceError as error:
        session.rollback()
        raise HTTPException(status_code=422, detail={"code": "SOURCE_SAVE_FAILED", "message": str(error)}) from error
    return WarehouseSourceResponse(request_id=request_id, trace_id=trace_id, status="SUCCESS", source=source)


@public_router.post(
    "/governance/sources/{source_id}/scan",
    response_model=WarehouseSourceResponse,
    tags=["Warehouse Governance"],
)
def post_warehouse_scan(
    source_id: str,
    payload: MetricPreheatGenerateRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> WarehouseSourceResponse:
    request_id, trace_id = trace(request)
    try:
        source = scan_source(session, source_id, payload.workspace_id)
    except (WarehouseGovernanceError, RuntimeError) as error:
        session.rollback()
        raise HTTPException(status_code=422, detail={"code": "SOURCE_SCAN_FAILED", "message": str(error)}) from error
    return WarehouseSourceResponse(request_id=request_id, trace_id=trace_id, status="SUCCESS", source=source)


@public_router.put(
    "/governance/sources/{source_id}/confirmation",
    response_model=WarehouseSourceResponse,
    tags=["Warehouse Governance"],
)
def put_warehouse_confirmation(
    source_id: str,
    payload: WarehouseGovernanceRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> WarehouseSourceResponse:
    request_id, trace_id = trace(request)
    try:
        source = save_governance(session, source_id, payload)
    except WarehouseGovernanceError as error:
        session.rollback()
        raise HTTPException(status_code=422, detail={"code": "SOURCE_CONFIRM_FAILED", "message": str(error)}) from error
    return WarehouseSourceResponse(request_id=request_id, trace_id=trace_id, status="SUCCESS", source=source)


@public_router.post(
    "/governance/sources/{source_id}/publish",
    response_model=WarehouseSourceResponse,
    tags=["Warehouse Governance"],
)
def post_warehouse_publish(
    source_id: str,
    payload: MetricPreheatGenerateRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> WarehouseSourceResponse:
    request_id, trace_id = trace(request)
    try:
        source = publish_governance(session, source_id, payload.workspace_id)
    except WarehouseGovernanceError as error:
        session.rollback()
        raise HTTPException(status_code=422, detail={"code": "SOURCE_PUBLISH_FAILED", "message": str(error)}) from error
    return WarehouseSourceResponse(request_id=request_id, trace_id=trace_id, status="SUCCESS", source=source)


@public_router.get(
    "/metrics/manage/drafts",
    response_model=MetricDraftListResponse,
    tags=["Metric Management"],
)
def get_metric_drafts(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    workspace_id: str = "demo",
) -> MetricDraftListResponse:
    request_id, trace_id = trace(request)
    try:
        return list_metric_drafts(session, request_id, trace_id, workspace_id)
    except MetricManagementError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "METRIC_DRAFT_LIST_FAILED", "message": str(error)},
        ) from error


@public_router.put(
    "/metrics/manage/drafts/{metric_id}",
    response_model=MetricDraftResponse,
    tags=["Metric Management"],
)
def put_metric_draft(
    metric_id: str,
    payload: MetricDraftUpsertRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> MetricDraftResponse:
    if metric_id != payload.metric_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "METRIC_ID_MISMATCH", "message": "路径和请求中的指标 ID 不一致。"},
        )
    request_id, trace_id = trace(request)
    try:
        return save_metric_draft(session, payload, request_id, trace_id)
    except MetricManagementError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "METRIC_DRAFT_INVALID", "message": str(error)},
        ) from error


@public_router.post(
    "/metrics/manage/drafts/{metric_id}/preheat/generate",
    response_model=MetricPreheatResponse,
    tags=["Metric Management"],
)
def post_metric_preheat_generate(
    metric_id: str,
    payload: MetricPreheatGenerateRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> MetricPreheatResponse:
    request_id, trace_id = trace(request)
    try:
        proposal = generate_preheat_proposal(session, metric_id)
    except MetricPreheatError as error:
        session.rollback()
        raise HTTPException(status_code=422, detail={"code": "PREHEAT_GENERATE_FAILED", "message": str(error)}) from error
    return MetricPreheatResponse(
        request_id=request_id, trace_id=trace_id, status="SUCCESS", metric_id=metric_id, proposal=proposal
    )


@public_router.post(
    "/metrics/manage/drafts/{metric_id}/preheat/apply",
    response_model=MetricPreheatResponse,
    tags=["Metric Management"],
)
def post_metric_preheat_apply(
    metric_id: str,
    payload: MetricPreheatApplyRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> MetricPreheatResponse:
    request_id, trace_id = trace(request)
    try:
        proposal = apply_preheat_proposal(session, metric_id, payload)
    except MetricPreheatError as error:
        session.rollback()
        raise HTTPException(status_code=422, detail={"code": "PREHEAT_APPLY_FAILED", "message": str(error)}) from error
    return MetricPreheatResponse(
        request_id=request_id, trace_id=trace_id, status="SUCCESS", metric_id=metric_id, proposal=proposal
    )


@public_router.post(
    "/metrics/manage/drafts/{metric_id}/closure-validation",
    response_model=MetricClosureValidationResponse,
    tags=["Metric Management"],
)
def post_metric_closure_validation(
    metric_id: str,
    payload: MetricClosureValidationRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> MetricClosureValidationResponse:
    request_id, trace_id = trace(request)
    try:
        return validate_metric_closure(
            session, metric_id, payload, request_id, trace_id
        )
    except (MetricClosureError, MetricManagementError, GoldenQuestionError) as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "METRIC_CLOSURE_FAILED", "message": str(error)},
        ) from error


@public_router.post(
    "/metrics/manage/drafts/{metric_id}/publish",
    response_model=MetricPublishResponse,
    tags=["Metric Management"],
)
def post_metric_publish(
    metric_id: str,
    payload: MetricPublishRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> MetricPublishResponse:
    request_id, trace_id = trace(request)
    try:
        return publish_metric_draft(
            session, metric_id, request_id, trace_id, payload.workspace_id
        )
    except MetricManagementError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "METRIC_PUBLISH_FAILED", "message": str(error)},
        ) from error


@public_router.post(
    "/metrics/manage/drafts/{metric_id}/prelaunch-publish",
    response_model=MetricPublishResponse,
    tags=["Metric Management"],
)
def post_metric_prelaunch_publish(
    metric_id: str,
    payload: MetricPublishRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> MetricPublishResponse:
    """Publish AI-preheated semantics before any query or feedback is recorded."""

    request_id, trace_id = trace(request)
    try:
        return publish_metric_draft(
            session,
            metric_id,
            request_id,
            trace_id,
            payload.workspace_id,
            prelaunch_bootstrap=True,
        )
    except MetricManagementError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "PRELAUNCH_PUBLISH_FAILED", "message": str(error)},
        ) from error


@public_router.post(
    "/metrics/manage/semantic-index/{metric_id}/refresh",
    response_model=MetricSemanticIndexResponse,
    tags=["Metric Management"],
)
def post_metric_semantic_index_refresh(
    metric_id: str,
    payload: MetricPublishRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> MetricSemanticIndexResponse:
    request_id, trace_id = trace(request)
    if payload.workspace_id != "demo":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "METRIC_INDEX_REFRESH_FAILED", "message": "workspace is not allowed"},
        )
    try:
        result = refresh_metric_vector_index(session, metric_id)
    except (ValueError, RuntimeError) as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "METRIC_INDEX_REFRESH_FAILED", "message": str(error)},
        ) from error
    return MetricSemanticIndexResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="SUCCESS",
        metric_id=metric_id,
        documents=int(result["documents"]),
        total_tokens=int(result["total_tokens"]),
        embedding_model=str(result["embedding_model"]),
    )


@public_router.get(
    "/metrics/manage/scope-examples/{business_domain_id}",
    response_model=SemanticScopeExampleListResponse,
    tags=["Metric Management"],
)
def get_semantic_scope_examples(
    business_domain_id: str,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    workspace_id: str = "demo",
) -> SemanticScopeExampleListResponse:
    request_id, trace_id = trace(request)
    try:
        return list_scope_examples(
            session,
            business_domain_id,
            workspace_id,
            request_id,
            trace_id,
        )
    except SemanticScopeManagementError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "SEMANTIC_SCOPE_LIST_FAILED", "message": str(error)},
        ) from error


@public_router.put(
    "/metrics/manage/scope-examples/{business_domain_id}",
    response_model=SemanticScopeExampleListResponse,
    tags=["Metric Management"],
)
def put_semantic_scope_examples(
    business_domain_id: str,
    payload: SemanticScopeExampleReplaceRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> SemanticScopeExampleListResponse:
    request_id, trace_id = trace(request)
    try:
        return replace_scope_examples(
            session,
            business_domain_id,
            payload,
            request_id,
            trace_id,
        )
    except SemanticScopeManagementError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "SEMANTIC_SCOPE_SAVE_FAILED", "message": str(error)},
        ) from error


@public_router.post(
    "/metrics/manage/scope-examples/{business_domain_id}/preview",
    response_model=SemanticScopePreviewResponse,
    tags=["Metric Management"],
)
def post_semantic_scope_preview(
    business_domain_id: str,
    payload: SemanticScopePreviewRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> SemanticScopePreviewResponse:
    request_id, trace_id = trace(request)
    try:
        return preview_scope_examples(
            session,
            business_domain_id,
            payload,
            request_id,
            trace_id,
        )
    except SemanticScopeManagementError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "SEMANTIC_SCOPE_PREVIEW_FAILED", "message": str(error)},
        ) from error


@public_router.get(
    "/metrics/manage/ambiguity-policy/{business_domain_id}",
    response_model=SemanticAmbiguityPolicyResponse,
    tags=["Metric Management"],
)
def get_semantic_ambiguity_policy(
    business_domain_id: str,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    workspace_id: str = "demo",
) -> SemanticAmbiguityPolicyResponse:
    request_id, trace_id = trace(request)
    try:
        return list_ambiguity_policy(
            session, business_domain_id, workspace_id, request_id, trace_id
        )
    except SemanticScopeManagementError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "SEMANTIC_AMBIGUITY_LIST_FAILED", "message": str(error)},
        ) from error


@public_router.put(
    "/metrics/manage/ambiguity-policy/{business_domain_id}",
    response_model=SemanticAmbiguityPolicyResponse,
    tags=["Metric Management"],
)
def put_semantic_ambiguity_policy(
    business_domain_id: str,
    payload: SemanticAmbiguityPolicyRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> SemanticAmbiguityPolicyResponse:
    request_id, trace_id = trace(request)
    try:
        return replace_ambiguity_policy(
            session, business_domain_id, payload, request_id, trace_id
        )
    except SemanticScopeManagementError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "SEMANTIC_AMBIGUITY_SAVE_FAILED", "message": str(error)},
        ) from error


def _join_graph_error(error: JoinGraphManagementError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={"code": "JOIN_GRAPH_MANAGEMENT_FAILED", "message": str(error)})


@public_router.get("/join-graph", response_model=dict[str, Any], tags=["Join Graph Management"])
def get_join_graph(session: Annotated[Session, Depends(get_db)], workspace_id: str = "demo") -> dict[str, Any]:
    try: return graph_snapshot(session, workspace_id)
    except JoinGraphManagementError as error: raise _join_graph_error(error) from error


@public_router.put("/join-graph/drafts/{relation_id}", response_model=dict[str, Any], tags=["Join Graph Management"])
def put_join_graph_draft(relation_id: str, payload: dict[str, Any], session: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    try: return save_draft(session, relation_id, payload)
    except JoinGraphManagementError as error: session.rollback(); raise _join_graph_error(error) from error


@public_router.patch("/join-graph/models/{model_id}", response_model=dict[str, Any], tags=["Join Graph Management"])
def patch_join_graph_model(model_id: str, payload: dict[str, Any], session: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    try: return update_model(session, model_id, payload)
    except JoinGraphManagementError as error: session.rollback(); raise _join_graph_error(error) from error


@public_router.post("/join-graph/drafts/{relation_id}/validate", response_model=dict[str, Any], tags=["Join Graph Management"])
def post_join_graph_validate(relation_id: str, session: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    try: return validate_draft(session, relation_id)
    except JoinGraphManagementError as error: session.rollback(); raise _join_graph_error(error) from error


@public_router.post("/join-graph/drafts/{relation_id}/publish", response_model=dict[str, Any], tags=["Join Graph Management"])
def post_join_graph_publish(relation_id: str, session: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    try: return publish_draft(session, relation_id)
    except JoinGraphManagementError as error: session.rollback(); raise _join_graph_error(error) from error


@public_router.post("/join-graph/relations/{relation_id}/deprecate", response_model=dict[str, Any], tags=["Join Graph Management"])
def post_join_graph_deprecate(relation_id: str, session: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    try: return deprecate_relation(session, relation_id)
    except JoinGraphManagementError as error: session.rollback(); raise _join_graph_error(error) from error


@public_router.post("/join-graph/scan", response_model=dict[str, Any], tags=["Join Graph Management"])
def post_join_graph_scan(session: Annotated[Session, Depends(get_db)], domain: str = "production_benchmark") -> dict[str, Any]:
    try: return scan_candidates(session, domain)
    except JoinGraphManagementError as error: raise _join_graph_error(error) from error


@public_router.get(
    "/demo/identity-token",
    response_model=dict[str, Any],
    tags=["Frontend"],
)
def get_demo_identity_token(request: Request, role_id: str = "public_viewer") -> dict[str, Any]:
    if get_settings().environment != "development":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DEMO_IDENTITY_DISABLED", "message": "演示身份签发已关闭。"},
        )
    role_to_operator = {
        "public_viewer": "public_demo_user",
        "production_analyst": "production_analyst",
        "production_tenant_1": "production_tenant_1",
        "production_tenant_2": "production_tenant_2",
        "metric_admin": "metric_admin",
    }
    operator_id = role_to_operator.get(role_id)
    if operator_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "DEMO_ROLE_INVALID", "message": "演示角色不存在。"},
        )
    request_id, trace_id = trace(request)
    return {
        "request_id": request_id,
        "trace_id": trace_id,
        "status": "SUCCESS",
        "role_id": role_id,
        "operator_id": operator_id,
        "identity_token": issue_demo_identity_token(operator_id),
        "expires_in": get_settings().demo_identity_ttl_seconds,
    }


@public_router.get(
    "/operations/summary",
    response_model=dict[str, Any],
    tags=["Frontend"],
)
def get_chatbi_operations_summary(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    workspace_id: str = "demo",
    window_days: int = 30,
) -> dict[str, Any]:
    request_id, trace_id = trace(request)
    try:
        summary = operations_summary(session, workspace_id, window_days)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "OPERATIONS_WINDOW_INVALID", "message": str(error)},
        ) from error
    return {"request_id": request_id, "trace_id": trace_id, **summary}


@public_router.post(
    "/operations/interactions",
    response_model=dict[str, Any],
    tags=["Frontend"],
)
def post_chatbi_product_interaction(
    payload: ProductInteractionRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    request_id, trace_id = trace(request)
    try:
        event = record_product_interaction(
            session,
            workspace_id=payload.workspace_id,
            conversation_id=payload.conversation_id,
            query_id=payload.query_id,
            event_name=payload.event_name,
            trace_id=trace_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "PRODUCT_INTERACTION_INVALID", "message": str(error)},
        ) from error
    return {
        "request_id": request_id,
        "trace_id": trace_id,
        "status": "RECORDED",
        "event_id": event.event_id,
        "event_name": event.event_name,
    }


@public_router.get(
    "/evaluations/latest",
    response_model=dict[str, Any],
    tags=["Frontend"],
)
def get_chatbi_latest_evaluation_report(
    request: Request,
    report_name: str | None = None,
) -> dict[str, Any]:
    request_id, trace_id = trace(request)
    try:
        report = load_evaluation_report(report_name)
    except EvaluationReportError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EVALUATION_REPORT_NOT_FOUND", "message": str(error)},
        ) from error
    return {
        "request_id": request_id,
        "trace_id": trace_id,
        **report,
    }


@public_router.get(
    "/evaluations/trends",
    response_model=dict[str, Any],
    tags=["Frontend"],
)
def list_chatbi_evaluation_trends(
    request: Request,
    limit: int = 20,
) -> dict[str, Any]:
    request_id, trace_id = trace(request)
    try:
        trends = load_evaluation_trends(limit=limit)
    except EvaluationReportError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "EVALUATION_TRENDS_INVALID", "message": str(error)},
        ) from error
    return {
        "request_id": request_id,
        "trace_id": trace_id,
        **trends,
    }


@router.post("/context/load", response_model=ContextLoadResponse, tags=["Context"])
def load_context(
    payload: ContextLoadRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> ContextLoadResponse:
    settings = get_settings()
    request_id, trace_id = trace(request)
    identity = resolve_identity_token(payload.identity_token)
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_IDENTITY_TOKEN", "message": "身份令牌无效。"},
        )
    if payload.workspace_id != settings.default_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "WORKSPACE_NOT_ALLOWED", "message": "工作空间不可访问。"},
        )
    if not identity.can_query_business_data:
        return ContextLoadResponse(
            request_id=request_id, trace_id=trace_id, context_ok=False,
            blocked_reason_code="BUSINESS_DATA_NOT_ALLOWED",
            operator_id=identity.operator_id, allowed_domains=list(identity.allowed_domains),
            role_ids=[identity.role_id], row_policy_token="", last_query_context={},
        )
    if payload.biz_domain and payload.biz_domain not in identity.allowed_domains:
        return ContextLoadResponse(
            request_id=request_id, trace_id=trace_id, context_ok=False,
            blocked_reason_code="BUSINESS_DOMAIN_NOT_ALLOWED",
            operator_id=identity.operator_id, allowed_domains=list(identity.allowed_domains),
            role_ids=[identity.role_id], row_policy_token="", last_query_context={},
        )
    safety = classify_safety_intent(payload.query) if payload.query else None
    if safety and safety.blocked:
        return ContextLoadResponse(
            request_id=request_id, trace_id=trace_id, context_ok=False,
            blocked_reason_code=safety.reason_code,
            operator_id=identity.operator_id, allowed_domains=list(identity.allowed_domains),
            role_ids=[identity.role_id], row_policy_token="", last_query_context={},
        )

    context = session.scalar(
        select(ConversationContext).where(
            ConversationContext.workspace_id == payload.workspace_id,
            ConversationContext.conversation_id == payload.conversation_id,
        )
    )
    last_query_context = (
        context.last_query_context
        if context is not None and context.operator_id == identity.operator_id
        else {"metrics": [], "dimensions": [], "filters": [], "time_range": None}
    )
    policy_value = (
        f"{payload.workspace_id}|{identity.operator_id}|{identity.role_id}|"
        f"{POLICY_VERSION}|{identity.scope_fingerprint}"
    )
    return ContextLoadResponse(
        request_id=request_id,
        trace_id=trace_id,
        operator_id=identity.operator_id,
        allowed_domains=list(identity.allowed_domains),
        role_ids=[identity.role_id],
        row_policy_token=f"rpt.v1.{sign_value(policy_value, settings.signing_secret)}",
        last_query_context=last_query_context,
    )


@router.post("/context/save", response_model=ContextSaveResponse, tags=["Context"])
def save_context(
    payload: ContextSaveRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> ContextSaveResponse:
    """Persist only a validated, successfully executed semantic query context."""

    settings = get_settings()
    policy = policy_for_operator(payload.operator_id)
    if (
        payload.workspace_id != settings.default_workspace_id
        or policy is None
        or payload.biz_domain not in policy.allowed_domains
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "QUERY_CONTEXT_NOT_ALLOWED", "message": "查询上下文不可访问。"},
        )
    try:
        dsl = QueryDsl.model_validate(payload.dsl)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "CONTEXT_DSL_INVALID", "message": "只能保存已校验 DSL。"},
        ) from error
    metric_ids = [item.metric_id for item in dsl.metrics]
    if not _operator_can_use_metrics(
        session, payload.workspace_id, payload.operator_id, metric_ids
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "QUERY_CONTEXT_NOT_ALLOWED", "message": "指标上下文不可访问。"},
        )
    metrics = {
        item.id: item
        for item in session.scalars(select(Metric).where(Metric.id.in_(metric_ids))).all()
    }
    snapshot = {
        "biz_domain": payload.biz_domain,
        "metrics": [
            {
                "metric_id": item.metric_id,
                "metric_version": item.metric_version,
                "display_name": metrics[item.metric_id].name,
            }
            for item in dsl.metrics
        ],
        "dimensions": [item.model_dump(mode="json") for item in dsl.dimensions],
        "filters": [item.model_dump(mode="json") for item in dsl.filters],
        "time_range": dsl.time_range.model_dump(mode="json"),
        "intent": dsl.intent,
    }
    context = session.scalar(
        select(ConversationContext).where(
            ConversationContext.workspace_id == payload.workspace_id,
            ConversationContext.conversation_id == payload.conversation_id,
        )
    )
    if context is None:
        context = ConversationContext(
            workspace_id=payload.workspace_id,
            conversation_id=payload.conversation_id,
            operator_id=payload.operator_id,
            last_query_context=snapshot,
        )
        session.add(context)
    else:
        context.operator_id = payload.operator_id
        context.last_query_context = snapshot
    session.commit()
    request_id, trace_id = trace(request)
    return ContextSaveResponse(
        request_id=request_id,
        trace_id=trace_id,
        status="SUCCESS",
        conversation_id=payload.conversation_id,
        message="已保存本轮指标、维度、筛选和时间上下文。",
    )


@router.post("/metrics/retrieve", response_model=MetricRetrieveResponse, tags=["Metrics"])
def metrics_retrieve(
    payload: MetricRetrieveRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> MetricRetrieveResponse:
    settings = get_settings()
    request_id, trace_id = trace(request)
    identity = policy_for_operator(payload.operator_id)
    if payload.workspace_id != settings.default_workspace_id or identity is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "QUERY_CONTEXT_NOT_ALLOWED", "message": "查询上下文不可访问。"},
        )
    if not identity.can_query_business_data or payload.biz_domain not in identity.allowed_domains:
        return MetricRetrieveResponse(
            request_id=request_id,
            trace_id=trace_id,
            gate_status="BLOCKED",
            mentions=[],
            reason_codes=["QUERY_CONTEXT_NOT_ALLOWED"],
            clarification_message="当前角色无权访问该业务域。",
        )
    safety = classify_safety_intent(payload.query)
    if safety.blocked:
        return MetricRetrieveResponse(
            request_id=request_id,
            trace_id=trace_id,
            gate_status="BLOCKED",
            mentions=[],
            reason_codes=["UNSAFE_QUERY_INTENT"],
            clarification_message=safety.message,
        )
    retrieval = retrieve_metrics(session, payload, request_id, trace_id)
    return retrieval.model_copy(
        update={"adjudication_token": issue_adjudication_token(payload, retrieval)}
    )


@router.post(
    "/metrics/adjudicate/validate",
    response_model=MetricRetrieveResponse,
    tags=["Metrics"],
)
def validate_metric_adjudication(
    payload: MetricAdjudicationValidateRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> MetricRetrieveResponse:
    settings = get_settings()
    identity = policy_for_operator(payload.operator_id)
    if (
        payload.workspace_id != settings.default_workspace_id
        or identity is None
        or not identity.can_query_business_data
        or payload.biz_domain not in identity.allowed_domains
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "QUERY_CONTEXT_NOT_ALLOWED", "message": "查询上下文不可访问。"},
        )
    return validate_dify_metric_adjudication(session, payload)


@router.post("/dsl/validate", response_model=DslValidateResponse, tags=["DSL"])
def dsl_validate(
    payload: DslValidateRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> DslValidateResponse:
    metric_ids = [
        str(item.get("metric_id"))
        for item in (payload.dsl.get("metrics") or [])
        if isinstance(item, dict) and item.get("metric_id")
    ]
    if not _operator_can_use_metrics(
        session, payload.workspace_id, payload.operator_id, metric_ids
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "QUERY_CONTEXT_NOT_ALLOWED", "message": "查询上下文不可访问。"},
        )
    request_id, trace_id = trace(request)
    return validate_dsl(
        session,
        payload.dsl,
        payload.row_policy_context,
        request_id,
        trace_id,
        payload.query,
    )


@router.post("/query/compile", response_model=CompileResponse, tags=["Query"])
def query_compile(
    payload: CompileRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> CompileResponse:
    metric_ids = [item.metric_id for item in payload.dsl.metrics]
    if not _operator_can_use_metrics(
        session, payload.workspace_id, payload.operator_id, metric_ids
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "QUERY_CONTEXT_NOT_ALLOWED", "message": "查询上下文不可访问。"},
        )
    request_id, trace_id = trace(request)
    validation = validate_dsl(
        session,
        payload.dsl.model_dump(mode="json", exclude_none=True),
        payload.permission_context,
        request_id,
        trace_id,
    )
    if validation.status != "VALID":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "DSL_NOT_VALID",
                "message": validation.message,
                "issues": [item.model_dump() for item in validation.issues],
            },
        )
    try:
        return compile_query(
            session,
            payload.dsl,
            payload.workspace_id,
            payload.operator_id,
            request_id,
            trace_id,
        )
    except CompilationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "QUERY_COMPILE_BLOCKED", "message": str(error)},
        ) from error


@router.post("/query/execute", response_model=ExecuteResponse, tags=["Query"])
def query_execute(
    payload: ExecuteRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> ExecuteResponse:
    request_id, trace_id = trace(request)
    try:
        return execute_query(
            session,
            payload,
            idempotency_key,
            request_id,
            trace_id,
        )
    except ExecutionError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "QUERY_NOT_EXECUTABLE", "message": str(error)},
        ) from error


@router.post("/result/profile", response_model=ProfileResponse, tags=["Result"])
def result_profile(
    payload: ProfileRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> ProfileResponse:
    request_id, trace_id = trace(request)
    try:
        return profile_result(session, payload, request_id, trace_id)
    except ProfileError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "RESULT_NOT_PROFILEABLE", "message": str(error)},
        ) from error


@router.post(
    "/interpretation/generate",
    response_model=InterpretationGenerateResponse,
    tags=["Interpretation"],
)
def interpretation_generate(
    payload: InterpretationGenerateRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> InterpretationGenerateResponse:
    request_id, trace_id = trace(request)
    try:
        return generate_interpretation(session, payload, request_id, trace_id)
    except InterpretationGenerationError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "INTERPRETATION_NOT_GENERATABLE", "message": str(error)},
        ) from error


@router.post("/reflection/validate", response_model=ReflectionResponse, tags=["Reflection"])
def reflection_validate(
    payload: ReflectionRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> ReflectionResponse:
    request_id, trace_id = trace(request)
    try:
        return validate_interpretation(session, payload, request_id, trace_id)
    except ReflectionError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "INTERPRETATION_NOT_VALIDATABLE", "message": str(error)},
        ) from error
