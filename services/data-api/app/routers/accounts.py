"""
Data API - 资金账户与流水查询

GET /api/accounts
GET /api/transactions
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from sqlalchemy.orm import Session

from libs.ledger import LedgerService
from libs.ledger.contracts import AccountFilter, TransactionFilter

from ..deps import get_db, get_tenant_id, get_account_id_optional
from ..serializers import dto_to_dict

router = APIRouter(prefix="/api", tags=["accounts"])


def _parse_dt(s: Optional[str]):
    if not s:
        return None
    from datetime import datetime
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


@router.get("/accounts")
def list_accounts(
    tenant_id: int = Depends(get_tenant_id),
    account_id: Optional[int] = Depends(get_account_id_optional),
    currency: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """资金账户列表（Ledger 层，按租户/账户/币种）"""
    filt = AccountFilter(
        tenant_id=tenant_id,
        account_id=account_id,
        currency=currency,
        status=status,
        limit=limit,
        offset=offset,
    )
    svc = LedgerService(db)
    accounts = svc.list_accounts(filt)
    return {"success": True, "data": [dto_to_dict(a) for a in accounts], "total": len(accounts)}


@router.get("/transactions")
def list_transactions(
    tenant_id: int = Depends(get_tenant_id),
    account_id: Optional[int] = Depends(get_account_id_optional),
    ledger_account_id: Optional[str] = Query(None),
    currency: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    source_id: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None),
    start_time: Optional[str] = Query(None, description="ISO datetime"),
    end_time: Optional[str] = Query(None, description="ISO datetime"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """账务流水列表（按租户、账户、类型、时间范围）。返回 data[].remark 由业务写入，无固定枚举，详见 docs/api/LEDGER_REMARKS.md。"""
    filt = TransactionFilter(
        tenant_id=tenant_id,
        account_id=account_id,
        ledger_account_id=ledger_account_id,
        currency=currency,
        transaction_type=transaction_type,
        source_type=source_type,
        source_id=source_id,
        symbol=symbol,
        start_time=_parse_dt(start_time),
        end_time=_parse_dt(end_time),
        limit=limit,
        offset=offset,
    )
    svc = LedgerService(db)
    transactions = svc.list_transactions(filt)
    return {"success": True, "data": [dto_to_dict(t) for t in transactions], "total": len(transactions)}
