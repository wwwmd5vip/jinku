#!/usr/bin/env python3
"""采集认证代币的介绍与官网（CoinGecko 合约接口），写回 contracts.json。

用法:
    python3 scripts/collect_token_info.py [--sleep 6.5] [--dry-run]

字段: description(英文简介)、website(官网)。
CoinGecko 免费版限速约 10 次/分钟,默认每次请求间隔 6.5 秒。
单个代币拉取失败不中断,保留原字段。
"""
import argparse
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# contracts.json 的 chain -> CoinGecko asset platform id
PLATFORMS = {
    'ethereum': 'ethereum',
    'bsc': 'binance-smart-chain',
    'polygon': 'polygon-pos',
    'tron': 'tron',
}

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / 'contracts.json'
TIMEOUT = 20

# 区块链浏览器域名:CoinGecko 合约页缺官网时会返回浏览器链接,不算官网
EXPLORER_HOSTS = (
    'etherscan.io', 'bscscan.com', 'polygonscan.com',
    'tronscan.org', 'tronscanapi.com',
)


def _is_explorer(url: str) -> bool:
    return any(h in url for h in EXPLORER_HOSTS)


def _ssl_context() -> ssl.SSLContext:
    """macOS python.org 构建不带根证书,优先 certifi,回退系统 CA bundle。"""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ModuleNotFoundError:
        pass
    for ca in ('/etc/ssl/cert.pem', '/etc/ssl/certs/ca-certificates.crt'):
        if Path(ca).exists():
            return ssl.create_default_context(cafile=ca)
    return ssl.create_default_context()


def fetch(platform: str, address: str) -> dict | None:
    url = f'https://api.coingecko.com/api/v3/coins/{platform}/contract/{address}'
    req = urllib.request.Request(url, headers={'User-Agent': 'jinku-collector/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=_ssl_context()) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        print(f'  HTTP {e.code}: {url}', file=sys.stderr)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        print(f'  error: {e}', file=sys.stderr)
    return None


def extract(d: dict) -> tuple[str | None, str | None]:
    desc = ((d.get('description') or {}).get('en') or '').strip() or None
    homepage = [u for u in ((d.get('links') or {}).get('homepage') or []) if u]
    return desc, (homepage[0] if homepage else None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--sleep', type=float, default=6.5, help='请求间隔秒数')
    ap.add_argument('--dry-run', action='store_true', help='只打印不写文件')
    ap.add_argument('--only-missing', action='store_true',
                    help='只拉取缺 description 或 website 的条目')
    args = ap.parse_args()

    data = json.loads(CONTRACTS.read_text())
    contracts = data['contracts']
    ok = skip = fail = 0
    fetched = 0
    for i, c in enumerate(contracts):
        platform = PLATFORMS.get(c['chain'])
        label = f"{c['chain']}/{c['symbol']} {c['address']}"
        if not platform:
            print(f'[{i+1}/{len(contracts)}] {label} -> 未知链,跳过')
            skip += 1
            continue
        if args.only_missing and c.get('description') and c.get('website'):
            continue
        if fetched:
            time.sleep(args.sleep)
        fetched += 1
        d = fetch(platform, c['address'])
        if d is None:
            print(f'[{i+1}/{len(contracts)}] {label} -> 拉取失败,保留原值')
            fail += 1
        else:
            desc, site = extract(d)
            if desc:
                c['description'] = desc
            if site:
                c['website'] = site
            print(f'[{i+1}/{len(contracts)}] {label} -> desc={bool(desc)} site={site}')
            ok += 1

    # 同 symbol 跨链继承:同一代币的简介/官网跨链一致
    # (如 bsc/USDT 继承 ethereum/USDT),补 CoinGecko 合约页缺描述的情况。
    # 浏览器链接(etherscan/bscscan 等)不算官网,同样参与继承替换。
    by_symbol: dict[str, dict] = {}
    for c in contracts:
        src = by_symbol.setdefault(c['symbol'], {})
        if c.get('description') and 'description' not in src:
            src['description'] = c['description']
        site = c.get('website')
        if site and not _is_explorer(site) and 'website' not in src:
            src['website'] = site
    filled = 0
    for c in contracts:
        src = by_symbol.get(c['symbol'], {})
        if not c.get('description') and src.get('description'):
            c['description'] = src['description']
            filled += 1
            print(f"  继承: {c['chain']}/{c['symbol']} <- description")
        site = c.get('website')
        official = src.get('website')
        if (not site or _is_explorer(site)) and official and official != site:
            c['website'] = official
            filled += 1
            print(f"  继承: {c['chain']}/{c['symbol']} <- website")
    if filled:
        print(f'跨链继承补齐 {filled} 个字段')

    if not args.dry_run:
        CONTRACTS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
        print(f'写回 {CONTRACTS}')
    print(f'完成: 成功 {ok}, 跳过 {skip}, 失败 {fail}')
    return 0 if fail == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
