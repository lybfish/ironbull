"""
Backtest Service - HTTP API

提供回测服务的 HTTP 接口。

端点：
- GET /health
- POST /api/backtest/run - 运行回测（使用提供的 K 线数据）
- POST /api/backtest/run-live - 运行回测（从交易所获取真实 K 线）
- GET /api/backtest/result/{backtest_id} - 获取回测结果（v0 暂不实现持久化，直接返回）
"""

import sys
import os
import httpx
from datetime import datetime
from typing import Optional, List

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from flask import Flask, request, jsonify, g
from werkzeug.exceptions import HTTPException
from libs.core import get_config, get_logger, setup_logging, gen_id, AppError
from libs.strategies import get_strategy
from services.backtest.app.backtest_engine import BacktestEngine, BacktestResult

# 初始化 Flask
app = Flask(__name__)

# 配置
config = get_config()

# Data Provider URL（用于获取真实 K 线数据）
DATA_PROVIDER_URL = config.get_str("data_provider_url", "http://127.0.0.1:8010")

# 配置日志
service_name = "backtest"
setup_logging(
    level=config.get_str("log_level", "INFO"),
    structured=config.get_bool("log_structured", False),
    service_name=service_name,
)
log = get_logger("backtest-service")


@app.before_request
def add_request_id():
    request_id = request.headers.get("X-Request-Id") or gen_id("req_")
    g.request_id = request_id


@app.after_request
def add_request_id_header(response):
    if hasattr(g, "request_id"):
        response.headers["X-Request-Id"] = g.request_id
    return response


def _error_payload(code: str, message: str, detail: Optional[dict] = None) -> dict:
    payload = {"code": code, "message": message, "detail": detail or {}}
    if hasattr(g, "request_id"):
        payload["request_id"] = g.request_id
    return payload


@app.errorhandler(AppError)
def app_error_handler(exc: AppError):
    return jsonify(_error_payload(exc.code, exc.message, exc.detail)), 400


@app.errorhandler(HTTPException)
def http_exception_handler(exc: HTTPException):
    detail = exc.description if isinstance(exc.description, str) else exc.description
    return jsonify(_error_payload("HTTP_ERROR", "HTTP error", {"detail": detail})), exc.code


@app.errorhandler(Exception)
def unhandled_exception_handler(exc: Exception):
    log.error("unhandled exception", request_id=getattr(g, "request_id", None), error=str(exc))
    return jsonify(_error_payload("INTERNAL_ERROR", "Internal error", {"error": str(exc)})), 500


@app.route("/health", methods=["GET"])
def health():
    """健康检查"""
    return jsonify({
        "status": "ok",
        "service": "backtest",
        "data_provider_url": DATA_PROVIDER_URL,
    }), 200


