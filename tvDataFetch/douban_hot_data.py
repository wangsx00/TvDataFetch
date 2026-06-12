#!/usr/bin/env python3

import argparse
import json
import os
import sys
from datetime import datetime
from urllib.parse import quote

from curl_cffi import requests

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/137.0.0.0 Safari/537.36"
)
ACCEPT_LANGUAGE = "zh-CN,zh;q=0.9,en;q=0.8"
DEFAULT_TYPE = "movie"
DEFAULT_TAG = "热门"
DEFAULT_LIMIT = 20
DOUBAN_COOKIE = os.environ.get("DOUBAN_COOKIE", "").strip()


def log_step(message: str) -> None:
    time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{time}] {message}", file=sys.stderr)


def safe_preview(text: str, length: int = 160) -> str:
    return " ".join(str(text).split())[:length]


def build_request_url(options: argparse.Namespace) -> str:
    current_year = datetime.utcnow().year
    url = (
        "https://movie.douban.com/j/new_search_subjects"
        f"?sort=U&range=0,10&tags=&playable=1&start=0&year_range={current_year},{current_year}"
    )

    if options.tag and options.tag != DEFAULT_TAG:
        url += f"&tag={quote(options.tag, safe='')}"
    if options.type and options.type != DEFAULT_TYPE:
        url += f"&selectable_type={quote(options.type, safe='')}"
    if options.limit:
        url += f"&limit={options.limit}"

    return url


def fetch_hot_data(options: argparse.Namespace) -> list:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": ACCEPT_LANGUAGE,
        "Referer": "https://movie.douban.com/explore",
    }
    if DOUBAN_COOKIE:
        headers["Cookie"] = DOUBAN_COOKIE

    url = build_request_url(options)
    log_step(f"DOUBAN_COOKIE {'已配置' if DOUBAN_COOKIE else '未配置'}")
    log_step(f"抓取数据，URL: {url}")

    with requests.Session(headers=headers, impersonate="chrome136", timeout=30) as session:
        response = session.get(url, impersonate="chrome136")

    body = response.text

    if "error code: 008" in body:
        raise RuntimeError(
            "豆瓣要求登录（error code: 008）。请为 GitHub Actions 配置 DOUBAN_COOKIE secret 后重试。"
        )
    if response.status_code >= 400:
        raise RuntimeError(f"HTTP {response.status_code}: {safe_preview(body)}")

    try:
        payload = response.json()
    except Exception as error:  # noqa: BLE001
        raise RuntimeError(f"返回非 JSON: {safe_preview(body)}") from error

    data = payload.get("data")
    if not isinstance(data, list):
        raise RuntimeError(f"JSON 结构异常: {safe_preview(body)}")

    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--type", default=DEFAULT_TYPE)
    parser.add_argument("--tag", default=DEFAULT_TAG)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--ids-only", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> int:
    options = parse_args()
    try:
        data = fetch_hot_data(options)
        if options.ids_only:
            print(" ".join(str(item.get("id", "")) for item in data if item.get("id")))
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2 if options.pretty else None))
        return 0
    except Exception as error:  # noqa: BLE001
        print(f"执行出错: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
