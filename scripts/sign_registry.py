#!/usr/bin/env python3
"""keyfort 合约认证记录签名工具（jinku 自有仓库版）。

数据源 contracts.json → 逐合约生成 registry/<chain>/<address>.json，
Ed25519 签名，App 端（keyfort_core ContractRegistry）内置公钥验签后采信。

用法：
  python3 scripts/sign_registry.py init   # 首次：生成维护者密钥对（私钥不入库）
  python3 scripts/sign_registry.py sign   # 按 contracts.json 重签全部记录

私钥保存在 scripts/registry_private_key.hex（已 gitignore，0600）。
公钥需同步写入 keyfort_core/lib/src/registry/contract_registry.dart 的
kRegistryMaintainerPublicKeyHex。
"""
import json
import os
import stat
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

ROOT = Path(__file__).resolve().parent.parent
KEY_FILE = ROOT / "scripts" / "registry_private_key.hex"
CONTRACTS = ROOT / "contracts.json"
MANIFEST = ROOT / "manifest.json"
REGISTRY_DIR = ROOT / "registry"

# 与 Dart 端 ContractRecord.canonical() 逐字节一致：
# 键排序、无空白、非 ASCII 不转义。
CANONICAL_KEYS = ("address", "chain", "decimals", "name", "risk", "symbol", "updatedAt")


def canonical(record: dict) -> str:
    body = {k: record[k] for k in CANONICAL_KEYS}
    body["address"] = body["address"].lower()
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def cmd_init() -> None:
    if KEY_FILE.exists():
        sys.exit(f"密钥已存在: {KEY_FILE}（如需轮换请先删除旧文件并全量重签）")
    priv = Ed25519PrivateKey.generate()
    priv_bytes = priv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    pub_bytes = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    KEY_FILE.write_text(priv_bytes.hex() + "\n")
    os.chmod(KEY_FILE, stat.S_IRUSR | stat.S_IWUSR)
    print("私钥已写入:", KEY_FILE)
    print("公钥（写入 contract_registry.dart kRegistryMaintainerPublicKeyHex）:")
    print(pub_bytes.hex())


def _load_key() -> Ed25519PrivateKey:
    if not KEY_FILE.exists():
        sys.exit("缺少私钥，先运行: python3 scripts/sign_registry.py init")
    return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(KEY_FILE.read_text().strip()))


def cmd_sign() -> int:
    priv = _load_key()
    updated_at = json.loads(MANIFEST.read_text())["updatedAt"]
    contracts = json.loads(CONTRACTS.read_text())["contracts"]
    written = skipped = 0
    for c in contracts:
        if not c.get("verified"):
            continue
        record = {
            "chain": c["chain"],
            "address": c["address"],
            "name": c["name"],
            "symbol": c["symbol"],
            "decimals": c["decimals"],
            "risk": "verified",
            "updatedAt": updated_at,
        }
        sig = priv.sign(canonical(record).encode("utf-8"))
        record["sig"] = sig.hex()
        out = REGISTRY_DIR / c["chain"] / f"{c['address'].lower()}.json"
        payload = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
        if out.exists() and out.read_text() == payload:
            skipped += 1
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload)
        written += 1
    print(f"签名完成: 新写 {written}，未变更 {skipped}")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "init":
        cmd_init()
    elif cmd == "sign":
        sys.exit(cmd_sign())
    else:
        sys.exit(__doc__)