@app.route("/api/backtest/run", methods=["POST"])
def run_backtest():
    """
    运行回测
    
    Request Body:
    {
        "strategy_code": "ma_cross",
        "strategy_config": {"fast_ma": 5, "slow_ma": 20},  // 可选
        "symbol": "BTCUSDT",
        "timeframe": "15m",
        "candles": [...],  // K线数据（按时间升序）
        "initial_balance": 10000.0,  // 可选，默认 10000
        "commission_rate": 0.001,    // 可选，默认 0.001
        "lookback": 50,              // 可选，默认 50
        "risk_per_trade": 100        // 可选，以损定仓：每笔最大亏损（0=固定仓位）
    }
    
    Response:
    {
        "success": true,
        "result": BacktestResult
    }
    """
    
    try:
        data = request.get_json()
        
        # 必填参数
        strategy_code = data.get("strategy_code")
        symbol = data.get("symbol")
        timeframe = data.get("timeframe")
        candles = data.get("candles")
        
        if not all([strategy_code, symbol, timeframe, candles]):
            return jsonify(
                _error_payload(
                    "VALIDATION_ERROR",
                    "Missing required fields",
                    {"required": ["strategy_code", "symbol", "timeframe", "candles"]},
                )
            ), 400
        
        # 可选参数
        strategy_config = data.get("strategy_config", {})
        initial_balance = data.get("initial_balance", 10000.0)
        commission_rate = data.get("commission_rate", 0.001)
        lookback = data.get("lookback", 50)
        risk_per_trade = data.get("risk_per_trade", 0.0)  # 以损定仓
        amount_usdt = data.get("amount_usdt", 0.0)        # 固定名义持仓
        
        # 加载策略
        try:
            strategy = get_strategy(strategy_code, strategy_config)
        except Exception as e:
            return jsonify(
                _error_payload(
                    "STRATEGY_LOAD_ERROR",
                    "Failed to load strategy",
                    {"error": str(e)},
                )
            ), 400
        
        # 创建回测引擎
        engine = BacktestEngine(
            initial_balance=initial_balance,
            commission_rate=commission_rate,
            risk_per_trade=risk_per_trade,
            amount_usdt=amount_usdt,
        )
        
        if amount_usdt > 0:
            risk_mode = f"固定名义持仓({amount_usdt} USDT/单)"
        elif risk_per_trade > 0:
            risk_mode = "以损定仓"
        else:
            risk_mode = "固定仓位"
        log.info(
            f"开始回测: strategy={strategy_code}, symbol={symbol}, "
            f"timeframe={timeframe}, candles={len(candles)}, mode={risk_mode}"
        )
        
        # 运行回测
        result = engine.run(
            strategy=strategy,
            symbol=symbol,
            timeframe=timeframe,
            candles=candles,
            lookback=lookback,
        )
        
        log.info(
            f"回测完成: trades={result.total_trades}, "
            f"win_rate={result.win_rate:.2f}%, "
            f"pnl={result.total_pnl:.2f}"
        )
        
        # 返回结果（转为 dict）
        return jsonify({
            "success": True,
            "result": _backtest_result_to_dict(result)
        }), 200
        
    except ValueError as e:
        log.error(f"参数错误: {str(e)}")
        return jsonify(_error_payload("VALIDATION_ERROR", "Validation failed", {"error": str(e)})), 400
    except Exception as e:
        log.error(f"回测失败: {str(e)}")
        return jsonify(_error_payload("INTERNAL_ERROR", "Internal error", {"error": str(e)})), 500


def _backtest_result_to_dict(result: BacktestResult) -> dict:
    """将 BacktestResult 转为 dict（用于 JSON 序列化）"""
    return {
        "strategy_code": result.strategy_code,
        "symbol": result.symbol,
        "timeframe": result.timeframe,
        "start_time": result.start_time.isoformat(),
        "end_time": result.end_time.isoformat(),
        
        # 基础统计
        "total_trades": result.total_trades,
        "winning_trades": result.winning_trades,
        "losing_trades": result.losing_trades,
        "win_rate": round(result.win_rate, 2),
        
        # 方向统计
        "long_trades": result.long_trades,
        "short_trades": result.short_trades,
        "long_pnl": round(result.long_pnl, 2),
        "short_pnl": round(result.short_pnl, 2),
        
        # 收益统计
        "total_pnl": round(result.total_pnl, 2),
        "total_pnl_pct": round(result.total_pnl_pct, 2),
        "avg_pnl": round(result.avg_pnl, 2),
        "avg_win": round(result.avg_win, 2),
        "avg_loss": round(result.avg_loss, 2),
        
        # 风险统计
        "max_drawdown": round(result.max_drawdown, 2),
        "max_drawdown_pct": round(result.max_drawdown_pct, 2),
        
        # 盈亏比指标
        "risk_reward_ratio": round(result.risk_reward_ratio, 2),
        "profit_factor": round(result.profit_factor, 2),
        "expectancy": round(result.expectancy, 2),
        
        # 账户统计
        "initial_balance": result.initial_balance,
        "final_balance": round(result.final_balance, 2),
        "peak_balance": round(result.peak_balance, 2),
        
        # 交易记录（简化）
        "trades": [
            {
                "trade_id": t.trade_id,
                "side": t.side,
                "entry_price": t.entry_price,
                "entry_time": t.entry_time.isoformat(),
                "exit_price": t.exit_price,
                "exit_time": t.exit_time.isoformat() if t.exit_time else None,
                "quantity": t.quantity,
                "stop_loss": t.stop_loss,
                "take_profit": t.take_profit,
                "exit_reason": t.exit_reason,
                "pnl": round(t.pnl, 2) if t.pnl else None,
                "pnl_pct": round(t.pnl_pct, 2) if t.pnl_pct else None,
            }
            for t in result.trades
        ],
        
        # 权益曲线（可选，数据量大时可省略）
        "equity_curve": result.equity_curve if len(result.equity_curve) < 1000 else [],
    }


