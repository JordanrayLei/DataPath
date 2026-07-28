from __future__ import annotations

import re
from dataclasses import dataclass

POLICY_VERSION = "1.2"


@dataclass(frozen=True)
class SafetyDecision:
    blocked: bool
    reason_code: str = ""
    message: str = ""


_WRITE_ACTION_PATTERNS = (
    re.compile(r"(?:删除|删掉|清空|清除|销毁|移除).{0,12}(?:表|数据|记录|订单|客户|字段|支付|退款|用户|身份)"),
    re.compile(r"(?:修改|更新|写入|插入|新增|重写).{0,12}(?:数据|记录|订单|客户|状态|字段|表|支付|退款|库存|金额|用户|身份)"),
    re.compile(r"(?:表|数据|记录|订单|客户|状态|字段|支付|退款|库存|金额|用户|身份).{0,16}(?:删除|清空|清除|修改|更新|写入|插入|新增|重写|设为|改为|改成|调整为|变更为)"),
    re.compile(r"(?:执行|进行|发起)?.{0,6}(?:删除|清空|修改|更新|写入|插入|新增)(?:操作|命令)"),
    re.compile(
        r"(?<![a-z])(?:drop|delete|truncate|alter|update|insert|create|grant|revoke)(?![a-z])",
        re.IGNORECASE,
    ),
)
_SENSITIVE_EXPORT_PATTERN = re.compile(
    r"(?:批量)?(?:导出|下载|打包|dump|export).{0,16}(?:所有|全部|全量|明细|客户信息|个人信息|身份信息|手机号|证件号码|身份证号|地址)"
    r"|(?:所有|全部|全量|批量).{0,16}(?:客户信息|个人信息|身份信息|手机号|证件号码|身份证号|地址).{0,12}(?:导出|下载|打包)",
    re.IGNORECASE,
)
_ACCESS_BYPASS_PATTERN = re.compile(
    r"(?:绕过|绕开|规避|跳过|忽略|关闭|禁用|取消|撤销|撤掉).{0,10}"
    r"(?:权限|鉴权|审批|安全规则|安全限制|访问控制|只读限制|查询限制|租户隔离)"
)
_CREDENTIAL_OR_PRIVILEGE_PATTERN = re.compile(
    r"(?:获取|查看|读取|导出|提供|给我|授予|申请).{0,18}"
    r"(?:密码|口令|密钥|token|凭据|超级用户|管理员权限|数据库权限|root权限)"
    r"|(?:数据库|超级用户|管理员|root).{0,12}(?:密码|口令|密钥|token|凭据|权限)"
    r"|(?:提升|升级|变更|设置|设).{0,16}(?:为|成)?(?:超级用户|系统管理员|数据库管理员|管理员|root)",
    re.IGNORECASE,
)


def classify_safety_intent(query: str) -> SafetyDecision:
    """Classify actions that must never reach metric retrieval or SQL compilation."""

    normalized = " ".join(query.strip().split())
    if _ACCESS_BYPASS_PATTERN.search(normalized):
        return SafetyDecision(
            blocked=True,
            reason_code="ACCESS_CONTROL_BYPASS",
            message="不能绕过权限、鉴权或安全规则。",
        )
    if _CREDENTIAL_OR_PRIVILEGE_PATTERN.search(normalized):
        return SafetyDecision(
            blocked=True,
            reason_code="CREDENTIAL_OR_PRIVILEGE_REQUEST",
            message="不能获取凭据、管理员权限或数据库高权限。",
        )
    if any(pattern.search(normalized) for pattern in _WRITE_ACTION_PATTERNS):
        return SafetyDecision(
            blocked=True,
            reason_code="DANGEROUS_WRITE_ACTION",
            message="当前产品只支持只读分析，不能执行删除、修改或其他写操作。",
        )
    if _SENSITIVE_EXPORT_PATTERN.search(normalized):
        return SafetyDecision(
            blocked=True,
            reason_code="SENSITIVE_BULK_EXPORT",
            message="当前产品不允许批量导出客户明细或其他敏感信息。",
        )
    return SafetyDecision(blocked=False)


