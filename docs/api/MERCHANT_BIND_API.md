# 绑定 API（交易所 API Key）

**接口**：`POST /merchant/user/apikey`（Merchant API，需 AppKey+Sign 鉴权）

用于为用户绑定交易所 API Key，支持 **Binance、OKX、Gate**。

---

## 请求参数（form-urlencoded）

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| email | string | 是 | 用户邮箱（唯一标识） |
| exchange | string | 是 | 交易所：**binance** / **okx** / **gate** |
| api_key | string | 是 | API Key |
| api_secret | string | 是 | API Secret |
| **passphrase** | string | **OKX 必填** | API Passphrase（创建 API 时设置的密码）。**选择 OKX 时必须多传这一行**；Gate 可选；Binance 不填 |
| account_type | string | 否 | 账户类型（默认 futures） |

---

## 前端/客户端说明

- **选择 Binance**：只需传 email、exchange、api_key、api_secret；不传 passphrase。
- **选择 OKX**：必须多传 **passphrase**（一行输入框）。不传或为空会返回错误：「OKX 必须填写 API Passphrase」。
- **选择 Gate**：支持。passphrase 可选（Gate 部分 API 需要），按需传。

---

## 响应

成功：

```json
{
    "code": 0,
    "msg": "绑定成功",
    "data": {
        "account_id": 1,
        "exchange": "okx",
        "account_type": "futures"
    }
}
```

失败示例：

- `exchange` 不在支持列表：`{"code": 1, "msg": "不支持的交易所，仅支持: binance, okx, gate"}`
- 选 OKX 未传 passphrase：`{"code": 1, "msg": "OKX 必须填写 API Passphrase（创建 API 时设置的密码）"}`
