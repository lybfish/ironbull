"""
Member Service - 会员业务逻辑

- 创建用户、邀请链路
- 绑定/解绑交易所账户
- 策略开启/关闭
- 按策略获取可执行账户（供 signal-monitor 等多账户执行使用）
"""

import hashlib
import random
import string
from dataclasses import dataclass
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session

from .models import User, ExchangeAccount, StrategyBinding, Strategy
from .repository import MemberRepository


@dataclass
class ExecutionTarget:
    """
    按策略绑定可执行目标：绑定 + 交易所账户凭证（仅服务端使用，勿暴露给前端）。
    用于 signal-monitor 等根据 strategy_code 查绑定后，对每个账户创建 LiveTrader 并执行。
    execution_node_id 非空时表示由该节点执行，空或 0 表示本机执行。
    """
    tenant_id: int
    account_id: int
    user_id: int
    exchange: str
    api_key: str
    api_secret: str
    passphrase: Optional[str]
    market_type: str  # spot / future
    binding_id: int
    strategy_code: str
    ratio: int  # 跟单比例 1-100
    execution_node_id: Optional[int] = None  # 执行节点ID，空/0=本机


def _generate_invite_code() -> str:
    """8 位数字邀请码"""
    return "".join(random.choices(string.digits, k=8))


def _hash_password(password: str) -> str:
    """与 old3 一致：MD5"""
    return hashlib.md5(password.encode()).hexdigest()


