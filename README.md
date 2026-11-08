# jinku — KeyFort 公开数据仓库

存放 KeyFort 钱包的**公开链上数据**：认证合约注册表、合约/链图标、各链 RPC 接口列表。
应用不写死这些数据，运行时远程拉取本仓库，便于不发版即可更新维护。

## 远程访问

统一通过 jsDelivr / raw.githubusercontent 拉取：

```
https://raw.githubusercontent.com/wwwmd5vip/jinku/main/manifest.json
https://raw.githubusercontent.com/wwwmd5vip/jinku/main/rpc.json
https://raw.githubusercontent.com/wwwmd5vip/jinku/main/contracts.json
https://raw.githubusercontent.com/wwwmd5vip/jinku/main/chains.json
https://raw.githubusercontent.com/wwwmd5vip/jinku/main/icons/tokens/tron/TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t.png
```

入口固定为 `manifest.json`：先读清单（版本、文件路径、图标路径模板），再按需取数据文件。

## 文件说明

| 文件 | 内容 |
| --- | --- |
| `manifest.json` | 数据版本、文件清单、图标路径模板 |
| `chains.json` | 链公开元数据（id/名称/符号/精度/浏览器链接模板） |
| `rpc.json` | 每条链的 RPC 端点列表（`priority` 升序即故障转移顺序） |
| `contracts.json` | 认证合约注册表（地址/名称/符号/精度/标准/verified/图标） |
| `icons/chains/{chainId}.png` | 链图标 |
| `icons/tokens/{chain}/{address}.png` | 代币合约图标（EVM 地址保留校验和大小写） |

## 更新流程

1. 直接改本仓库 main 分支（加合约、换 RPC、换图标）。
2. 同步把 `manifest.json` 的 `version` +1 并刷新 `updatedAt`。
3. 客户端下次启动拉取 manifest，发现 version 变化即刷新缓存 —— 无需发版。

## 客户端约定

- 拉取失败：回落到本地缓存（SharedPreferences），再回落到应用内置兜底值。
- 图标缺失：按 manifest 模板拼 URL，404 时显示默认占位图标。
- `verified: false` 的合约可收录但客户端需标注未认证。