def _fetch_candles_from_data_provider(
    symbol: str,
    timeframe: str,
    limit: int = 500,
    exchange: str = None,
    source: str = "live",
) -> List[dict]:
    """
    从 data-provider 获取 K 线数据
    
    Args:
        symbol: 交易对
        timeframe: 时间周期
        limit: K 线数量
        exchange: 交易所（可选）
        source: 数据源 mock/live
    
    Returns:
        K 线数据列表
    """
    params = {
        "symbol": symbol,
        "timeframe": timeframe,
        "limit": limit,
        "source": source,
    }
    if exchange:
        params["exchange"] = exchange
    
    url = f"{DATA_PROVIDER_URL}/api/candles"
    
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            return data.get("candles", [])
    except httpx.TimeoutException:
        raise Exception(f"Data provider timeout: {url}")
    except httpx.HTTPStatusError as e:
        raise Exception(f"Data provider error: {e.response.status_code}")
    except Exception as e:
        raise Exception(f"Failed to fetch candles: {str(e)}")


@app.route("/api/backtest/run-live", methods=["POST"])
def run_backtest_live():
    """
    使用真实 K 线数据运行回测
    
    Request Body:
    {
        "strategy_code": "ma_cross",
        "strategy_config": {"fast_ma": 5, "slow_ma": 20},  // 可选
        "symbol": "BTC/USDT",
        "timeframe": "15m",
        "limit": 500,                 // K线数量，默认 500
        "exchange": "binance",        // 可选，默认使用配置
        "initial_balance": 10000.0,   // 可选，默认 10000
        "commission_rate": 0.001,     // 可选，默认 0.001
        "lookback": 50                // 可选，默认 50
    }
    
    Response:
    {
        "success": true,
        "data_source": "live",
        "candles_count": 500,
        "result": BacktestResult
    }
    """
    
    try:
        data = request.get_json()
        
        # 必填参数
        strategy_code = data.get("strategy_code")
        symbol = data.get("symbol")
        timeframe = data.get("timeframe")
        
        if not all([strategy_code, symbol, timeframe]):
            return jsonify(
                _error_payload(
                    "VALIDATION_ERROR",
                    "Missing required fields",
                    {"required": ["strategy_code", "symbol", "timeframe"]},
                )
            ), 400
        
        # 可选参数
        strategy_config = data.get("strategy_config", {})
        limit = data.get("limit", 500)
        exchange = data.get("exchange")
        initial_balance = data.get("initial_balance", 10000.0)
        commission_rate = data.get("commission_rate", 0.001)
        lookback = data.get("lookback", 50)
        risk_per_trade = data.get("risk_per_trade", 0.0)  # 以损定仓
        amount_usdt = data.get("amount_usdt", 0.0)        # 固定名义持仓（与线上一致）
        
        # 1. 从 data-provider 获取真实 K 线
        log.info(
            f"获取真实K线: symbol={symbol}, timeframe={timeframe}, limit={limit}"
        )
        
        try:
            candles = _fetch_candles_from_data_provider(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
                exchange=exchange,
                source="live",
            )
        except Exception as e:
            return jsonify(
                _error_payload(
                    "DATA_FETCH_ERROR",
                    "Failed to fetch candles",
                    {"error": str(e)},
                )
            ), 503
        
        if not candles or len(candles) < lookback + 10:
            return jsonify(
                _error_payload(
                    "INSUFFICIENT_DATA",
                    "Not enough candles for backtest",
                    {"received": len(candles) if candles else 0, "required": lookback + 10},
                )
            ), 400
        
        log.info(f"获取到 {len(candles)} 根K线")
        
        # 2. 加载策略
        try:
            strategy = get_strategy(strategy_code, strategy_config)
        except Exception as e:
            return jsonify(
                _error_payload(
                    "STRATEGY_LOAD_ERROR",
                    "Failed to load strategy",
                    {"error": str(e)},
                )
            ), 400
        
        # 3. 创建回测引擎
        engine = BacktestEngine(
            initial_balance=initial_balance,
            commission_rate=commission_rate,
            risk_per_trade=risk_per_trade,
            amount_usdt=amount_usdt,
        )
        
        if amount_usdt > 0:
            risk_mode = f"固定名义持仓({amount_usdt} USDT/单)"
        elif risk_per_trade > 0:
            risk_mode = "以损定仓"
        else:
            risk_mode = "固定仓位"
        log.info(
            f"开始真实数据回测: strategy={strategy_code}, symbol={symbol}, "
            f"timeframe={timeframe}, candles={len(candles)}, mode={risk_mode}"
        )
        
        # 4. 运行回测
        result = engine.run(
            strategy=strategy,
            symbol=symbol,
            timeframe=timeframe,
            candles=candles,
            lookback=lookback,
        )
        
        log.info(
            f"回测完成: trades={result.total_trades}, "
            f"win_rate={result.win_rate:.2f}%, "
            f"pnl={result.total_pnl:.2f}"
        )
        
        # 5. 返回结果
        return jsonify({
            "success": True,
            "data_source": "live",
            "exchange": exchange or "binance",
            "candles_count": len(candles),
            "result": _backtest_result_to_dict(result)
        }), 200
        
    except ValueError as e:
        log.error(f"参数错误: {str(e)}")
        return jsonify(_error_payload("VALIDATION_ERROR", "Validation failed", {"error": str(e)})), 400
    except Exception as e:
        log.error(f"回测失败: {str(e)}")
        return jsonify(_error_payload("INTERNAL_ERROR", "Internal error", {"error": str(e)})), 500


