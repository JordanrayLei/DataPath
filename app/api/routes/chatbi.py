from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_service_token
from app.config import get_settings
from app.db.models import ConversationContext
from app.db.session import get_db
from app.schemas.chatbi import (
    ChatbiAskRequest,
    ChatbiAskResponse,
    CompileRequest,
    CompileResponse,
    ContextLoadRequest,
    ContextLoadResponse,
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
    MetricManagementOptionsResponse,
    MetricPublishRequest,
    MetricPublishResponse,
    MetricRetrieveRequest,
    MetricRetrieveResponse,
    ProfileRequest,
    ProfileResponse,
    ReflectionRequest,
    ReflectionResponse,
)
from app.services.dsl_validator import validate_dsl
from app.services.metric_retrieval import retrieve_metrics
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
from app.services.join_graph_management import (
    JoinGraphManagementError, deprecate_relation, graph_snapshot, publish_draft,
    save_draft, scan_candidates, update_model, validate_draft,
)
from app.services.evaluation_reports import (
    EvaluationReportError,
    load_evaluation_report,
    load_evaluation_trends,
)


public_router = APIRouter(prefix="/api/chatbi")

router = APIRouter(
    prefix="/api/chatbi",
    dependencies=[Depends(require_service_token)],
)


def trace(request: Request) -> tuple[str, str]:
    return request.state.request_id, request.state.trace_id


@public_router.post("/ask", response_model=ChatbiAskResponse, tags=["Frontend"])
def ask_chatbi(
    payload: ChatbiAskRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> ChatbiAskResponse:
    request_id, trace_id = trace(request)
    try:
        return answer_chatbi_question(session, payload, request_id, trace_id)
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
) -> MetricCatalogDetailResponse:
    request_id, trace_id = trace(request)
    try:
        return get_metric_detail(session, metric_id, request_id, trace_id, workspace_id=workspace_id)
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
def post_join_graph_scan(session: Annotated[Session, Depends(get_db)], domain: str = "sales") -> dict[str, Any]:
    try: return scan_candidates(session, domain)
    except JoinGraphManagementError as error: raise _join_graph_error(error) from error


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
    if payload.identity_token != settings.demo_identity_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_IDENTITY_TOKEN", "message": "身份令牌无效。"},
        )
    if payload.workspace_id != settings.default_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "WORKSPACE_NOT_ALLOWED", "message": "工作空间不可访问。"},
        )

    context = session.scalar(
        select(ConversationContext).where(
            ConversationContext.workspace_id == payload.workspace_id,
            ConversationContext.conversation_id == payload.conversation_id,
        )
    )
    last_query_context = (
        context.last_query_context
        if context is not None
        else {"metrics": [], "dimensions": [], "filters": [], "time_range": None}
    )
    request_id, trace_id = trace(request)
    policy_value = f"{payload.workspace_id}|{settings.default_operator_id}|public_viewer"
    return ContextLoadResponse(
        request_id=request_id,
        trace_id=trace_id,
        operator_id=settings.default_operator_id,
        allowed_domains=["sales", "advertising"],
        role_ids=["public_viewer"],
        row_policy_token=f"rpt.v1.{sign_value(policy_value, settings.signing_secret)}",
        last_query_context=last_query_context,
    )


@router.post("/metrics/retrieve", response_model=MetricRetrieveResponse, tags=["Metrics"])
def metrics_retrieve(
    payload: MetricRetrieveRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> MetricRetrieveResponse:
    settings = get_settings()
    if payload.workspace_id != settings.default_workspace_id or payload.operator_id != settings.default_operator_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "QUERY_CONTEXT_NOT_ALLOWED", "message": "查询上下文不可访问。"},
        )
    request_id, trace_id = trace(request)
    return retrieve_metrics(session, payload, request_id, trace_id)


@router.post("/dsl/validate", response_model=DslValidateResponse, tags=["DSL"])
def dsl_validate(
    payload: DslValidateRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> DslValidateResponse:
    settings = get_settings()
    if payload.workspace_id != settings.default_workspace_id or payload.operator_id != settings.default_operator_id:
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
    )


@router.post("/query/compile", response_model=CompileResponse, tags=["Query"])
def query_compile(
    payload: CompileRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> CompileResponse:
    settings = get_settings()
    if payload.workspace_id != settings.default_workspace_id or payload.operator_id != settings.default_operator_id:
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
