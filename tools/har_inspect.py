#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 HAR 抓包文件快速定位业务接口，用于逆向登录/业务接口。

用法示例:
  python har_inspect.py a.har                     # 概览: 条目数 + host 分布 + 方法/状态分布
  python har_inspect.py a.har -H www.zhihu.com    # 只看指定域名
  python har_inspect.py a.har -k login,token,sign # 按关键词(逗号分隔)过滤 URL
  python har_inspect.py a.har -t                  # 按时间排序打印时间线
  python har_inspect.py a.har -H www.zhihu.com -i 3  # 深挖过滤后第 3 个条目
"""
import argparse
import base64
import json
import sys
import urllib.parse as up
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["log"]["entries"]


def host(url):
    return up.urlparse(url).netloc


def pathq(url):
    p = up.urlparse(url)
    return p.path + (("?" + p.query) if p.query else "")


def decode_body(content):
    """HAR 里响应体可能存成 base64, 需要还原。"""
    txt = content.get("text", "")
    if content.get("encoding") == "base64" and txt:
        try:
            txt = base64.b64decode(txt).decode("utf-8", "replace")
        except Exception:
            pass
    return txt


def overview(entries):
    n = len(entries)
    print("总条目数:", n)
    print("\n=== host 分布 (业务接口 vs 静态资源 vs 埋点) ===")
    for h, c in Counter(host(e["request"]["url"]) for e in entries).most_common():
        print(f"  {c:5d}  {h}")
    print("\n=== 方法分布 ===", dict(Counter(e["request"]["method"] for e in entries)))
    print("=== 状态码分布 ===", dict(Counter(e["response"]["status"] for e in entries)))


def filter_entries(entries, hostname=None, keywords=None):
    out = entries
    if hostname:
        out = [e for e in out if host(e["request"]["url"]) == hostname]
    if keywords:
        out = [e for e in out if any(k in e["request"]["url"] for k in keywords)]
    return out


def show_list(entries):
    for i, e in enumerate(entries):
        r = e["request"]
        print(f"[{i:3d}] {r['method']:6s} {e['response']['status']} "
              f"{host(r['url'])} {pathq(r['url'])[:100]}")


def show_timeline(entries):
    for e in sorted(entries, key=lambda x: x["startedDateTime"]):
        r = e["request"]
        print(f"{e['startedDateTime'][11:23]}  {r['method']:6s} "
              f"{e['response']['status']}  {pathq(r['url'])[:110]}")


def show_detail(entries, idx):
    e = entries[idx]
    r = e["request"]
    print("=== 请求 ===")
    print(f"{r['method']} {r['url']}")
    print("-- 关键请求头 --")
    keep = {"cookie", "authorization", "x-xsrftoken", "x-zse-93", "x-zse-96",
            "x-zst-81", "content-type", "referer", "origin", "user-agent"}
    for h in r["headers"]:
        if h["name"].lower() in keep:
            print(f"  {h['name']}: {h['value'][:200]}")
    qs = r.get("queryString", [])
    if qs:
        print("-- Query 参数 --")
        for q in qs:
            print(f"  {q['name']} = {q['value']}")
    pd = r.get("postData", {})
    if pd:
        print(f"-- POST 数据 (mimeType={pd.get('mimeType')}) --")
        print("  " + (pd.get("text", "")[:800]))
    print("\n=== 响应 ===")
    print(f"status={e['response']['status']}")
    print("-- Set-Cookie --")
    for h in e["response"]["headers"]:
        if h["name"].lower() == "set-cookie":
            print(f"  {h['value'][:200]}")
    body = decode_body(e["response"]["content"])
    print(f"-- 响应体 (长度 {len(body)}) --")
    print(body[:800])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("har")
    ap.add_argument("-H", "--host")
    ap.add_argument("-k", "--keywords")
    ap.add_argument("-t", "--timeline", action="store_true")
    ap.add_argument("-i", "--index", type=int)
    args = ap.parse_args()

    entries = load(args.har)
    kws = args.keywords.split(",") if args.keywords else None
    sel = filter_entries(entries, args.host, kws)

    if args.index is not None:
        show_detail(sel, args.index)
    elif args.timeline:
        show_timeline(sel)
    elif args.host or kws:
        show_list(sel)
    else:
        overview(entries)


if __name__ == "__main__":
    main()