# ========== 参数优化 API ==========

def _run_backtest_for_optimizer(
    strategy_code: str,
    config: dict,
    symbol: str,
    timeframe: str,
    candles: list,
) -> dict:
    """为优化器提供的回测函数"""
    strategy = get_strategy(strategy_code, config)
    engine = BacktestEngine(initial_balance=10000, commission_rate=0.001)
    result = engine.run(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        candles=candles,
        lookback=50,
    )
    return {
        "total_pnl": result.total_pnl,
        "total_pnl_pct": result.total_pnl_pct,
        "win_rate": result.win_rate,
        "total_trades": result.total_trades,
        "max_drawdown": result.max_drawdown,
        "max_drawdown_pct": result.max_drawdown_pct,
        "final_balance": result.final_balance,
    }


@app.route("/api/backtest/optimize", methods=["POST"])
def optimize_strategy():
    """
    参数优化 API
    
    Request Body:
    {
        "strategy_code": "ma_cross",
        "symbol": "BTC/USDT",
        "timeframe": "15m",
        "limit": 500,                    // K线数量
        "param_grid": {                  // 参数网格
            "fast_ma": [5, 10, 15, 20],
            "slow_ma": [20, 30, 40, 50]
        },
        "score_by": "pnl",               // 优化目标: pnl / sharpe / win_rate
        "constraints": {                 // 可选约束
            "slow_ma_gt_fast_ma": true
        }
    }
    
    Response:
    {
        "success": true,
        "best_params": {"fast_ma": 10, "slow_ma": 40},
        "best_score": 2500.5,
        "best_result": {...},
        "total_combinations": 16,
        "elapsed_seconds": 5.2,
        "top_10": [...]
    }
    """
    from libs.optimizer import GridOptimizer, ParameterGrid
    
    try:
        data = request.get_json()
        
        # 必填参数
        strategy_code = data.get("strategy_code")
        symbol = data.get("symbol")
        timeframe = data.get("timeframe")
        param_grid_data = data.get("param_grid")
        
        if not all([strategy_code, symbol, timeframe, param_grid_data]):
            return jsonify(_error_payload(
                "VALIDATION_ERROR",
                "Missing required fields",
                {"required": ["strategy_code", "symbol", "timeframe", "param_grid"]},
            )), 400
        
        # 可选参数
        limit = data.get("limit", 300)
        score_by = data.get("score_by", "pnl")
        constraints_config = data.get("constraints", {})
        
        # 1. 获取 K 线数据
        log.info(f"获取K线数据: symbol={symbol}, timeframe={timeframe}, limit={limit}")
        
        candles = _fetch_candles_from_data_provider(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            source="live",
        )
        
        if not candles or len(candles) < 100:
            return jsonify(_error_payload(
                "INSUFFICIENT_DATA",
                "Not enough candles",
                {"received": len(candles) if candles else 0},
            )), 400
        
        # 2. 创建参数网格
        param_grid = ParameterGrid(param_grid_data)
        
        log.info(f"参数组合数: {len(param_grid)}")
        
        # 3. 设置评分函数
        if score_by == "pnl":
            score_func = lambda r: r.get("total_pnl", 0)
        elif score_by == "sharpe":
            score_func = lambda r: r.get("total_pnl", 0) / max(abs(r.get("max_drawdown", 1)), 1)
        elif score_by == "win_rate":
            score_func = lambda r: r.get("win_rate", 0)
        else:
            score_func = lambda r: r.get("total_pnl", 0)
        
        # 4. 设置约束
        constraints = {}
        if constraints_config.get("slow_ma_gt_fast_ma"):
            constraints["slow_ma"] = lambda p: p.get("slow_ma", 100) > p.get("fast_ma", 0)
        
        # 5. 创建优化器
        optimizer = GridOptimizer(
            backtest_func=_run_backtest_for_optimizer,
            score_func=score_func,
            constraints=constraints,
        )
        
        # 6. 执行优化
        log.info("开始参数优化...")
        
        result = optimizer.optimize(
            strategy_code=strategy_code,
            symbol=symbol,
            timeframe=timeframe,
            candles=candles,
            param_grid=param_grid,
        )
        
        log.info(f"优化完成: best_params={result.best_params}, best_score={result.best_score}")
        
        return jsonify({
            "success": True,
            **result.to_dict(),
        }), 200
        
    except Exception as e:
        log.error(f"优化失败: {str(e)}")
        return jsonify(_error_payload("INTERNAL_ERROR", "Optimization failed", {"error": str(e)})), 500