_GENERIC_ANALYSIS_PATTERNS = (
    re.compile(r"^(?:最近)?(?:经营|业务|整体)?(?:情况|表现)(?:怎么样)?$", re.IGNORECASE),
    re.compile(r"^(?:经营|业务|整体)(?:怎么样|如何)$"),
    re.compile(r"^(?:最近)?(?:有)?什么变化$"),
    re.compile(r"^(?:帮我)?(?:看|看看|看一下|查|查一下)?(?:金额|数据|核心数据)$"),
    re.compile(r"^(?:帮我)?分析一下$"),
    re.compile(r"^哪个最高$"),
    re.compile(
        r"^(?:看|看看|看一下|查|查一下)?(?:生产评测|生产环境|复杂仓库)?"
        r"(?:经营情况|业务趋势|表现|金额|数据|核心数据|指标)(?:怎么样|如何)?$"
    ),
    re.compile(r"^(?:帮我)?分析(?:一下)?(?:生产评测|生产环境|复杂仓库)$"),
    re.compile(r"^最近数据如何$"),
    re.compile(
        r"^(?:请)?(?:帮我)?(?:看|看看|查看|分析|查|查一下)?(?:一下)?"
        r"(?:生产评测|生产环境|复杂仓库|整体业务|经营业务|生产经营|订单业务|履约业务|支付业务)?"
        r"(?:整体|核心|最近|当前)?"
        r"(?:经营情况|业务情况|情况|表现|趋势|数据|指标|金额|效率)"
        r"(?:怎么样|如何|有什么变化)?$"
    ),
    re.compile(
        r"^(?:请)?(?:帮我)?(?:看|看看|查看|分析|查|查一下|计算|汇总|给出)(?:一下)?"
        r"(?:整体|核心|最近|当前)"
        r"(?:生产经营|订单业务|履约业务|支付业务|整体业务)"
        r"(?:情况|表现|趋势|数据|指标|金额|效率)(?:的结果)?$"
    ),
)

_PRODUCTION_STAGED_METRIC_PATTERN = re.compile(
    r"订单直接连接明细后统计订单金额"
    r"|按促销查看订单金额"
    r"|按多级类目查看商品净收入",
    re.IGNORECASE,
)

_PRODUCTION_STAGED_SCD2_PATTERNS = (
    re.compile(r"(?:scd\s*2|as[-_ ]?of|缓慢变化维|历史版本|生效版本)", re.IGNORECASE),
    re.compile(
        r"(?:下单|成交|支付|退款|发货)(?:时|当时|时点|发生时|那时|那一刻).{0,16}"
        r"(?:客户|商品|产品|分类|属性|版本)"
    ),
    re.compile(
        r"(?:客户|商品|产品|分类|属性|版本).{0,16}"
        r"(?:下单|成交|支付|退款|发货)(?:时|当时|时点|发生时|那时|那一刻)"
    ),
    re.compile(
        r"(?:当前|现在).{0,16}(?:客户|商品|产品|分类|属性|版本).{0,24}"
        r"(?:下单|成交|支付|退款|发货)(?:时|当时|时点|那时|那一刻)"
    ),
)


def is_underspecified_metric_query(query: str) -> bool:
    """Return true when an in-domain analysis request lacks a usable metric."""

    normalized = re.sub(r"[\s？?！!。,.，]+", "", query).casefold()
    return any(pattern.fullmatch(normalized) for pattern in _GENERIC_ANALYSIS_PATTERNS)


def is_explicitly_staged_production_query(query: str) -> bool:
    """Detect governed production metrics that are known but not publishable yet."""

    normalized = re.sub(r"[\s？?！!。,.，]+", "", query).casefold()
    return bool(
        _PRODUCTION_STAGED_METRIC_PATTERN.search(normalized)
        or any(pattern.search(normalized) for pattern in _PRODUCTION_STAGED_SCD2_PATTERNS)
    )
