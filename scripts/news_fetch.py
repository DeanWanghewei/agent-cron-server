#!/usr/bin/env python3
"""
新闻预采集脚本 — 每日 07:30 执行
采集科技新闻 + 全网热点，写入 JSON 供 Agent 08:00 读取摘要
"""
import asyncio
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote_plus

import httpx

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "news"
CST = timezone(timedelta(hours=8))

TIMEOUT = 15.0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, application/xml, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


# ─── 科技新闻 RSS 列表 ───
RSS_FEEDS = {
    "36氪": "https://36kr.com/feed",
    "IT之家": "https://www.ithome.com/rss/",
    "钛媒体": "https://www.tmtpost.com/feed.xml",
    "爱范儿": "https://www.ifanr.com/feed",
    "少数派": "https://sspai.com/feed",
    "虎嗅": "https://www.huxiu.com/rss/0.xml",
}


def parse_rss_items(text: str, source: str) -> list[dict]:
    """解析 RSS XML，返回标准化条目列表"""
    try:
        items = re.findall(r"<item>(.*?)</item>", text, re.DOTALL)
        results = []
        for item in items[:8]:
            title_m = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", item) or re.search(r"<title>(.*?)</title>", item)
            desc_m = re.search(r"<description><!\[CDATA\[(.*?)\]\]></description>", item) or re.search(r"<description>(.*?)</description>", item)
            link_m = re.search(r"<link>(.*?)</link>", item)
            pub_m = re.search(r"<pubDate>(.*?)</pubDate>", item)
            results.append({
                "title": title_m.group(1).strip() if title_m else "",
                "description": re.sub(r"<[^>]+>", "", desc_m.group(1).strip())[:200] if desc_m else "",
                "link": link_m.group(1).strip() if link_m else "",
                "pubdate": pub_m.group(1).strip() if pub_m else "",
                "source": source,
            })
        return results
    except Exception:
        return []


async def fetch_rss(client: httpx.AsyncClient, name: str, url: str) -> list[dict]:
    """拉取单个 RSS 源"""
    try:
        r = await client.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return []
        items = parse_rss_items(r.text, name)
        print(f"  [OK] {name}: {len(items)} 条")
        return items
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        return []


async def fetch_zhihu_hot(client: httpx.AsyncClient) -> list[dict]:
    """知乎热榜"""
    try:
        r = await client.get(
            "https://www.zhihu.com/api/v4/search/top_search",
            headers={**HEADERS, "Referer": "https://www.zhihu.com/"},
            timeout=TIMEOUT
        )
        if r.status_code != 200:
            return []
        data = r.json()
        words = data.get("top_search", {}).get("words", [])[:10]
        results = [
            {"title": w.get("query", ""), "description": w.get("desc", ""), "source": "知乎热榜"}
            for w in words
        ]
        print(f"  [OK] 知乎热榜: {len(results)} 条")
        return results
    except Exception as e:
        print(f"  [FAIL] 知乎热榜: {e}")
        return []


async def fetch_qq_hot(client: httpx.AsyncClient) -> list[dict]:
    """腾讯新闻热点 RSS"""
    try:
        r = await client.get("https://news.qq.com/rss/newsoul.xml", headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return []
        items = parse_rss_items(r.text, "腾讯新闻")
        print(f"  [OK] 腾讯新闻: {len(items)} 条")
        return items
    except Exception as e:
        print(f"  [FAIL] 腾讯新闻: {e}")
        return []


async def fetch_ifeng_news(client: httpx.AsyncClient) -> list[dict]:
    """凤凰网 RSS"""
    try:
        r = await client.get("https://www.ifeng.com/rss.php", headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return []
        items = parse_rss_items(r.text, "凤凰网")
        print(f"  [OK] 凤凰网: {len(items)} 条")
        return items
    except Exception as e:
        print(f"  [FAIL] 凤凰网: {e}")
        return []


async def fetch_ithome_news(client: httpx.AsyncClient, keyword: str) -> list[dict]:
    """IT之家搜索 RSS（按关键词）"""
    try:
        url = f"https://www.ithome.com/rss/{keyword}.xml"
        r = await client.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return []
        items = parse_rss_items(r.text, f"IT之家/{keyword}")
        return items
    except Exception:
        return []


async def fetch_sohu_news(client: httpx.AsyncClient) -> list[dict]:
    """搜狐新闻 RSS"""
    try:
        r = await client.get("https://feed.sohu.com.cn/news/rss_list.xml", headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return []
        items = parse_rss_items(r.text, "搜狐新闻")
        print(f"  [OK] 搜狐新闻: {len(items)} 条")
        return items
    except Exception as e:
        print(f"  [FAIL] 搜狐新闻: {e}")
        return []


async def fetch_tencent_news(client: httpx.AsyncClient) -> list[dict]:
    """腾讯科技 RSS"""
    try:
        r = await client.get("https://tech.qq.com/rss.xml", headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return []
        items = parse_rss_items(r.text, "腾讯科技")
        print(f"  [OK] 腾讯科技: {len(items)} 条")
        return items
    except Exception as e:
        print(f"  [FAIL] 腾讯科技: {e}")
        return []


def is_recent(pubdate: str, hours: int = 48) -> bool:
    """简单判断条目是否在最近 hours 小时内发布"""
    if not pubdate:
        return True  # 无日期假定为最近
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(pubdate)
        delta = datetime.now(CST) - dt.replace(tzinfo=timezone.utc).astimezone(CST)
        return delta.total_seconds() < hours * 3600
    except Exception:
        return True


async def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(CST).strftime("%Y-%m-%d")
    result_file = DATA_DIR / f"{today}.json"

    async with httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(60.0)) as client:
        tasks = {}

        # ── RSS 科技新闻源 ──
        for name, url in RSS_FEEDS.items():
            tasks[f"rss:{name}"] = fetch_rss(client, name, url)

        # ── 备用搜索 RSS（IT之家分类）──
        for kw in ["ai", "mobile", "internet"]:
            tasks[f"ithome:{kw}"] = fetch_ithome_news(client, kw)

        # ── 热点 ──
        tasks["知乎热榜"] = fetch_zhihu_hot(client)
        tasks["腾讯新闻"] = fetch_qq_hot(client)
        tasks["搜狐新闻"] = fetch_sohu_news(client)
        tasks["腾讯科技"] = fetch_tencent_news(client)
        tasks["凤凰网"] = fetch_ifeng_news(client)

        print(f"[{datetime.now(CST).strftime('%H:%M:%S')}] 开始并发采集 {len(tasks)} 个数据源...")
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    # 整理
    tech_news = []
    hot_topics = []
    sources_used = set()

    for (key, result) in zip(tasks.keys(), results):
        if isinstance(result, Exception):
            continue
        if not result:
            continue
        for item in result:
            sources_used.add(item.get("source", "unknown"))
            # 判断是否科技新闻（RSS 源都是）
            if key.startswith("rss:") or key.startswith("ithome:") or key.startswith("tencent"):
                # 过滤过老条目（48小时外）
                if is_recent(item.get("pubdate", ""), hours=48):
                    tech_news.append(item)
            else:
                hot_topics.append(item)

    output = {
        "date": today,
        "fetched_at": datetime.now(CST).isoformat(),
        "tech_news": tech_news,
        "hot_topics": hot_topics,
        "sources_used": sorted(sources_used),
    }

    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n完成：{result_file}")
    print(f"  科技新闻：{len(tech_news)} 条")
    print(f"  热点话题：{len(hot_topics)} 条")
    print(f"  来源：{', '.join(sorted(sources_used))}")


if __name__ == "__main__":
    asyncio.run(main())
