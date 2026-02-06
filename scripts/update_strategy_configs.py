#!/usr/bin/env python3
"""
将 dim_strategy 中所有策略的 config 更新为各策略的「最优/推荐默认」参数。
与 libs/strategies 中各策略的 config.get(key, default) 一一对应，便于信号监控与回测使用。

用法（项目根目录）：
  PYTHONPATH=. python scripts/update_strategy_configs.py
  PYTHONPATH=. python scripts/update_strategy_configs.py --dry-run
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from libs.core.database import get_session
from libs.member.models import Strategy
from libs.member.repository import MemberRepository


# 各策略 code -> 最优/推荐默认 config（与 libs/strategies 内默认一致，部分做稳健微调）
OPTIMAL_CONFIGS = {
    "ma_cross": {
        "fast_ma": 5,
        "slow_ma": 20,
        "use_ema": False,
        "atr_sl_mult": 2.0,
        "atr_tp_mult": 4.0,
    },
    "macd": {
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "sl_atr_mult": 2.0,
        "tp_atr_mult": 3.0,
    },
    "rsi": {
        "rsi_period": 14,
        "rsi_overbought": 70,
        "rsi_oversold": 30,
        "sl_atr_mult": 2.0,
        "tp_atr_mult": 3.0,
    },
    "rsi_boll": {
        "rsi_period": 14,
        "rsi_overbought": 70,
        "rsi_oversold": 30,
        "boll_period": 20,
        "boll_std": 2.0,
    },
    "boll_squeeze": {
        "squeeze_threshold": 2.0,
        "boll_period": 20,
        "boll_std": 2.0,
        "sl_atr_mult": 1.5,
        "tp_atr_mult": 3.0,
    },
    "breakout": {
        "lookback": 20,
    },
    "momentum": {
        "momentum_period": 14,
        "momentum_threshold": 5,
        "sl_atr_mult": 1.5,
        "tp_atr_mult": 4.0,
    },
    "trend_aggressive": {
        "ema_fast": 8,
        "ema_slow": 21,
        "atr_multiplier": 1.5,
    },
    "trend_add": {
        "ema_period": 20,
        "pullback_pct": 1.0,
    },
    "swing": {
        "ma_period": 20,
        "swing_target": 5.0,
    },
    "ma_dense": {
        "ma_periods": [5, 10, 20, 60],
        "ma_type": "SMA",
        "sl_atr_mult": 1.5,
        "tp_atr_mult": 3.0,
        "dense_threshold": 2.0,
    },
    "reversal": {
        "rsi_extreme": 20,
        "sl_atr_mult": 2.0,
        "tp_atr_mult": 4.0,
    },
    "scalping": {
        "scalp_target": 0.3,
        "stop_loss": 0.2,
        "rsi_oversold": 30,
        "rsi_overbought": 70,
    },
    "arbitrage": {
        "lookback": 20,
    },
    "hedge": {
        "stop_loss_pct": 5.0,
        "rsi_threshold": 50,
        "boll_period": 20,
    },
    "hedge_conservative": {
        "boll_period": 20,
        "boll_std": 2.0,
        "stop_loss_pct": 5.0,
        "rsi_threshold": 50,
    },
    "reversal_hedge": {
        "rsi_extreme_low": 20,
        "boll_std": 2.5,
    },
    "smc": {
        "lookback": 50,
        "ob_min_body_ratio": 0.5,
        "fvg_min_gap": 0.001,
        "liquidity_lookback": 20,
        "require_fvg": False,
        "require_sweep": False,
        "sl_atr_mult": 1.5,
        "tp_atr_mult": 3.0,
    },
    "smc_fibo": {
        "max_loss": 100,
        "min_rr": 1.5,
        "fibo_levels": [0.382, 0.5, 0.618],
        "fibo_tolerance": 0.005,
        "lookback": 50,
        "swing_left": 5,
        "swing_right": 3,
        "ob_min_body_ratio": 0.5,
        "sl_buffer_pct": 0.002,
        "htf_multiplier": 4,
        "htf_ema_fast": 20,
        "htf_ema_slow": 50,
        "require_htf_filter": True,
    },
    "sr_break": {
        "lookback": 50,
    },
    "grid": {
        "grid_count": 10,
        "price_range": 5.0,
    },
    "hft": {
        "profit_target": 0.15,
        "stop_loss": 0.1,
        "rsi_period": 7,
        "ema_period": 5,
    },
    "ema_cross": {
        "fast_ema": 9,
        "slow_ema": 21,
        "signal_ema": 5,
        "sl_atr_mult": 2.0,
        "tp_atr_mult": 3.0,
    },
    "turtle": {
        "entry_period": 20,
        "exit_period": 10,
        "atr_period": 20,
        "risk_unit": 2,
    },
    "mean_reversion": {
        "period": 20,
        "std_mult": 2.0,
        "exit_std": 0.5,
    },
    "keltner": {
        "ema_period": 20,
        "atr_period": 10,
        "atr_mult": 2.0,
        "mode": "trend",
    },
    "supertrend": {
        "period": 10,
        "multiplier": 3.0,
    },
    "portfolio": {
        "strategies": [],
        "fusion_mode": "voting",
        "min_agreement": 0.5,
        "min_confidence": 60,
    },
    "market_regime": {
        "adx_period": 14,
        "adx_trend_threshold": 25,
        "adx_range_threshold": 20,
        "bb_period": 20,
        "bb_std": 2.0,
        "bb_squeeze_threshold": 0.02,
        "ma_periods": [10, 20, 50],
        "max_position": 1000,
        "risk_pct": 0.01,
        "tp_pct_min": 0.45,
        "tp_pct_max": 0.70,
        "sl_pct": 0.70,
        "atr_period": 14,
        "atr_mult_sl": 2.0,
        "atr_mult_tp": 3.0,
    },
}


def main():
    parser = argparse.ArgumentParser(description="Update dim_strategy.config with optimal defaults")
    parser.add_argument("--dry-run", action="store_true", help="Only print would-be updates")
    args = parser.parse_args()

    session = get_session()
    repo = MemberRepository(session)
    try:
        strategies = repo.list_strategies(status=None)  # 全部
        updated = 0
        for s in strategies:
            code = s.code
            if code not in OPTIMAL_CONFIGS:
                print(f"  [skip] {code} (no config defined)")
                continue
            new_config = OPTIMAL_CONFIGS[code]
            if args.dry_run:
                print(f"  [dry-run] {code} -> {json.dumps(new_config, ensure_ascii=False)}")
                updated += 1
                continue
            s.config = new_config
            repo.update_strategy(s)
            print(f"  [ok] {code}")
            updated += 1
        session.commit()
        print(f"Done. Updated {updated} strategies.")
    except Exception as e:
        session.rollback()
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
