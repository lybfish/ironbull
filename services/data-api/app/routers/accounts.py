"""
Data API - 资金账户与流水查询

GET /api/accounts
GET /api/transactions
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException

from sqlalchemy.orm import Session

from libs.ledger import LedgerService
from libs.ledger.contracts import AccountFilter, TransactionFilter
from libs.ledger.models import Account, Transaction

from ..deps import get_db, get_tenant_id, get_account_id_optional, get_current_admin
from ..serializers import dto_to_dict
from ..utils import parse_datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["accounts"])


@router.get("/accounts")
def list_accounts(
    tenant_id: int = Depends(get_tenant_id),
    account_id: Optional[int] = Depends(get_account_id_optional),
    currency: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _admin: dict = Depends(get_current_admin),
):
    """资金账户列表（Ledger 层，按租户/账户/币种）"""
    try:
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
        # 统计总数（去掉 limit/offset 条件）
        count_query = db.query(Account).filter(Account.tenant_id == tenant_id)
        if account_id is not None:
            count_query = count_query.filter(Account.account_id == account_id)
        if currency:
            count_query = count_query.filter(Account.currency == currency)
        if status:
            count_query = count_query.filter(Account.status == status)
        total = count_query.count()
        return {"success": True, "data": [dto_to_dict(a) for a in accounts], "total": total}
    except Exception as e:
        logger.exception("账户查询失败")
        raise HTTPException(status_code=500, detail=f"账户查询失败: {str(e)}")


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
    _admin: dict = Depends(get_current_admin),
):
    """账务流水列表（按租户、账户、类型、时间范围）。返回 data[].remark 由业务写入，无固定枚举，详见 docs/api/LEDGER_REMARKS.md。"""
    try:
        st = parse_datetime(start_time)
        et = parse_datetime(end_time)
        filt = TransactionFilter(
            tenant_id=tenant_id,
            account_id=account_id,
            ledger_account_id=ledger_account_id,
            currency=currency,
            transaction_type=transaction_type,
            source_type=source_type,
            source_id=source_id,
            symbol=symbol,
            start_time=st,
            end_time=et,
            limit=limit,
            offset=offset,
        )
        svc = LedgerService(db)
        transactions = svc.list_transactions(filt)
        # 统计总数
        count_query = db.query(Transaction).filter(Transaction.tenant_id == tenant_id)
        if account_id is not None:
            count_query = count_query.filter(Transaction.account_id == account_id)
        if ledger_account_id:
            count_query = count_query.filter(Transaction.ledger_account_id == ledger_account_id)
        if currency:
            count_query = count_query.filter(Transaction.currency == currency)
        if transaction_type:
            count_query = count_query.filter(Transaction.transaction_type == transaction_type)
        if source_type:
            count_query = count_query.filter(Transaction.source_type == source_type)
        if source_id:
            count_query = count_query.filter(Transaction.source_id == source_id)
        if symbol:
            count_query = count_query.filter(Transaction.symbol == symbol)
        if st:
            count_query = count_query.filter(Transaction.transaction_at >= st)
        if et:
            count_query = count_query.filter(Transaction.transaction_at <= et)
        total = count_query.count()
        return {"success": True, "data": [dto_to_dict(t) for t in transactions], "total": total}
    except Exception as e:
        logger.exception("流水查询失败")
        raise HTTPException(status_code=500, detail=f"流水查询失败: {str(e)}")
