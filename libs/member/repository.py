"""
Member Repository - 会员、账户、策略绑定数据访问
"""

from typing import Optional, List
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import User, ExchangeAccount, StrategyBinding, Strategy, TenantStrategy


class MemberRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---------- User ----------
    def get_user_by_id(self, user_id: int, tenant_id: Optional[int] = None) -> Optional[User]:
        q = self.db.query(User).filter(User.id == user_id)
        if tenant_id is not None:
            q = q.filter(User.tenant_id == tenant_id)
        return q.first()

    def get_user_by_email(self, email: str, tenant_id: int) -> Optional[User]:
        return self.db.query(User).filter(
            User.tenant_id == tenant_id,
            User.email == email,
        ).first()

    def get_user_by_invite_code(self, invite_code: str) -> Optional[User]:
        return self.db.query(User).filter(User.invite_code == invite_code).first()

    def invite_code_exists(self, code: str) -> bool:
        return self.db.query(User).filter(User.invite_code == code).first() is not None

    def list_users(
        self,
        tenant_id: int,
        page: int = 1,
        limit: int = 20,
        email: Optional[str] = None,
        invite_code: Optional[str] = None,
        status: Optional[int] = None,
    ) -> tuple[List[User], int]:
        q = self.db.query(User).filter(User.tenant_id == tenant_id)
        if email:
            q = q.filter(User.email.like(f"%{email}%"))
        if invite_code:
            q = q.filter(User.invite_code == invite_code)
        if status is not None:
            q = q.filter(User.status == status)
        total = q.count()
        items = q.order_by(User.id.desc()).offset((page - 1) * limit).limit(limit).all()
        return items, total

    def create_user(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user

    def update_user(self, user: User) -> User:
        self.db.merge(user)
        self.db.flush()
        return user

    def count_invitees(self, user_id: int) -> int:
        return self.db.query(User).filter(User.inviter_id == user_id).count()

    def get_direct_members(self, user_id: int, page: int = 1, limit: int = 20) -> tuple[List[User], int]:
        q = self.db.query(User).filter(User.inviter_id == user_id)
        total = q.count()
        items = q.order_by(User.id.desc()).offset((page - 1) * limit).limit(limit).all()
        return items, total

    def get_all_sub_user_ids(self, user_id: int) -> List[int]:
        """递归获取所有下级用户 ID"""
        result = []
        current = [user_id]
        while current:
            next_ids = (
                self.db.query(User.id).filter(User.inviter_id.in_(current)).all()
            )
            next_ids = [r[0] for r in next_ids]
            result.extend(next_ids)
            current = next_ids
        return result

    # ---------- ExchangeAccount ----------
    def get_account_by_id(self, account_id: int, user_id: Optional[int] = None) -> Optional[ExchangeAccount]:
        q = self.db.query(ExchangeAccount).filter(ExchangeAccount.id == account_id)
        if user_id is not None:
            q = q.filter(ExchangeAccount.user_id == user_id)
        return q.first()

    def get_accounts_by_user(self, user_id: int) -> List[ExchangeAccount]:
        return self.db.query(ExchangeAccount).filter(
            ExchangeAccount.user_id == user_id,
            ExchangeAccount.status == 1,
        ).all()

    def get_account_by_user_exchange(
        self,
        user_id: int,
        exchange: str,
        account_type: str = "futures",
    ) -> Optional[ExchangeAccount]:
        return self.db.query(ExchangeAccount).filter(
            ExchangeAccount.user_id == user_id,
            ExchangeAccount.exchange == exchange,
            ExchangeAccount.account_type == account_type,
        ).first()

    def create_account(self, acc: ExchangeAccount) -> ExchangeAccount:
        self.db.add(acc)
        self.db.flush()
        return acc

    def update_account(self, acc: ExchangeAccount) -> ExchangeAccount:
        self.db.merge(acc)
        self.db.flush()
        return acc

    def list_accounts_by_execution_node(
        self, execution_node_id: int
    ) -> List[ExchangeAccount]:
        """按执行节点列出交易所账户（用于中心向节点发起同步）"""
        return self.db.query(ExchangeAccount).filter(
            ExchangeAccount.execution_node_id == execution_node_id,
            ExchangeAccount.status == 1,
        ).all()

    def sum_futures_balance_by_user_ids(self, user_ids: List[int]) -> Decimal:
        if not user_ids:
            return Decimal("0")
        r = self.db.query(func.coalesce(func.sum(ExchangeAccount.futures_balance), 0)).filter(
            ExchangeAccount.user_id.in_(user_ids),
            ExchangeAccount.status == 1,
        ).scalar()
        return Decimal(str(r or 0))

    # ---------- StrategyBinding ----------
    def get_binding(self, user_id: int, account_id: int, strategy_code: str) -> Optional[StrategyBinding]:
        return self.db.query(StrategyBinding).filter(
            StrategyBinding.user_id == user_id,
            StrategyBinding.account_id == account_id,
            StrategyBinding.strategy_code == strategy_code,
        ).first()

    def get_bindings_by_user(self, user_id: int) -> List[StrategyBinding]:
        return self.db.query(StrategyBinding).filter(StrategyBinding.user_id == user_id).all()

    def create_binding(self, b: StrategyBinding) -> StrategyBinding:
        self.db.add(b)
        self.db.flush()
        return b

    def update_binding(self, b: StrategyBinding) -> StrategyBinding:
        self.db.merge(b)
        self.db.flush()
        return b

    def get_bindings_by_strategy_code(self, strategy_code: str) -> List[StrategyBinding]:
        return self.db.query(StrategyBinding).filter(
            StrategyBinding.strategy_code == strategy_code,
            StrategyBinding.status == 1,
        ).all()

    def list_bindings_by_tenant(
        self,
        tenant_id: int,
        strategy_code: Optional[str] = None,
        status: Optional[int] = None,
        limit: int = 200,
    ) -> List[StrategyBinding]:
        """按租户查绑定（通过 User.tenant_id 过滤）"""
        q = self.db.query(StrategyBinding).join(User, StrategyBinding.user_id == User.id).filter(
            User.tenant_id == tenant_id,
        )
        if strategy_code:
            q = q.filter(StrategyBinding.strategy_code == strategy_code)
        if status is not None:
            q = q.filter(StrategyBinding.status == status)
        return q.order_by(StrategyBinding.id.desc()).limit(limit).all()

    # ---------- Strategy ----------
    def list_strategies(
        self,
        status: Optional[int] = 1,
        show_to_user: Optional[bool] = None,
    ) -> List[Strategy]:
        q = self.db.query(Strategy)
        if status is not None:
            q = q.filter(Strategy.status == status)
        if show_to_user is not None:
            q = q.filter(Strategy.show_to_user == (1 if show_to_user else 0))
        return q.order_by(Strategy.id).all()

    def get_strategy_by_code(self, code: str) -> Optional[Strategy]:
        return self.db.query(Strategy).filter(Strategy.code == code).first()

    def get_strategy_by_id(self, strategy_id: int) -> Optional[Strategy]:
        return self.db.query(Strategy).filter(Strategy.id == strategy_id).first()

    def update_strategy(self, strategy: Strategy) -> Strategy:
        self.db.merge(strategy)
        self.db.flush()
        return strategy

    # ---------- TenantStrategy (租户策略实例) ----------
    def list_tenant_strategies(
        self,
        tenant_id: int,
        status: Optional[int] = None,
    ) -> List[TenantStrategy]:
        q = self.db.query(TenantStrategy).filter(TenantStrategy.tenant_id == tenant_id)
        if status is not None:
            q = q.filter(TenantStrategy.status == status)
        return q.order_by(TenantStrategy.sort_order.asc(), TenantStrategy.id.asc()).all()

    def get_tenant_strategy(self, tenant_id: int, strategy_id: int) -> Optional[TenantStrategy]:
        return self.db.query(TenantStrategy).filter(
            TenantStrategy.tenant_id == tenant_id,
            TenantStrategy.strategy_id == strategy_id,
        ).first()

    def get_tenant_strategy_by_id(self, instance_id: int, tenant_id: Optional[int] = None) -> Optional[TenantStrategy]:
        q = self.db.query(TenantStrategy).filter(TenantStrategy.id == instance_id)
        if tenant_id is not None:
            q = q.filter(TenantStrategy.tenant_id == tenant_id)
        return q.first()

    def create_tenant_strategy(self, ts: TenantStrategy) -> TenantStrategy:
        self.db.add(ts)
        self.db.flush()
        return ts

    def update_tenant_strategy(self, ts: TenantStrategy) -> TenantStrategy:
        self.db.merge(ts)
        self.db.flush()
        return ts

    def delete_tenant_strategy(self, ts: TenantStrategy) -> None:
        self.db.delete(ts)
        self.db.flush()
