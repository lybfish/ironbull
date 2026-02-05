"""Static node registry (v0)."""

from typing import Dict

from libs.core import get_config


def get_node_registry() -> Dict[str, str]:
    config = get_config()
    crypto_url = config.get_str("crypto_node_url", "")
    mt5_url = config.get_str("mt5_node_url", "")

    if not crypto_url:
        crypto_port = config.get_int("crypto_node_port", 9101)
        crypto_url = f"http://127.0.0.1:{crypto_port}"

    if not mt5_url:
        mt5_port = config.get_int("mt5_node_port", 9102)
        mt5_url = f"http://127.0.0.1:{mt5_port}"

    return {
        "crypto": crypto_url,
        "mt5": mt5_url,
    }
