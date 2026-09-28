#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
影视仓 / TVBox 配置源自动更新脚本（仅标准库，无第三方依赖）

流程：
  1) 从「种子多仓源」+「自维护 sources.txt」读取候选源
  2) 逐层展开多仓（storeHouse / urls / TXT 列表），最深 MAX_DEPTH 层
  3) 识别叶子「单仓」（含 sites 字段）作为最终可用线路
  4) 校验可达性、去重，生成标准 storeHouse 多仓 JSON -> tvbox.json
  5) 追加更新日志 update.log

用法：
  python update_source.py

输出：
  tvbox.json    —— 可直接填进影视仓「配置地址」的源文件
  update.log    —— 每次运行的校验日志
"""

import json
import urllib.request
import urllib.error
from urllib.parse import urlsplit, urlunsplit
from datetime import datetime, timezone, timedelta

TIMEOUT = 12
MAX_DEPTH = 2
UA = ("Mozilla/5.0 (Linux; Android 12; TV) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# 种子多仓源：维护者会持续更新其中的子源，作为「自动发现新源」的来源。
# 你也可以随时往 sources.txt 里加新的种子。
SEED_HOUSES = [
    "https://raw.iqiq.io/lm317379829/PyramidStore/pyramid/py.json",
    "https://raw.iqiq.io/FongMi/TV/gh-pages/json/config.json",
]

CURATED_FILE = "sources.txt"


def idna_encode(url):
    """把中文域名转成 punycode，避免 urllib latin-1 编码报错。"""
    try:
        parts = urlsplit(url)
        host = parts.hostname
        if host and any(ord(c) > 127 for c in host):
            host = host.encode("idna").decode("ascii")
            netloc = host
            if parts.port:
                netloc += ":%d" % parts.port
            if parts.username:
                ui = parts.username
                if parts.password:
                    ui += ":" + parts.password
                netloc = ui + "@" + netloc
            return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    except Exception:
        pass
    return url


def http_get(url):
    url = idna_encode(url)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "*/*",
        "Connection": "close",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read()
    for enc in ("utf-8", "utf-8-sig", "gbk"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="ignore")


def load_json(text):
    t = text.lstrip()
    if not (t.startswith("{") or t.startswith("[")):
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def parse_house_entries(obj):
    """从多仓对象中提取子源 [(name, url)]。非多仓返回 None。"""
    if not isinstance(obj, dict):
        return None
    sh = obj.get("storeHouse")
    if isinstance(sh, list):
        out = []
        for it in sh:
            if isinstance(it, dict):
                u = it.get("sourceUrl") or it.get("url") or ""
                n = it.get("sourceName") or it.get("name") or u
                if u:
                    out.append((n, u))
        return out
    urls = obj.get("urls")
    if isinstance(urls, list):
        out = []
        for it in urls:
            if isinstance(it, dict):
                u = it.get("url") or ""
                n = it.get("name") or u
                if u:
                    out.append((n, u))
        return out
    return None


def parse_txt(text):
    """解析 TXT 列表：每行 名称,URL 或 名称$URL 或纯 URL。"""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, u = "", ""
        for sep in (",", "$", "，", "|", "\t"):
            if sep in line:
                a, b = line.split(sep, 1)
                name, u = a.strip(), b.strip()
                break
        else:
            u = line
        if u.startswith("http"):
            out.append((name, u))
    return out


def is_single(obj):
    return isinstance(obj, dict) and isinstance(obj.get("sites"), list)


def load_curated():
    """读取自维护候选列表，返回 [(name, url)]。"""
    out = []
    try:
        with open(CURATED_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                name, u = "", line
                for sep in (",", "，", "$"):
                    if sep in line:
                        a, b = line.split(sep, 1)
                        name, u = a.strip(), b.strip()
                        break
                if u.startswith("http"):
                    out.append((name, u))
    except FileNotFoundError:
        pass
    return out


def main():
    singles = {}   # url -> name （最终可用单仓）
    failed = {}    # url -> reason
    seen = set()
    queue = []     # (url, depth)

    # 种子多仓入队
    for u in SEED_HOUSES:
        queue.append((u, 0))
    # 自维护条目：直接保留（用户显式维护的，无论是单仓还是多仓都保留）
    for name, u in load_curated():
        queue.append((u, 0))
        singles.setdefault(u, name)

    # 广度优先展开
    while queue:
        u, depth = queue.pop(0)
        if u in seen or depth > MAX_DEPTH:
            continue
        seen.add(u)
        try:
            text = http_get(u)
        except Exception as e:
            failed[u] = str(e)
            continue

        obj = load_json(text)
        if obj is not None:
            if is_single(obj):
                n = obj.get("name") or obj.get("site_name") or u
                singles[u] = singles.get(u) or n
                continue
            entries = parse_house_entries(obj)
            if entries:
                for n, cu in entries:
                    singles.setdefault(cu, n)
                    queue.append((cu, depth + 1))
                continue
            failed[u] = "无法解析（未知 JSON 结构）"
        else:
            entries = parse_txt(text)
            if entries:
                for n, cu in entries:
                    singles.setdefault(cu, n)
                    queue.append((cu, depth + 1))
                continue
            failed[u] = "无法解析（非 JSON/TXT）"

    # 过滤失效条目
    final = {u: n for u, n in singles.items() if u not in failed}

    # 生成标准 storeHouse 多仓 JSON
    out = {"storeHouse": [{"sourceName": n or u, "sourceUrl": u}
                          for u, n in final.items()]}
    with open("tvbox.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # 日志
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    with open("update.log", "a", encoding="utf-8") as f:
        f.write(f"[{now}] 可用线路 {len(final)} 条，失效 {len(failed)} 个\n")
        for u, r in failed.items():
            f.write(f"   失效: {u} -> {r}\n")

    print(f"[完成] 可用线路 {len(final)} 条 -> tvbox.json")
    print(f"[完成] 失效 {len(failed)} 个（详见 update.log）")


if __name__ == "__main__":
    main()