@app.route("/api/backtest/optimize-genetic", methods=["POST"])
def optimize_strategy_genetic():
    """
    遗传算法参数优化 API
    
    比网格搜索更智能，适合大参数空间
    
    Request Body:
    {
        "strategy_code": "ma_cross",
        "symbol": "BTC/USDT",
        "timeframe": "15m",
        "limit": 500,
        "param_space": {
            "fast_ma": {"type": "int", "low": 5, "high": 30, "step": 1},
            "slow_ma": {"type": "int", "low": 20, "high": 100, "step": 5}
        },
        "config": {
            "population_size": 30,
            "generations": 15,
            "mutation_rate": 0.2
        },
        "score_by": "pnl",
        "constraints": ["slow_ma > fast_ma"]
    }
    """
    from libs.optimizer import (
        GeneticOptimizer,
        GeneticConfig,
        ParameterSpace,
        fitness_pnl,
        fitness_sharpe,
        fitness_calmar,
        fitness_composite,
    )
    import time
    
    try:
        data = request.get_json()
        
        # 必填参数
        strategy_code = data.get("strategy_code")
        symbol = data.get("symbol")
        timeframe = data.get("timeframe")
        param_space_data = data.get("param_space")
        
        if not all([strategy_code, symbol, timeframe, param_space_data]):
            return jsonify(_error_payload(
                "VALIDATION_ERROR",
                "Missing required fields",
                {"required": ["strategy_code", "symbol", "timeframe", "param_space"]},
            )), 400
        
        # 可选参数
        limit = data.get("limit", 300)
        score_by = data.get("score_by", "pnl")
        ga_config = data.get("config", {})
        constraint_exprs = data.get("constraints", [])
        
        # 1. 获取 K 线数据
        log.info(f"遗传算法优化: symbol={symbol}, timeframe={timeframe}")
        
        candles = _fetch_candles_from_data_provider(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            source="live",
        )
        
        if not candles or len(candles) < 100:
            return jsonify(_error_payload(
                "INSUFFICIENT_DATA",
                "Not enough candles",
                {"received": len(candles) if candles else 0},
            )), 400
        
        # 2. 创建参数空间
        param_space = ParameterSpace()
        for name, spec in param_space_data.items():
            ptype = spec.get("type", "int")
            if ptype == "int":
                param_space.add_int(name, spec["low"], spec["high"], spec.get("step", 1))
            elif ptype == "float":
                param_space.add_float(name, spec["low"], spec["high"], spec.get("precision", 2))
            elif ptype == "choice":
                param_space.add_choice(name, spec["choices"])
        
        # 3. 设置适应度函数
        fitness_funcs = {
            "pnl": fitness_pnl,
            "sharpe": fitness_sharpe,
            "calmar": fitness_calmar,
            "composite": fitness_composite,
        }
        fitness_func = fitness_funcs.get(score_by, fitness_pnl)
        
        # 4. 设置约束
        constraints = []
        for expr in constraint_exprs:
            # 支持简单表达式: "slow_ma > fast_ma"
            if ">" in expr:
                parts = expr.replace(" ", "").split(">")
                if len(parts) == 2:
                    a, b = parts
                    constraints.append(lambda p, a=a, b=b: p.get(a, 0) > p.get(b, 0))
            elif "<" in expr:
                parts = expr.replace(" ", "").split("<")
                if len(parts) == 2:
                    a, b = parts
                    constraints.append(lambda p, a=a, b=b: p.get(a, 0) < p.get(b, 0))
        
        # 5. 创建回测函数（闭包）
        def backtest_func(params):
            result = _run_backtest_for_optimizer(
                strategy_code=strategy_code,
                config=params,  # params 作为策略配置
                symbol=symbol,
                timeframe=timeframe,
                candles=candles,
            )
            return result
        
        # 6. 遗传算法配置
        config_obj = GeneticConfig(
            population_size=ga_config.get("population_size", 30),
            generations=ga_config.get("generations", 15),
            elite_ratio=ga_config.get("elite_ratio", 0.1),
            crossover_rate=ga_config.get("crossover_rate", 0.8),
            mutation_rate=ga_config.get("mutation_rate", 0.2),
            tournament_size=ga_config.get("tournament_size", 3),
            early_stop_generations=ga_config.get("early_stop", 5),
        )
        
        # 7. 创建并运行优化器
        optimizer = GeneticOptimizer(
            param_space=param_space,
            backtest_func=backtest_func,
            fitness_func=fitness_func,
            config=config_obj,
            constraints=constraints,
        )
        
        start_time = time.time()
        result = optimizer.optimize(verbose=False)
        elapsed = time.time() - start_time
        
        log.info(f"遗传算法完成: best_fitness={result.best_fitness:.4f}, generations={result.generations_run}")
        
        # 8. 排序所有个体，取 top 10
        all_sorted = sorted(
            result.all_individuals,
            key=lambda x: x.get("fitness", float("-inf")),
            reverse=True,
        )[:10]
        
        return jsonify({
            "success": True,
            "best_params": result.best_params,
            "best_fitness": result.best_fitness,
            "best_metrics": result.best_metrics,
            "generations_run": result.generations_run,
            "total_evaluations": len(result.all_individuals),
            "elapsed_seconds": round(elapsed, 2),
            "top_10": all_sorted,
            "evolution_history": [
                {
                    "generation": h["generation"],
                    "best_fitness": round(h["best_fitness"], 4),
                    "avg_fitness": round(h["avg_fitness"], 4),
                }
                for h in result.population_history
            ],
        }), 200
        
    except Exception as e:
        log.error(f"遗传算法优化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify(_error_payload("INTERNAL_ERROR", "Genetic optimization failed", {"error": str(e)})), 500


@app.route("/api/strategies", methods=["GET"])
def list_all_strategies():
    """列出所有可用策略"""
    from libs.strategies import list_strategies
    return jsonify({"strategies": list_strategies()}), 200


@app.route("/api/backtest/portfolio", methods=["POST"])
def backtest_portfolio():
    """
    策略组合回测 API
    
    Request Body:
    {
        "strategies": [
            {"code": "ma_cross", "weight": 0.3},
            {"code": "macd", "weight": 0.25},
            {"code": "smc", "weight": 0.25},
            {"code": "turtle", "weight": 0.2}
        ],
        "fusion_mode": "voting",      // voting / weighted / unanimous / any
        "min_agreement": 0.5,         // 最小同意比例
        "symbol": "BTC/USDT",
        "timeframe": "1h",
        "limit": 300
    }
    """
    from libs.strategies import get_strategy
    
    try:
        data = request.get_json()
        
        # 必填参数
        strategies_config = data.get("strategies")
        symbol = data.get("symbol")
        timeframe = data.get("timeframe")
        
        if not all([strategies_config, symbol, timeframe]):
            return jsonify(_error_payload(
                "VALIDATION_ERROR",
                "Missing required fields",
                {"required": ["strategies", "symbol", "timeframe"]},
            )), 400
        
        # 可选参数
        fusion_mode = data.get("fusion_mode", "voting")
        min_agreement = data.get("min_agreement", 0.5)
        limit = data.get("limit", 300)
        
        # 1. 获取 K 线数据
        candles = _fetch_candles_from_data_provider(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            source="live",
        )
        
        if not candles or len(candles) < 100:
            return jsonify(_error_payload(
                "INSUFFICIENT_DATA",
                "Not enough candles",
            )), 400
        
        # 2. 创建策略组合
        portfolio_config = {
            "strategies": strategies_config,
            "fusion_mode": fusion_mode,
            "min_agreement": min_agreement,
        }
        
        portfolio = get_strategy("portfolio", portfolio_config)
        
        # 3. 运行回测
        engine = BacktestEngine(initial_balance=10000, commission_rate=0.001)
        result = engine.run(
            strategy=portfolio,
            symbol=symbol,
            timeframe=timeframe,
            candles=candles,
            lookback=50,
        )
        
        log.info(f"策略组合回测完成: trades={result.total_trades}, pnl={result.total_pnl:.2f}")
        
        # 4. 单独回测每个子策略作为对比
        individual_results = []
        for cfg in strategies_config:
            code = cfg.get("code")
            weight = cfg.get("weight", 1.0)
            try:
                strategy = get_strategy(code, cfg.get("config", {}))
                eng = BacktestEngine(initial_balance=10000, commission_rate=0.001)
                res = eng.run(
                    strategy=strategy,
                    symbol=symbol,
                    timeframe=timeframe,
                    candles=candles,
                    lookback=50,
                )
                individual_results.append({
                    "code": code,
                    "weight": weight,
                    "trades": res.total_trades,
                    "win_rate": round(res.win_rate, 2),
                    "pnl": round(res.total_pnl, 2),
                    "pnl_pct": round(res.total_pnl_pct, 2),
                    "max_drawdown_pct": round(res.max_drawdown_pct, 2),
                })
            except Exception as e:
                individual_results.append({
                    "code": code,
                    "error": str(e),
                })
        
        return jsonify({
            "success": True,
            "fusion_mode": fusion_mode,
            "min_agreement": min_agreement,
            "portfolio_result": _backtest_result_to_dict(result),
            "individual_results": individual_results,
        }), 200
        
    except Exception as e:
        log.error(f"策略组合回测失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify(_error_payload("INTERNAL_ERROR", str(e))), 500


if __name__ == "__main__":
    port = config.get("backtest_port", 8030)
    log.info(f"🚀 Backtest Service 启动在端口 {port}")
    app.run(host="127.0.0.1", port=port, debug=False)