class MemberService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = MemberRepository(db)

    def get_root_user(self, tenant_id: int) -> Optional[User]:
        """获取租户的根用户"""
        from libs.tenant.repository import TenantRepository
        tr = TenantRepository(self.db)
        t = tr.get_by_id(tenant_id)
        if not t or not t.root_user_id:
            return None
        return self.repo.get_user_by_id(t.root_user_id, tenant_id)

    def get_user(self, user_id: int, tenant_id: Optional[int] = None) -> Optional[User]:
        return self.repo.get_user_by_id(user_id, tenant_id)

    def get_user_by_email(self, email: str, tenant_id: int) -> Optional[User]:
        return self.repo.get_user_by_email(email, tenant_id)

    def verify_login(self, tenant_id: int, email: str, password: str) -> Optional[User]:
        """验证登录：邮箱+密码，返回用户或 None。"""
        user = self.repo.get_user_by_email(email, tenant_id)
        if not user or not user.password_hash:
            return None
        if user.status != 1:
            return None
        if _hash_password(password) != user.password_hash:
            return None
        return user

    def create_user(
        self,
        tenant_id: int,
        email: str,
        password: str,
        inviter_id: Optional[int] = None,
        root_user_id: Optional[int] = None,
    ) -> Tuple[Optional[User], str]:
        """
        创建用户。返回 (user, error_msg)，error_msg 非空表示失败。
        """
        if self.repo.get_user_by_email(email, tenant_id):
            return None, "邮箱已被注册"
        inviter_id = inviter_id or root_user_id
        inviter_path = ""
        if inviter_id:
            inviter = self.repo.get_user_by_id(inviter_id, tenant_id)
            if not inviter:
                return None, "邀请人不存在或不属于该商户"
            inviter_path = (inviter.inviter_path or "").strip().rstrip("/")
            inviter_path = f"{inviter_path}/{inviter_id}" if inviter_path else str(inviter_id)
        for _ in range(15):
            invite_code = _generate_invite_code()
            if not self.repo.invite_code_exists(invite_code):
                break
        else:
            return None, "邀请码生成失败，请重试"
        user = User(
            tenant_id=tenant_id,
            email=email,
            password_hash=_hash_password(password),
            is_root=0,
            invite_code=invite_code,
            inviter_id=inviter_id,
            inviter_path=inviter_path or None,
            status=1,
        )
        self.repo.create_user(user)
        # 更新租户 total_users
        from libs.tenant.repository import TenantRepository
        tr = TenantRepository(self.db)
        t = tr.get_by_id(tenant_id)
        if t:
            t.total_users = (t.total_users or 0) + 1
            self.db.merge(t)
        return user, ""

    def bind_api_key(
        self,
        user_id: int,
        tenant_id: int,
        exchange: str,
        api_key: str,
        api_secret: str,
        account_type: str = "futures",
        passphrase: Optional[str] = None,
    ) -> Tuple[Optional[ExchangeAccount], str]:
        """绑定交易所 API，已存在则更新。返回 (account, error_msg)"""
        user = self.repo.get_user_by_id(user_id, tenant_id)
        if not user:
            return None, "用户不存在"
        existing = self.repo.get_account_by_user_exchange(user_id, exchange, account_type)
        if existing:
            existing.api_key = api_key
            existing.api_secret = api_secret
            existing.passphrase = passphrase
            existing.status = 1
            self.repo.update_account(existing)
            return existing, ""
        acc = ExchangeAccount(
            user_id=user_id,
            tenant_id=tenant_id,
            exchange=exchange,
            account_type=account_type,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            status=1,
        )
        self.repo.create_account(acc)
        return acc, ""

    def unbind_api_key(self, user_id: int, account_id: int, tenant_id: int) -> bool:
        """解绑：软删除或直接删除。这里采用将 status 置 0。若表无 status 可改为删除。"""
        acc = self.repo.get_account_by_id(account_id, user_id=user_id)
        if not acc or acc.tenant_id != tenant_id:
            return False
        acc.status = 0
        self.repo.update_account(acc)
        return True

    def open_strategy(
        self,
        user_id: int,
        tenant_id: int,
        strategy_id: int,
        account_id: int,
        mode: int = 2,
        min_point_card: float = 0,
    ) -> Tuple[Optional[StrategyBinding], str]:
        """开启策略。strategy_id 为 dim_strategy.id，需解析出 strategy_code。点卡余额不足时拒绝开通。"""
        user = self.repo.get_user_by_id(user_id, tenant_id)
        if not user:
            return None, "用户不存在"
        # 开通策略需满足最小点卡余额（自充+赠送）
        total_point = float(user.point_card_self or 0) + float(user.point_card_gift or 0)
        if total_point < min_point_card:
            return None, "点卡余额不足，无法开启策略（需至少 %.2f 点卡）" % min_point_card
        strategy = self.repo.get_strategy_by_id(strategy_id)
        if not strategy or strategy.status != 1:
            return None, "策略不存在或未启用"
        acc = self.repo.get_account_by_id(account_id, user_id=user_id)
        if not acc or acc.tenant_id != tenant_id or acc.status != 1:
            return None, "交易账户不存在或未启用"
        binding = self.repo.get_binding(user_id, account_id, strategy.code)
        if binding:
            binding.status = 1
            binding.mode = mode
            self.repo.update_binding(binding)
            return binding, ""
        binding = StrategyBinding(
            user_id=user_id,
            account_id=account_id,
            strategy_code=strategy.code,
            mode=mode,
            status=1,
        )
        self.repo.create_binding(binding)
        return binding, ""

    def close_strategy(self, user_id: int, tenant_id: int, strategy_id: int, account_id: int) -> bool:
        """关闭策略"""
        strategy = self.repo.get_strategy_by_id(strategy_id)
        if not strategy:
            return False
        binding = self.repo.get_binding(user_id, account_id, strategy.code)
        if not binding:
            return False
        user = self.repo.get_user_by_id(user_id, tenant_id)
        if not user:
            return False
        binding.status = 0
        self.repo.update_binding(binding)
        return True

    def get_user_strategies(self, user_id: int, tenant_id: int) -> List[dict]:
        """用户已绑定的策略列表，含策略名称（优先租户实例展示名）、账户、盈亏等"""
        user = self.repo.get_user_by_id(user_id, tenant_id)
        if not user:
            return []
        bindings = self.repo.get_bindings_by_user(user_id)
        result = []
        for b in bindings:
            s = self.repo.get_strategy_by_code(b.strategy_code)
            strategy_id = s.id if s else 0
            strategy_name = s.name if s else b.strategy_code
            # 优先用该租户的策略实例展示名（与 GET /merchant/strategies 一致）
            if s:
                ts = self.repo.get_tenant_strategy(tenant_id, s.id)
                if ts and (ts.display_name or "").strip():
                    strategy_name = (ts.display_name or "").strip()
            result.append({
                "strategy_id": strategy_id,
                "strategy_name": strategy_name,
                "symbol": s.symbol if s else "",
                "account_id": b.account_id,
                "status": b.status,
                "mode": b.mode,
                "total_profit": float(b.total_profit or 0),
                "total_trades": int(b.total_trades or 0),
                "create_time": b.created_at.strftime("%Y-%m-%d %H:%M:%S") if b.created_at else "",
            })
        return result

    def get_execution_targets_by_strategy_code(self, strategy_code: str) -> List[ExecutionTarget]:
        """
        根据 strategy_code 获取所有已绑定且启用的 (binding + 交易所账户) 列表，
        含执行所需字段（api_key/api_secret 等），仅服务端使用。
        用于按策略多账户执行时创建 LiveTrader + TradeSettlementService。
        点卡余额为 0 的用户不进入执行列表；该租户已下架/删除策略实例的也不执行。
        """
        strategy = self.repo.get_strategy_by_code(strategy_code)
        if not strategy:
            return []
        bindings = self.repo.get_bindings_by_strategy_code(strategy_code)
        targets = []
        for b in bindings:
            acc = self.repo.get_account_by_id(b.account_id)
            if not acc or acc.status != 1:
                continue
            user = self.repo.get_user_by_id(acc.user_id)
            if not user:
                continue
            # 该租户下该策略实例必须存在且启用，否则不执行（与开通校验一致）
            ts = self.repo.get_tenant_strategy(acc.tenant_id, strategy.id)
            if not ts or ts.status != 1:
                continue
            total_point = float(user.point_card_self or 0) + float(user.point_card_gift or 0)
            if total_point <= 0:
                continue  # 点卡为 0 不执行，相当于策略对该账户暂停
            market_type = "future" if (acc.account_type or "futures").lower() in ("futures", "future") else "spot"
            node_id = getattr(acc, "execution_node_id", None)
            if node_id is not None and node_id == 0:
                node_id = None
            targets.append(ExecutionTarget(
                tenant_id=acc.tenant_id,
                account_id=acc.id,
                user_id=acc.user_id,
                exchange=acc.exchange or "binance",
                api_key=acc.api_key,
                api_secret=acc.api_secret,
                passphrase=acc.passphrase,
                market_type=market_type,
                binding_id=b.id,
                strategy_code=b.strategy_code,
                ratio=int(b.ratio or 100),
                execution_node_id=node_id,
            ))
        return targets
