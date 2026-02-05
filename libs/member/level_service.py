"""
Level Service - 会员等级计算（S0-S7）

规则：
- 自持 >= 1000 USDT（交易所合约余额）
- 团队业绩 >= 等级要求
- 不达标则降级，无保护期
"""

from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session

from .models import User, LevelConfig
from .repository import MemberRepository

SELF_HOLD_THRESHOLD = Decimal("1000")


class LevelService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = MemberRepository(db)
        self._level_configs: Optional[List[LevelConfig]] = None

    def _get_level_configs(self) -> List[LevelConfig]:
        if self._level_configs is None:
            self._level_configs = self.db.query(LevelConfig).order_by(LevelConfig.level.desc()).all()
        return self._level_configs

    def get_self_hold(self, user_id: int) -> Decimal:
        """用户自持金额（所有绑定账户的 futures_balance 之和）"""
        return self.repo.sum_futures_balance_by_user_ids([user_id])

    def get_team_performance(self, user_id: int) -> Decimal:
        """团队业绩（所有下级的 futures_balance 之和）"""
        sub_ids = self.repo.get_all_sub_user_ids(user_id)
        if not sub_ids:
            return Decimal("0")
        return self.repo.sum_futures_balance_by_user_ids(sub_ids)

    def compute_level(self, user_id: int) -> int:
        """
        根据自持和团队业绩计算等级 0-7。
        自持 < 1000 则 S0；否则按团队业绩取满足条件的最高等级。
        """
        self_hold = self.get_self_hold(user_id)
        if self_hold < SELF_HOLD_THRESHOLD:
            return 0
        team_perf = self.get_team_performance(user_id)
        configs = self._get_level_configs()
        for cfg in configs:
            if cfg.level == 0:
                return 0
            if team_perf >= (cfg.min_team_perf or 0):
                return cfg.level
        return 0

    def refresh_user_level(self, user: User) -> User:
        """更新用户的 team_performance 和 member_level"""
        user.team_performance = self.get_team_performance(user.id)
        user.member_level = self.compute_level(user.id)
        self.repo.update_user(user)
        return user

    def get_level_name(self, level: int) -> str:
        return f"S{level}"
