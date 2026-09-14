#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
任天堂 NES 与红白机 (FC/FDS) 跨区整合数据全能引擎 (All-in-One Single Script)

核心能力：
1. 爬取并清洗中文维基百科的 NES、FC卡带、FC磁碟机 (FDS) 游戏列表；
2. 融合 No-Intro 官方 DAT 克隆树 (NES/FDS) 的 Parent-Clone 官方克隆关系；
3. 融合 rom-name-cn 子模块的中英文对照库与中文别名映射 (name_alias)；
4. 深度识别并合并属于同一款游戏的美版与日版版本，放入同一个标准数据结构中；
5. 自动抓取 Bilibili 空间合集《红白机游戏编年史系列》全部 98 期视频分段与起播时间轴；
6. 基于别名拆解与发售年份定锚 (Temporal Disambiguation) 精准对齐解说视频；
7. 全格式全量导出：JSON, Pickle, Python 原生模块, CSV 表格, Excel 富格式工作簿 (.xlsx)；
8. 编译完全自包含的单文件交互式前端页面 data/fc_nes_games.html (含资源下载中心)；
9. 内置 10 项严密无框架标准库质量断言校验逻辑 (--verify)。
"""

import os
import sys
import re
import csv
import glob
import json
import time
import ssl
import pickle
import logging
import urllib.request
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime
from urllib.parse import urljoin, unquote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    openpyxl = None

# 配置日志输出格式
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("fetch_fc_nes")


# ==============================================================================
# 第一部分: Bilibili 红白机游戏编年史合集视频抓取与章节提取
# ==============================================================================

MID = 3546818172423070
SEASON_ID = 4877626

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': f'https://space.bilibili.com/{MID}/lists/{SEASON_ID}'
}

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

EXCLUDE_NAMES = {
    '前言', '尾声', '结语', '片头', '片尾', '总结', '开场', 
    '结束语', '下期预告', '介绍', '说明', '闲聊', '后记'
}

TIMESTAMP_PATTERN = re.compile(r'(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\s+([^\r\n]+)')


def fetch_json_with_retry(url: str, retries: int = 3, timeout: int = 10) -> Dict[str, Any]:
    """带重试的网络请求"""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=timeout) as resp:
                raw = resp.read().decode('utf-8')
                return json.loads(raw)
        except Exception as e:
            if attempt == retries - 1:
                logger.error(f"请求失败 ({url}): {e}")
                raise
            time.sleep(1.0 * (attempt + 1))
    return {}


def collect_bilibili_season_videos(cache_dir: str = "cache/bilibili") -> List[Dict[str, Any]]:
    """获取合集中的所有视频基本信息"""
    os.makedirs(cache_dir, exist_ok=True)
    all_archives = []
    
    # 98 个视频，每页 30 条，共 4 页
    for pn in range(1, 5):
        page_cache = os.path.join(cache_dir, f"page_{pn}.json")
        if os.path.exists(page_cache):
            with open(page_cache, "r", encoding="utf-8") as f:
                pdata = json.load(f)
        else:
            url = f'https://api.bilibili.com/x/polymer/web-space/seasons_archives_list?mid={MID}&season_id={SEASON_ID}&page_num={pn}&page_size=30'
            logger.info(f"正在拉取合集第 {pn} 页视频列表...")
            pdata = fetch_json_with_retry(url)
            with open(page_cache, "w", encoding="utf-8") as f:
                json.dump(pdata, f, ensure_ascii=False, indent=2)
            time.sleep(0.3)
            
        archives = pdata.get('data', {}).get('archives', [])
        all_archives.extend(archives)

    logger.info(f"成功获取合集视频总数: {len(all_archives)} 个")
    return all_archives


def fetch_all_video_details(archives: List[Dict[str, Any]], cache_dir: str = "cache/bilibili") -> List[Dict[str, Any]]:
    """批量获取各视频详细简介并解析分段章节"""
    video_cache_dir = os.path.join(cache_dir, "videos")
    os.makedirs(video_cache_dir, exist_ok=True)
    
    segments_list = []

    for idx, arc in enumerate(archives):
        bvid = arc['bvid']
        title = arc['title']
        v_cache = os.path.join(video_cache_dir, f"{bvid}.json")
        
        vd = None
        if os.path.exists(v_cache):
            try:
                with open(v_cache, "r", encoding="utf-8") as f:
                    vd = json.load(f)
            except Exception:
                vd = None
                
        if not vd or vd.get('code') != 0:
            view_url = f'https://api.bilibili.com/x/web-interface/view?bvid={bvid}'
            try:
                vd = fetch_json_with_retry(view_url)
                with open(v_cache, "w", encoding="utf-8") as f:
                    json.dump(vd, f, ensure_ascii=False, indent=2)
                time.sleep(0.15)
            except Exception as e:
                logger.warning(f"获取视频详情失败 {bvid}: {e}")
                continue

        desc = vd.get('data', {}).get('desc', '')
        matches = TIMESTAMP_PATTERN.findall(desc)
        
        # 尝试提取视频标题中的发售年份
        year_match = re.search(r'(\d{4})年', title)
        video_year = int(year_match.group(1)) if year_match else None
        
        for h, m, s, gname in matches:
            gname = gname.strip()
            # 清理编号如 "01. ", "1、"
            gname_clean = re.sub(r'^\d+[\.、\s\-]+', '', gname).strip()
            if gname_clean in EXCLUDE_NAMES or not gname_clean:
                continue
                
            h_val = int(h) if h else 0
            seconds = h_val * 3600 + int(m) * 60 + int(s)
            time_str = f"{h+':' if h else ''}{m}:{s}"
            # 构造 B 站带起播时间参数的跳转链接
            url = f"https://www.bilibili.com/video/{bvid}/?t={seconds}"
            
            segments_list.append({
                "bvid": bvid,
                "aid": arc.get('aid'),
                "video_title": title,
                "video_year": video_year,
                "video_pic": arc.get('pic'),
                "chapter_raw": gname,
                "chapter_name": gname_clean,
                "timestamp": time_str,
                "seconds": seconds,
                "url": url,
            })

    logger.info(f"所有视频解析完成，共提取游戏分段章节: {len(segments_list)} 个")
    
    # 保存结果
    output_path = os.path.join(cache_dir, "bilibili_segments.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(segments_list, f, ensure_ascii=False, indent=2)
    logger.info(f"已保存视频分段数据: {output_path}")
    
    return segments_list


# ==============================================================================
# 第二部分: Bilibili 视频分段与 FC/NES 游戏库智能对齐引擎
# ==============================================================================

MANUAL_ALIAS_MAP = {
    "大力水手": "popeye",
    "大力水手学英语": "popeye-no-eigo-asobi",
    "大力水手英语": "popeye-no-eigo-asobi",
    "大金刚": "donkey-kong",
    "大金刚2": "donkey-kong-jr",
    "小金刚": "donkey-kong-jr",
    "大金刚3": "donkey-kong-3",
    "大金刚jr": "donkey-kong-jr",
    "小金刚学算术": "donkey-kong-jr-math",
    "小金刚算术": "donkey-kong-jr-math",
    "麻将": "mahjong",
    "五子棋": "gomoku-narabe-renju",
    "五子连珠": "gomoku-narabe-renju",
    "越野摩托": "excitebike",
    "越野机车": "excitebike",
    "培基": "basic-family",
    "家庭电脑basic": "basic-family",
    "培基语音": "basic-family",
    "培基v3": "family-basic-v3",
    "培基语音第三版": "family-basic-v3",
    "企鹅动物园": "antarctic-adventure",
    "企鹅大冒险": "antarctic-adventure",
    "南极探险": "antarctic-adventure",
    "农夫": "ikki",
    "一揆": "ikki",
    "公路追逐": "route-16-turbo",
    "路线16": "route-16-turbo",
    "火爆摔角": "tag-team-match-m-u-s-c-l-e",
    "筋肉人": "tag-team-match-m-u-s-c-l-e",
    "摔角": "pro-wrestling",
    "职业摔角": "pro-wrestling",
    "网球": "tennis",
    "棒球": "baseball",
    "高尔夫": "golf",
    "足球": "soccer",
    "排球": "volleyball",
    "冰球": "ice-hockey",
    "吃豆人": "pac-man",
    "淘金者": "lode-runner",
    "小蜜蜂": "galaxian",
    "大蜜蜂": "galaga",
    "铁板阵": "xevious",
    "转转乐园": "clu-clu-land",
    "敲冰块": "ice-climber",
    "气球大战": "balloon-fight",
    "打鸭子": "duck-hunt",
    "荒野枪手": "wild-gunman",
    "警技射击": "hogan-s-alley",
    "马里奥兄弟": "mario-bros",
    "超级马里奥兄弟": "super-mario-bros",
    "超级马里奥兄弟2": "super-mario-bros-2",
    "超级马里奥兄弟3": "super-mario-bros-3",
}

def normalize_text(text: Optional[str]) -> str:
    """规范化文本，过滤标点并对齐同义词"""
    if not text:
        return ""
    s = text.lower().strip()
    
    # 同义词转换
    s = s.replace("马里奥", "马力欧").replace("mario", "马力欧")
    s = s.replace("大金刚2", "大金刚jr").replace("小金刚", "大金刚jr")
    s = s.replace("五子棋", "五子连珠")
    s = s.replace("越野摩托", "越野机车")
    s = s.replace("学算术", "算术").replace("算数", "算术")
    s = s.replace("学英语", "英语")
    
    # 清理所有符号与空白
    s = re.sub(r'[\s\-_:：·・/／\(\)（）「」『』!！\?？\$\&\[\]\+\.\'\",，、]', '', s)
    return s


def extract_year(date_str: Optional[str]) -> Optional[int]:
    """从发售日字符串提取年份"""
    if not date_str:
        return None
    m = re.search(r'(\d{4})', date_str)
    return int(m.group(1)) if m else None


class BilibiliMatcher:
    def __init__(self, games: List[Dict[str, Any]], alias_json_path: str = "rom-name-cn/name_alias(Chinese).json"):
        self.games = games
        self.game_by_id = {g["id"]: g for g in games}
        self.lookup: Dict[str, List[Dict[str, Any]]] = {}
        self._build_index(alias_json_path)

    def _add_to_index(self, key: Optional[str], game: Dict[str, Any]):
        nk = normalize_text(key)
        if nk:
            if nk not in self.lookup:
                self.lookup[nk] = []
            if game not in self.lookup[nk]:
                self.lookup[nk].append(game)

    def _build_index(self, alias_json_path: str):
        # 1. 索引游戏主属性与版本属性
        for g in self.games:
            self._add_to_index(g.get("id"), g)
            self._add_to_index(g.get("title_zh"), g)
            self._add_to_index(g.get("title_en"), g)
            self._add_to_index(g.get("title_ja"), g)
            
            for v in g.get("versions", {}).values():
                self._add_to_index(v.get("title_zh"), g)
                self._add_to_index(v.get("title_en"), g)
                self._add_to_index(v.get("title_ja"), g)

        # 2. 索引 rom-name-cn 别名库
        if os.path.exists(alias_json_path):
            try:
                with open(alias_json_path, "r", encoding="utf-8") as f:
                    alias_data = json.load(f)
                for main_name, alias_info in alias_data.items():
                    aliases = alias_info.get("alias", [])
                    all_names = [main_name] + aliases
                    matched_games = []
                    for a in all_names:
                        na = normalize_text(a)
                        if na in self.lookup:
                            matched_games.extend(self.lookup[na])
                    if matched_games:
                        unique_games = {g["id"]: g for g in matched_games}.values()
                        for a in all_names:
                            for mg in unique_games:
                                self._add_to_index(a, mg)
            except Exception as e:
                logger.warning(f"加载 rom-name-cn 别名库失败: {e}")

    def match_segment(self, segment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """为单个视频分段匹配对应的游戏实体"""
        raw_name = segment.get("chapter_name", "")
        video_year = segment.get("video_year")

        # 1. 拆解斜杠候选别名与副标题 (如 "大金刚2/小金刚", "女武神冒险-时之钥匙传说")
        candidates = [raw_name]
        for sep in ['/', '／', '、', ' - ', '-', '——', '：', ':', ' ']:
            if sep in raw_name:
                candidates.extend([p.strip() for p in raw_name.split(sep) if len(p.strip()) >= 2])

        # 2. 优先查显式人工映射表 (优先精确匹配候选词，再降序匹配包含长词)
        for cand in candidates:
            if cand in MANUAL_ALIAS_MAP:
                gid = MANUAL_ALIAS_MAP[cand]
                if gid in self.game_by_id:
                    return self.game_by_id[gid]

        for k in sorted(MANUAL_ALIAS_MAP.keys(), key=len, reverse=True):
            if len(k) >= 4 and k in raw_name:
                gid = MANUAL_ALIAS_MAP[k]
                if gid in self.game_by_id:
                    return self.game_by_id[gid]

        matched_candidates = []

        for cand in candidates:
            # 直接匹配
            nc = normalize_text(cand)
            if nc and nc in self.lookup:
                matched_candidates.extend(self.lookup[nc])
                
            # 去除后缀尝试 (初代/一代/fc版/红白机版)
            clean_c = re.sub(r'(初代|一代|fc版|红白机版|卡带版)$', '', nc)
            if clean_c and clean_c in self.lookup:
                matched_candidates.extend(self.lookup[clean_c])

        if not matched_candidates:
            # 尝试子串包含匹配 (长度 >= 4)
            for cand in candidates:
                nc = normalize_text(cand)
                if len(nc) >= 4:
                    for k, g_list in self.lookup.items():
                        if len(k) >= 4 and (nc in k or k in nc):
                            matched_candidates.extend(g_list)
                            break

        if not matched_candidates:
            return None

        # 去重
        unique_matched = list({g["id"]: g for g in matched_candidates}.values())
        if len(unique_matched) == 1:
            return unique_matched[0]

        # 3. 多候选时利用发售年份定锚 (Temporal Disambiguation)
        if video_year:
            best_game = None
            min_diff = 999
            for g in unique_matched:
                jp_year = extract_year(g.get("release_dates", {}).get("japan"))
                na_year = extract_year(g.get("release_dates", {}).get("north_america"))
                g_year = jp_year or na_year
                if g_year:
                    diff = abs(g_year - video_year)
                    if diff < min_diff:
                        min_diff = diff
                        best_game = g
            if best_game and min_diff <= 2:
                return best_game

        return unique_matched[0]


def attach_bilibili_videos_to_games(
    games: List[Dict[str, Any]], 
    segments_path: str = "cache/bilibili/bilibili_segments.json"
) -> Dict[str, Any]:
    """将 Bilibili 视频分段匹配并挂载到游戏列表中"""
    if not os.path.exists(segments_path):
        logger.warning(f"未找到 B 站分段数据文件: {segments_path}，跳过视频信息挂载")
        for g in games:
            g["video"] = None
        return {"matched_count": 0, "total_segments": 0}

    with open(segments_path, "r", encoding="utf-8") as f:
        segments = json.load(f)

    matcher = BilibiliMatcher(games)
    matched_count = 0
    matched_game_ids = set()

    for seg in segments:
        hit_game = matcher.match_segment(seg)
        if hit_game:
            # 挂载视频信息 (如果已有，保留最早或最匹配的)
            if not hit_game.get("video"):
                hit_game["video"] = {
                    "bvid": seg["bvid"],
                    "aid": seg.get("aid"),
                    "video_title": seg["video_title"],
                    "chapter_name": seg["chapter_name"],
                    "timestamp": seg["timestamp"],
                    "seconds": seg["seconds"],
                    "url": seg["url"]
                }
                matched_count += 1
                matched_game_ids.add(hit_game["id"])

    # 对于没有匹配到视频的游戏，显式置为 null
    for g in games:
        if "video" not in g:
            g["video"] = None

    logger.info(f"B站合集视频章节对齐完成: 成功为 {len(matched_game_ids)} 款游戏绑定解说视频与精准起播时间轴")
    return {
        "matched_games_count": len(matched_game_ids),
        "total_segments": len(segments),
        "coverage_ratio": len(matched_game_ids) / len(segments) if segments else 0
    }


# ==============================================================================
# 第三部分: 自包含交互式前端页面 HTML 模板与代码生成器
# ==============================================================================

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>任天堂 NES 与红白机 (FC/FDS) 游戏库 - 跨区整合数据库</title>
  <meta name="description" content="任天堂 NES 与红白机 (FC/FDS) 跨区整合游戏信息库，深度融合 No-Intro DAT 克隆树与 rom-name-cn 权威对照库，美日同款游戏一站式检索。">
  <style>
    :root {
      --bg-primary: #0a0e17;
      --bg-secondary: #111827;
      --bg-card: rgba(17, 24, 39, 0.75);
      --bg-card-hover: rgba(30, 41, 59, 0.85);
      --border-color: rgba(255, 255, 255, 0.08);
      --border-glow: rgba(230, 0, 18, 0.4);
      --text-main: #f3f4f6;
      --text-sub: #9ca3af;
      --text-muted: #6b7280;
      
      --nintendo-red: #e60012;
      --nintendo-red-glow: rgba(230, 0, 18, 0.3);
      --badge-nes: #3b82f6;
      --badge-fc: #ef4444;
      --badge-fds: #f59e0b;
      --badge-cross: #10b981;
      --accent-cyan: #06b6d4;
      
      --radius-sm: 6px;
      --radius-md: 12px;
      --radius-lg: 16px;
      --transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      background-color: var(--bg-primary);
      background-image: 
        radial-gradient(circle at 15% 15%, rgba(230, 0, 18, 0.08) 0%, transparent 40%),
        radial-gradient(circle at 85% 85%, rgba(6, 182, 212, 0.06) 0%, transparent 40%),
        radial-gradient(circle at 50% 50%, rgba(16, 185, 129, 0.04) 0%, transparent 50%);
      background-attachment: fixed;
      color: var(--text-main);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
      min-height: 100vh;
      line-height: 1.5;
    }

    /* 顶部导航与英雄区域 */
    header {
      background: rgba(10, 14, 23, 0.8);
      backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--border-color);
      position: sticky;
      top: 0;
      z-index: 100;
    }

    .navbar {
      max-width: 1440px;
      margin: 0 auto;
      padding: 14px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      text-decoration: none;
      color: inherit;
    }

    .brand-logo {
      width: 38px;
      height: 38px;
      background: linear-gradient(135deg, #e60012 0%, #99000a 100%);
      border-radius: var(--radius-sm);
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      font-weight: 900;
      font-size: 1.15rem;
      letter-spacing: -0.5px;
      box-shadow: 0 4px 12px var(--nintendo-red-glow);
    }

    .brand-title {
      font-size: 1.2rem;
      font-weight: 700;
      letter-spacing: -0.3px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .brand-subtitle {
      font-size: 0.8rem;
      color: var(--text-sub);
    }

    .header-links {
      display: flex;
      gap: 12px;
      align-items: center;
    }

    .nav-btn {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--border-color);
      color: var(--text-sub);
      padding: 7px 14px;
      border-radius: var(--radius-sm);
      font-size: 0.85rem;
      text-decoration: none;
      transition: var(--transition);
      display: inline-flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
      user-select: none;
    }

    .nav-btn:hover {
      background: rgba(255, 255, 255, 0.12);
      color: var(--text-main);
      border-color: rgba(255, 255, 255, 0.2);
    }

    /* 导航栏专属下载按钮 */
    .btn-download-nav {
      background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(6, 182, 212, 0.15) 100%);
      border: 1px solid rgba(16, 185, 129, 0.4);
      color: #34d399;
      font-weight: 600;
      box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2);
    }

    .btn-download-nav:hover {
      background: linear-gradient(135deg, rgba(16, 185, 129, 0.3) 0%, rgba(6, 182, 212, 0.3) 100%);
      color: #fff;
      border-color: #34d399;
      box-shadow: 0 4px 14px rgba(16, 185, 129, 0.35);
      transform: translateY(-1px);
    }

    /* 容器布局 */
    main {
      max-width: 1440px;
      margin: 0 auto;
      padding: 24px 24px 60px;
    }

    /* 统计看板 */
    .stats-bar {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 14px;
      margin-bottom: 24px;
    }

    .stat-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 16px 20px;
      backdrop-filter: blur(8px);
      position: relative;
      overflow: hidden;
      transition: var(--transition);
    }

    .stat-card:hover {
      border-color: rgba(255, 255, 255, 0.15);
      transform: translateY(-2px);
    }

    .stat-card::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 4px;
      height: 100%;
      background: var(--accent, var(--nintendo-red));
    }

    .stat-value {
      font-size: 1.8rem;
      font-weight: 800;
      color: #fff;
      line-height: 1.2;
      font-feature-settings: "tnum";
    }

    .stat-label {
      font-size: 0.8rem;
      color: var(--text-sub);
      margin-top: 4px;
    }

    /* 筛选与搜索工具条 */
    .filter-panel {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 18px 20px;
      margin-bottom: 20px;
      backdrop-filter: blur(8px);
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .search-row {
      display: flex;
      gap: 14px;
      align-items: center;
      flex-wrap: wrap;
    }

    .search-wrapper {
      flex: 1;
      min-width: 260px;
      position: relative;
    }

    .search-icon {
      position: absolute;
      left: 14px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
      pointer-events: none;
    }

    .search-input {
      width: 100%;
      background: rgba(0, 0, 0, 0.35);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      padding: 11px 16px 11px 42px;
      color: var(--text-main);
      font-size: 0.95rem;
      outline: none;
      transition: var(--transition);
    }

    .search-input:focus {
      border-color: var(--nintendo-red);
      box-shadow: 0 0 0 3px var(--nintendo-red-glow);
    }

    .search-input::placeholder {
      color: var(--text-muted);
    }

    .select-controls {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }

    .custom-select {
      background: rgba(0, 0, 0, 0.35);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      padding: 10px 14px;
      color: var(--text-main);
      font-size: 0.9rem;
      outline: none;
      cursor: pointer;
      min-width: 150px;
    }

    .custom-select:focus {
      border-color: var(--nintendo-red);
    }

    .filter-pills {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
    }

    .filter-pill {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border-color);
      color: var(--text-sub);
      padding: 6px 16px;
      border-radius: 20px;
      font-size: 0.85rem;
      cursor: pointer;
      transition: var(--transition);
      display: inline-flex;
      align-items: center;
      gap: 6px;
      user-select: none;
    }

    .filter-pill:hover {
      background: rgba(255, 255, 255, 0.08);
      color: var(--text-main);
    }

    .filter-pill.active {
      background: #fff;
      color: #000;
      border-color: #fff;
      font-weight: 600;
    }

    .filter-pill.pill-cross.active {
      background: var(--badge-cross);
      color: #fff;
      border-color: var(--badge-cross);
    }

    .filter-pill.pill-video.active {
      background: #fb7299;
      color: #fff;
      border-color: #fb7299;
    }

    .filter-pill.pill-nes.active {
      background: var(--badge-nes);
      color: #fff;
      border-color: var(--badge-nes);
    }

    .filter-pill.pill-fc.active {
      background: var(--badge-fc);
      color: #fff;
      border-color: var(--badge-fc);
    }

    .filter-pill.pill-fds.active {
      background: var(--badge-fds);
      color: #fff;
      border-color: var(--badge-fds);
    }

    /* 视图切换与结果信息 */
    .results-info-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      font-size: 0.875rem;
      color: var(--text-sub);
      flex-wrap: wrap;
      gap: 12px;
    }

    .result-count-highlight {
      color: var(--nintendo-red);
      font-weight: 700;
    }

    .view-toggle {
      display: flex;
      background: rgba(0, 0, 0, 0.35);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      overflow: hidden;
    }

    .view-btn {
      background: transparent;
      border: none;
      padding: 6px 12px;
      color: var(--text-muted);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.85rem;
      transition: var(--transition);
    }

    .view-btn.active {
      background: rgba(255, 255, 255, 0.12);
      color: var(--text-main);
      font-weight: 600;
    }

    /* 徽章 Badge 样式 */
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 700;
      letter-spacing: 0.2px;
      line-height: 1.3;
      white-space: nowrap;
    }

    .badge-nes {
      background: rgba(59, 130, 246, 0.18);
      color: #60a5fa;
      border: 1px solid rgba(59, 130, 246, 0.35);
    }

    .badge-fc {
      background: rgba(239, 68, 68, 0.18);
      color: #f87171;
      border: 1px solid rgba(239, 68, 68, 0.35);
    }

    .badge-fds {
      background: rgba(245, 158, 11, 0.18);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.35);
    }

    .badge-cross {
      background: rgba(16, 185, 129, 0.18);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.35);
    }

    /* B站解说视频徽章与卡片样式 */
    .bili-btn, .bili-tag {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      background: rgba(251, 114, 153, 0.15);
      border: 1px solid rgba(251, 114, 153, 0.4);
      color: #fb7299;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
      text-decoration: none;
      transition: var(--transition);
      line-height: 1.2;
    }

    .bili-btn:hover, .bili-tag:hover {
      background: #fb7299;
      color: #fff;
      border-color: #fb7299;
      box-shadow: 0 0 10px rgba(251, 114, 153, 0.5);
    }

    .bili-card {
      margin-top: 16px;
      background: rgba(251, 114, 153, 0.08);
      border: 1px solid rgba(251, 114, 153, 0.3);
      border-radius: var(--radius-sm);
      padding: 14px 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }

    /* 表格视图 */
    .table-container {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      overflow-x: auto;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
      text-align: left;
    }

    th {
      background: rgba(17, 24, 39, 0.95);
      padding: 12px 14px;
      color: var(--text-sub);
      font-weight: 600;
      border-bottom: 1px solid var(--border-color);
      white-space: nowrap;
      font-size: 0.85rem;
    }

    td {
      padding: 10px 14px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      color: var(--text-main);
      vertical-align: middle;
    }

    tr:hover td {
      background: rgba(255, 255, 255, 0.03);
      cursor: pointer;
    }

    /* 表格上下子格子（英文/日文、美版/日版） */
    .split-cell-box {
      display: flex;
      flex-direction: column;
      gap: 4px;
      min-width: 150px;
    }

    .sub-cell {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 3px 8px;
      border-radius: 4px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.05);
      font-size: 0.83rem;
      line-height: 1.35;
      transition: background 0.15s ease;
    }

    .sub-cell:hover {
      background: rgba(255, 255, 255, 0.07);
    }

    .sub-cell-top {
      border-left: 2.5px solid #3b82f6;
    }

    .sub-cell-bottom {
      border-left: 2.5px solid #ef4444;
    }

    .sub-tag {
      font-size: 0.65rem;
      font-weight: 700;
      padding: 1px 5px;
      border-radius: 3px;
      flex-shrink: 0;
      letter-spacing: 0.3px;
      line-height: 1.2;
    }

    .tag-en { background: rgba(59, 130, 246, 0.2); color: #93c5fd; }
    .tag-ja { background: rgba(239, 68, 68, 0.2); color: #fca5a5; }
    .tag-na { background: rgba(59, 130, 246, 0.2); color: #93c5fd; }
    .tag-jp { background: rgba(239, 68, 68, 0.2); color: #fca5a5; }

    .sub-val {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 280px;
    }

    .sub-val-ja {
      color: var(--text-sub);
    }

    /* 网格卡片视图 */
    .games-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(310px, 1fr));
      gap: 18px;
    }

    .game-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 16px;
      backdrop-filter: blur(8px);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: var(--transition);
      cursor: pointer;
      position: relative;
    }

    .game-card:hover {
      border-color: rgba(255, 255, 255, 0.2);
      transform: translateY(-3px);
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
    }

    .game-card.is-cross {
      border-color: rgba(16, 185, 129, 0.3);
    }

    .game-card.is-cross::after {
      content: '';
      position: absolute;
      top: 0;
      right: 0;
      width: 0;
      height: 0;
      border-style: solid;
      border-width: 0 28px 28px 0;
      border-color: transparent var(--badge-cross) transparent transparent;
      border-top-right-radius: var(--radius-md);
    }

    .badges-row {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      margin-bottom: 8px;
    }

    .game-title-zh {
      font-size: 1.15rem;
      font-weight: 700;
      color: #fff;
      margin-bottom: 4px;
      line-height: 1.35;
    }

    .game-title-en {
      font-size: 0.9rem;
      color: var(--text-sub);
      margin-bottom: 2px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .game-title-ja {
      font-size: 0.8rem;
      color: var(--text-muted);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .card-meta {
      border-top: 1px solid var(--border-color);
      margin-top: 14px;
      padding-top: 12px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      font-size: 0.8rem;
      color: var(--text-sub);
    }

    .meta-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .meta-label {
      color: var(--text-muted);
    }

    .publisher-tag {
      max-width: 170px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      text-align: right;
    }

    /* 分页控制器 */
    .pagination-bar {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 8px;
      margin-top: 32px;
      margin-bottom: 48px;
      flex-wrap: wrap;
    }

    .page-btn {
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      color: var(--text-sub);
      min-width: 40px;
      height: 40px;
      padding: 0 12px;
      border-radius: var(--radius-sm);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-size: 0.9rem;
      transition: var(--transition);
      user-select: none;
    }

    .page-btn:hover:not(:disabled) {
      border-color: var(--nintendo-red);
      color: var(--text-main);
    }

    .page-btn.active {
      background: var(--nintendo-red);
      border-color: var(--nintendo-red);
      color: #fff;
      font-weight: 700;
    }

    .page-btn:disabled {
      opacity: 0.35;
      cursor: not-allowed;
    }

    /* 模态弹窗 Modal 通用 */
    .modal-backdrop {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(8px);
      z-index: 999;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }

    .modal-content {
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-lg);
      max-width: 800px;
      width: 100%;
      max-height: 90vh;
      overflow-y: auto;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.7);
      position: relative;
    }

    .modal-header {
      padding: 24px 24px 16px;
      border-bottom: 1px solid var(--border-color);
      position: relative;
    }

    .modal-close-btn {
      position: absolute;
      top: 20px;
      right: 20px;
      background: rgba(255, 255, 255, 0.05);
      border: none;
      color: var(--text-muted);
      width: 32px;
      height: 32px;
      border-radius: 50%;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.2rem;
      transition: var(--transition);
    }

    .modal-close-btn:hover {
      background: rgba(255, 255, 255, 0.15);
      color: #fff;
    }

    .modal-body {
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    .version-compare-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
    }

    .version-card {
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      padding: 16px;
    }

    .version-field-label {
      font-size: 0.75rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 2px;
    }

    .version-field-val {
      font-size: 0.95rem;
      color: var(--text-main);
      margin-bottom: 12px;
      word-break: break-word;
    }

    .wiki-link-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--border-color);
      color: var(--text-sub);
      padding: 8px 14px;
      border-radius: var(--radius-sm);
      text-decoration: none;
      font-size: 0.85rem;
      transition: var(--transition);
    }

    .wiki-link-btn:hover {
      background: rgba(255, 255, 255, 0.12);
      color: #fff;
    }

    /* 数据下载中心模态网格 */
    .download-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 18px;
    }

    .download-card {
      background: rgba(255, 255, 255, 0.025);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 20px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: var(--transition);
    }

    .download-card:hover {
      background: rgba(255, 255, 255, 0.06);
      border-color: rgba(255, 255, 255, 0.2);
      transform: translateY(-2px);
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
    }

    .download-card-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 14px;
    }

    .download-icon {
      width: 44px;
      height: 44px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .icon-excel {
      background: rgba(16, 185, 129, 0.15);
      color: #10b981;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }

    .icon-csv {
      background: rgba(59, 130, 246, 0.15);
      color: #3b82f6;
      border: 1px solid rgba(59, 130, 246, 0.3);
    }

    .icon-json {
      background: rgba(245, 158, 11, 0.15);
      color: #f59e0b;
      border: 1px solid rgba(245, 158, 11, 0.3);
    }

    .download-title {
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--text-main);
    }

    .download-badge {
      display: inline-block;
      font-size: 0.72rem;
      font-weight: 700;
      padding: 1px 6px;
      border-radius: 4px;
      margin-top: 2px;
    }

    .badge-excel { background: rgba(16, 185, 129, 0.2); color: #6ee7b7; }
    .badge-csv { background: rgba(59, 130, 246, 0.2); color: #93c5fd; }
    .badge-json { background: rgba(245, 158, 11, 0.2); color: #fcd34d; }

    .download-desc {
      font-size: 0.82rem;
      color: var(--text-sub);
      line-height: 1.6;
      margin-bottom: 20px;
      flex-grow: 1;
    }

    .download-btn {
      display: block;
      width: 100%;
      text-align: center;
      padding: 10px 14px;
      border-radius: var(--radius-sm);
      font-size: 0.9rem;
      font-weight: 600;
      text-decoration: none;
      transition: var(--transition);
      box-sizing: border-box;
    }

    .btn-excel {
      background: #10b981;
      color: #fff;
    }
    .btn-excel:hover {
      background: #059669;
      box-shadow: 0 4px 14px rgba(16, 185, 129, 0.4);
    }

    .btn-csv {
      background: #3b82f6;
      color: #fff;
    }
    .btn-csv:hover {
      background: #2563eb;
      box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4);
    }

    .btn-json {
      background: #f59e0b;
      color: #fff;
    }
    .btn-json:hover {
      background: #d97706;
      box-shadow: 0 4px 14px rgba(245, 158, 11, 0.4);
    }

    /* 空状态 */
    .empty-state {
      text-align: center;
      padding: 60px 20px;
      color: var(--text-muted);
    }

    .empty-state h3 {
      font-size: 1.2rem;
      color: var(--text-sub);
      margin-bottom: 8px;
    }
  </style>
</head>
<body>

  <!-- 顶部导航 -->
  <header>
    <div class="navbar">
      <a href="#" class="brand">
        <div class="brand-logo">FC</div>
        <div>
          <div class="brand-title">任天堂 NES / 红白机游戏库</div>
          <div class="brand-subtitle">结合 No-Intro DAT 克隆树与 rom-name-cn 跨区整合数据库</div>
        </div>
      </a>
      <div class="header-links">
        <button class="nav-btn btn-download-nav" id="openDownloadModalBtn" title="下载全量数据文件 (Excel/CSV/JSON)">
          <svg width="15" height="15" fill="currentColor" viewBox="0 0 16 16"><path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z"/><path d="M7.646 11.854a.5.5 0 0 0 .708 0l3-3a.5.5 0 0 0-.708-.708L8.5 10.293V1.5a.5.5 0 0 0-1 0v8.793L5.354 8.146a.5.5 0 1 0-.708.708l3 3z"/></svg>
          📦 数据导出下载
        </button>

        <div class="view-toggle">
          <button class="view-btn active" id="viewBtnTable" title="密集表格视图">
            <svg width="15" height="15" fill="currentColor" viewBox="0 0 16 16"><path d="M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V2zm15 2h-4v3h4V4zm0 4h-4v3h4V8zm0 4h-4v3h3a1 1 0 0 0 1-1v-2zm-5 3v-3H6v3h4zm-5 0v-3H1v2a1 1 0 0 0 1 1h3zm-4-4h4V8H1v3zm0-4h4V4H1v3zm5-3v3h4V4H6zm4 4H6v3h4V8z"/></svg>
            密集表格
          </button>
          <button class="view-btn" id="viewBtnGrid" title="卡片网格视图">
            <svg width="15" height="15" fill="currentColor" viewBox="0 0 16 16"><path d="M1 2.5A1.5 1.5 0 0 1 2.5 1h3A1.5 1.5 0 0 1 7 2.5v3A1.5 1.5 0 0 1 5.5 7h-3A1.5 1.5 0 0 1 1 5.5v-3zm8 0A1.5 1.5 0 0 1 10.5 1h3A1.5 1.5 0 0 1 15 2.5v3A1.5 1.5 0 0 1 13.5 7h-3A1.5 1.5 0 0 1 9 5.5v-3zm-8 8A1.5 1.5 0 0 1 2.5 9h3A1.5 1.5 0 0 1 7 10.5v3A1.5 1.5 0 0 1 5.5 15h-3A1.5 1.5 0 0 1 1 13.5v-3zm8 0A1.5 1.5 0 0 1 10.5 9h3a1.5 1.5 0 0 1 1.5 1.5v3a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 9 13.5v-3z"/></svg>
            海报卡片
          </button>
        </div>
      </div>
    </div>
  </header>

  <main>
    <!-- 统计看板 -->
    <section class="stats-bar" id="statsBar">
      <div class="stat-card" style="--accent: var(--nintendo-red);">
        <div class="stat-value" id="statTotalGames">--</div>
        <div class="stat-label">整合后独立游戏总数</div>
      </div>
      <div class="stat-card" style="--accent: var(--badge-cross);">
        <div class="stat-value" id="statCrossRegion">--</div>
        <div class="stat-label">美日同款跨区游戏 (已合并)</div>
      </div>
      <div class="stat-card" style="--accent: var(--badge-nes);">
        <div class="stat-value" id="statNesOnly">--</div>
        <div class="stat-label">NES 欧美独占游戏</div>
      </div>
      <div class="stat-card" style="--accent: var(--badge-fc);">
        <div class="stat-value" id="statJpOnly">--</div>
        <div class="stat-label">日本地区独占游戏 (FC/FDS)</div>
      </div>
      <div class="stat-card" style="--accent: var(--accent-cyan);">
        <div class="stat-value" id="statRawTotal">--</div>
        <div class="stat-label">维基百科原始记录总计</div>
      </div>
      <div class="stat-card" style="--accent: #fb7299;">
        <div class="stat-value" id="statVideoCount">--</div>
        <div class="stat-label">B站编年史解说视频</div>
      </div>
    </section>

    <!-- 筛选面板 -->
    <section class="filter-panel" id="filterPanel">
      <div class="search-row">
        <div class="search-wrapper">
          <span class="search-icon">
            <svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16"><path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z"/></svg>
          </span>
          <input type="text" id="searchInput" class="search-input" placeholder="输入中文译名、英文名、日文名、发行商检索..." autocomplete="off">
        </div>
        <div class="select-controls">
          <select id="publisherSelect" class="custom-select">
            <option value="">全部发行商</option>
          </select>
          <select id="sortSelect" class="custom-select">
            <option value="date_asc" selected>按发售日先后 (由早到晚)</option>
            <option value="date_desc">按发售日先后 (由晚到早)</option>
            <option value="name_asc">按英文名 (A → Z)</option>
            <option value="name_desc">按英文名 (Z → A)</option>
            <option value="zh_asc">按中文名</option>
          </select>
        </div>
      </div>

      <div class="filter-pills" id="filterPills">
        <button class="filter-pill active" data-filter="all">全部游戏</button>
        <button class="filter-pill pill-cross" data-filter="cross">美日同款跨区</button>
        <button class="filter-pill pill-video" data-filter="video" id="pillVideoBtn">📺 B站编年史解说</button>
        <button class="filter-pill pill-nes" data-filter="nes">NES (欧美版)</button>
        <button class="filter-pill pill-fc" data-filter="fc">FC (卡带)</button>
        <button class="filter-pill pill-fds" data-filter="fds">FDS (磁碟机)</button>
      </div>
    </section>

    <!-- 结果统计与切换栏 -->
    <div class="results-info-bar">
      <div>
        找到 <span id="filteredCount" class="result-count-highlight">0</span> 款游戏
        <span id="pageInfoSpan" style="margin-left: 8px;">(第 1 / 1 页)</span>
      </div>
      <div>
        每页显示：
        <select id="pageSizeSelect" class="custom-select" style="padding: 4px 8px;">
          <option value="36">36 款</option>
          <option value="60" selected>60 款</option>
          <option value="120">120 款</option>
          <option value="999999">全部</option>
        </select>
      </div>
    </div>

    <!-- 网格视图容器 -->
    <section class="games-grid" id="gamesGrid" style="display: none;"></section>

    <!-- 表格视图容器（默认密集表格） -->
    <section class="table-container" id="tableContainer" style="display: block;">
      <table>
        <thead>
          <tr>
            <th style="width: 120px;">平台</th>
            <th style="min-width: 140px;">中文译名</th>
            <th style="min-width: 220px;">英文名 / 日文名</th>
            <th style="min-width: 180px;">美版发售日 / 日版发售日</th>
            <th style="min-width: 130px;">主要发行商</th>
            <th style="width: 120px; min-width: 110px; text-align: center; white-space: nowrap;">跨区属性</th>
          </tr>
        </thead>
        <tbody id="gamesTableBody"></tbody>
      </table>
    </section>

    <!-- 空状态提示 -->
    <div class="empty-state" id="emptyState" style="display: none;">
      <h3>未找到匹配的游戏</h3>
      <p>请尝试减少筛选条件或输入不同的关键字检索。</p>
    </div>

    <!-- 分页控件 -->
    <div class="pagination-bar" id="paginationBar"></div>
  </main>

  <!-- 数据下载中心模态弹窗 -->
  <div class="modal-backdrop" id="downloadModalBackdrop">
    <div class="modal-content" style="max-width: 820px;">
      <div class="modal-header">
        <button class="modal-close-btn" id="downloadModalCloseBtn" aria-label="关闭">&times;</button>
        <div class="badges-row">
          <span class="badge badge-cross" style="font-size: 0.8rem;">离线资源下载</span>
          <span class="badge badge-nes" style="font-size: 0.8rem;">全格式就绪</span>
        </div>
        <h2 style="font-size: 1.4rem; margin-top: 6px; margin-bottom: 4px;">📦 整合数据资源导出与下载中心</h2>
        <div style="color: var(--text-sub); font-size: 0.875rem;">
          任天堂 NES 与红白机 (FC/FDS) 跨区整合全量数据，已生成 Excel、CSV 与 JSON 格式，均包含 B 站视频章节时间轴
        </div>
      </div>
      <div class="modal-body">
        <div class="download-grid">
          <!-- Excel 卡片 -->
          <div class="download-card">
            <div>
              <div class="download-card-header">
                <div class="download-icon icon-excel">
                  <svg width="24" height="24" fill="currentColor" viewBox="0 0 16 16"><path d="M5.884 6.68a.5.5 0 1 0-.768.64L7.349 10l-2.233 2.68a.5.5 0 0 0 .768.64L8 10.748l2.116 2.572a.5.5 0 0 0 .768-.64L8.651 10l2.233-2.68a.5.5 0 0 0-.768-.64L8 9.252 5.884 6.68z"/><path d="M14 14V4.5L9.5 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2zM9.5 3A1.5 1.5 0 0 0 11 4.5h2V14a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1h5.5v2z"/></svg>
                </div>
                <div>
                  <div class="download-title">Excel 格式工作簿</div>
                  <div class="download-badge badge-excel">.xlsx 格式</div>
                </div>
              </div>
              <div class="download-desc">
                • 包含「游戏清单」与「统计说明」双 Sheet<br>
                • 预设首行冻结、自动筛选与自适应列宽<br>
                • B 站解说视频附带起播秒数超链接，点击直达播放<br>
                • 跨区同款游戏绿色高亮标识
              </div>
            </div>
            <a href="fc_nes_games.xlsx" download="fc_nes_games.xlsx" class="download-btn btn-excel">
              📥 立即下载 Excel (.xlsx)
            </a>
          </div>

          <!-- CSV 卡片 -->
          <div class="download-card">
            <div>
              <div class="download-card-header">
                <div class="download-icon icon-csv">
                  <svg width="24" height="24" fill="currentColor" viewBox="0 0 16 16"><path d="M14 14V4.5L9.5 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2zM9.5 3A1.5 1.5 0 0 0 11 4.5h2V14a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1h5.5v2z"/><path d="M4.603 12.087a.81.81 0 0 1-.438-.42c-.087-.183-.13-.395-.13-.636 0-.253.043-.47.13-.651.087-.182.21-.324.369-.427.16-.103.349-.155.568-.155.185 0 .349.038.491.114.143.075.253.18.33.313.078.133.117.29.117.471h-.696a.44.44 0 0 0-.156-.324.516.516 0 0 0-.341-.114.475.475 0 0 0-.385.168.742.742 0 0 0-.142.49c0 .21.047.37.142.482.095.11.223.165.385.165.143 0 .256-.041.34-.123.084-.082.137-.197.158-.344h.696a.99.99 0 0 1-.123.498.866.866 0 0 1-.341.344c-.149.083-.332.124-.55.124-.22 0-.41-.053-.57-.16z"/></svg>
                </div>
                <div>
                  <div class="download-title">CSV 逗号表格</div>
                  <div class="download-badge badge-csv">.csv 格式</div>
                </div>
              </div>
              <div class="download-desc">
                • 标准 UTF-8 编码，带 BOM 保证 Excel 打开不乱码<br>
                • 包含中英日三语标题、发售日、平台与发行商<br>
                • 附带 B 站视频标题、时间戳与直达 URL<br>
                • 兼容导入 MySQL / PostgreSQL / Pandas / R
              </div>
            </div>
            <a href="fc_nes_games.csv" download="fc_nes_games.csv" class="download-btn btn-csv">
              📥 立即下载 CSV (.csv)
            </a>
          </div>

          <!-- JSON 卡片 -->
          <div class="download-card">
            <div>
              <div class="download-card-header">
                <div class="download-icon icon-json">
                  <svg width="24" height="24" fill="currentColor" viewBox="0 0 16 16"><path d="M14 14V4.5L9.5 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2zM9.5 3A1.5 1.5 0 0 0 11 4.5h2V14a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1h5.5v2z"/><path d="M5.5 8.5A1.5 1.5 0 0 1 7 7h1v1H7a.5.5 0 0 0-.5.5v1A1.5 1.5 0 0 1 5 11v1a1.5 1.5 0 0 1 1.5 1.5H8v1H6.5A2.5 2.5 0 0 1 4 12v-1a2.5 2.5 0 0 1 1.5-2.5zm5 0A1.5 1.5 0 0 0 9 7H8v1h1a.5.5 0 0 1 .5.5v1A1.5 1.5 0 0 0 11 11v1a1.5 1.5 0 0 0-1.5 1.5H8v1h1.5A2.5 2.5 0 0 0 12 12v-1a2.5 2.5 0 0 0-1.5-2.5z"/></svg>
                </div>
                <div>
                  <div class="download-title">JSON 结构化数据</div>
                  <div class="download-badge badge-json">.json 格式</div>
                </div>
              </div>
              <div class="download-desc">
                • 完整层级树形结构，保留 NES/FC/FDS 各版本详情<br>
                • 包含元数据统计 (statistics) 与完整版本字典<br>
                • B 站视频对象含 bvid, chapter, timestamp, seconds<br>
                • 适合前端直接消费或二次开发 REST/GraphQL API
              </div>
            </div>
            <a href="fc_nes_games.json" download="fc_nes_games.json" class="download-btn btn-json">
              📥 立即下载 JSON (.json)
            </a>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 游戏详情弹窗 -->
  <div class="modal-backdrop" id="gameModalBackdrop">
    <div class="modal-content" id="gameModalContent">
      <div class="modal-header">
        <button class="modal-close-btn" id="modalCloseBtn" aria-label="关闭">&times;</button>
        <div class="badges-row" id="modalBadges"></div>
        <h2 id="modalTitleZh" style="font-size: 1.4rem; margin-bottom: 4px;"></h2>
        <div id="modalTitleEn" style="color: var(--text-sub); font-size: 1rem;"></div>
        <div id="modalTitleJa" style="color: var(--text-muted); font-size: 0.875rem;"></div>
      </div>
      <div class="modal-body">
        <div style="background: rgba(255,255,255,0.03); padding: 12px 16px; border-radius: var(--radius-sm); font-size: 0.9rem;">
          <div style="color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase;">各地区发行日期总览</div>
          <div style="display: flex; gap: 24px; margin-top: 6px; flex-wrap: wrap;">
            <div>日本: <strong id="modalDateJp" style="color: var(--text-main);">--</strong></div>
            <div>北美: <strong id="modalDateNa" style="color: var(--text-main);">--</strong></div>
            <div>欧洲: <strong id="modalDatePal" style="color: var(--text-main);">--</strong></div>
          </div>
        </div>

        <div>
          <h4 style="font-size: 0.95rem; margin-bottom: 12px; color: var(--text-sub);">各版本详细数据对比</h4>
          <div class="version-compare-grid" id="modalVersionGrid"></div>
        </div>

        <div id="modalWikiSection" style="margin-top: 8px;"></div>
      </div>
    </div>
  </div>

  <!-- 内嵌完整数据，无需外部 js 依赖，零本地 CORS 问题 -->
  <script id="embeddedDataScript">
    /* FC_NES_DATA_INJECTION */
  </script>

  <script>
    // 全局数据状态
    let allGames = [];
    let filteredGames = [];
    let currentPage = 1;
    let pageSize = 60;
    let activeFilter = 'all';
    let currentView = 'table'; // 默认密集表格

    // 解析发售日数字，用于高精度时间线排序 (由早到晚)
    function parseGameDateNum(game) {
      const dates = [
        game.release_dates ? game.release_dates.japan : '',
        game.release_dates ? game.release_dates.north_america : '',
        game.release_dates ? game.release_dates.europe : ''
      ];
      let minVal = 99999999;
      for (const d of dates) {
        if (!d) continue;
        const mYear = d.match(/(\d{4})/);
        if (!mYear) continue;
        const year = parseInt(mYear[1], 10);
        const mMonth = d.match(/(\d{1,2})\s*月/);
        const month = mMonth ? parseInt(mMonth[1], 10) : 1;
        const mDay = d.match(/(\d{1,2})\s*日/);
        const day = mDay ? parseInt(mDay[1], 10) : 1;
        const val = year * 10000 + month * 100 + day;
        if (val < minVal) minVal = val;
      }
      return minVal;
    }

    // 初始化载入
    function init() {
      // 1. 优先使用内置全局数据 (完全自包含，无外部依赖)
      if (window.FC_NES_DATA && window.FC_NES_DATA.games) {
        renderWithData(window.FC_NES_DATA);
      } else {
        // 2. Fallback: 尝试使用 fetch 加载同目录下的 json
        fetch('fc_nes_games.json')
          .then(resp => resp.json())
          .then(data => renderWithData(data))
          .catch(err => {
            console.error('加载数据失败:', err);
            document.getElementById('emptyState').style.display = 'block';
            document.getElementById('emptyState').innerHTML = `
              <h3 style="color: var(--nintendo-red);">数据加载失败</h3>
              <p>未找到数据源，请确认数据文件完整。</p>
            `;
          });
      }
    }

    function renderWithData(dataset) {
      allGames = dataset.games || [];
      const stats = dataset.metadata.statistics;

      // 渲染统计看板
      document.getElementById('statTotalGames').textContent = Number(stats.total_unified_games || allGames.length).toLocaleString();
      document.getElementById('statCrossRegion').textContent = Number(stats.cross_region_games || 0).toLocaleString();
      document.getElementById('statNesOnly').textContent = Number(stats.nes_exclusive_games || 0).toLocaleString();
      document.getElementById('statJpOnly').textContent = Number(stats.japan_exclusive_games || 0).toLocaleString();
      document.getElementById('statRawTotal').textContent = Number(stats.raw_records ? stats.raw_records.total : 0).toLocaleString();

      const videoMatchedCount = stats.bilibili_videos_matched || allGames.filter(g => g.video).length;
      document.getElementById('statVideoCount').textContent = Number(videoMatchedCount).toLocaleString();

      // 更新跨区 Pill 与 B站解说 Pill 数量
      const crossPill = document.querySelector('[data-filter="cross"]');
      if (crossPill) {
        crossPill.textContent = `美日同款跨区 (${stats.cross_region_games})`;
      }
      const videoPill = document.querySelector('[data-filter="video"]');
      if (videoPill) {
        videoPill.textContent = `📺 B站编年史解说 (${videoMatchedCount})`;
      }

      // 初始化发行商下拉框
      populatePublishers();

      // 触发初始筛选与渲染
      applyFilters();
    }

    // 填充发行商选项
    function populatePublishers() {
      const pubSelect = document.getElementById('publisherSelect');
      const pubCounts = {};

      allGames.forEach(g => {
        (g.publishers || []).forEach(p => {
          if (p) pubCounts[p] = (pubCounts[p] || 0) + 1;
        });
      });

      // 按游戏数量排序
      const sortedPubs = Object.entries(pubCounts).sort((a, b) => b[1] - a[1]);
      sortedPubs.forEach(([name, count]) => {
        if (count >= 3) {
          const opt = document.createElement('option');
          opt.value = name;
          opt.textContent = `${name} (${count})`;
          pubSelect.appendChild(opt);
        }
      });
    }

    // 过滤与排序（默认按发售日由早到晚时间线）
    function applyFilters() {
      const searchKeyword = document.getElementById('searchInput').value.trim().toLowerCase();
      const selectedPub = document.getElementById('publisherSelect').value;
      const sortOrder = document.getElementById('sortSelect').value;

      filteredGames = allGames.filter(game => {
        // 平台标签过滤
        if (activeFilter === 'cross' && !game.is_cross_region) return false;
        if (activeFilter === 'video' && !game.video) return false;
        if (activeFilter === 'nes' && !game.platforms.includes('NES')) return false;
        if (activeFilter === 'fc' && !game.platforms.includes('FC')) return false;
        if (activeFilter === 'fds' && !game.platforms.includes('FDS')) return false;

        // 发行商过滤
        if (selectedPub && !(game.publishers || []).includes(selectedPub)) return false;

        // 搜索过滤
        if (searchKeyword) {
          const matchZh = (game.title_zh || '').toLowerCase().includes(searchKeyword);
          const matchEn = (game.title_en || '').toLowerCase().includes(searchKeyword);
          const matchJa = (game.title_ja || '').toLowerCase().includes(searchKeyword);
          const matchId = (game.id || '').toLowerCase().includes(searchKeyword);
          const matchPub = (game.publishers || []).some(p => p.toLowerCase().includes(searchKeyword));
          const matchVideo = game.video ? (game.video.chapter_name || '').toLowerCase().includes(searchKeyword) : false;
          if (!matchZh && !matchEn && !matchJa && !matchId && !matchPub && !matchVideo) return false;
        }

        return true;
      });

      // 排序（默认按发售日先后顺序由早到晚）
      filteredGames.sort((a, b) => {
        if (sortOrder === 'date_asc') {
          const v1 = parseGameDateNum(a);
          const v2 = parseGameDateNum(b);
          if (v1 !== v2) return v1 - v2;
          return (a.title_en || '').localeCompare(b.title_en || '');
        } else if (sortOrder === 'date_desc') {
          const v1 = parseGameDateNum(a);
          const v2 = parseGameDateNum(b);
          if (v1 !== v2) return v2 - v1;
          return (a.title_en || '').localeCompare(b.title_en || '');
        } else if (sortOrder === 'name_asc') {
          return (a.title_en || '').localeCompare(b.title_en || '');
        } else if (sortOrder === 'name_desc') {
          return (b.title_en || '').localeCompare(a.title_en || '');
        } else if (sortOrder === 'zh_asc') {
          return (a.title_zh || '').localeCompare(b.title_zh || '', 'zh-Hans-CN');
        }
        return 0;
      });

      currentPage = 1;
      renderCurrentPage();
    }

    // 渲染当前页
    function renderCurrentPage() {
      const total = filteredGames.length;
      document.getElementById('filteredCount').textContent = total.toLocaleString();

      if (total === 0) {
        document.getElementById('gamesGrid').style.display = 'none';
        document.getElementById('tableContainer').style.display = 'none';
        document.getElementById('emptyState').style.display = 'block';
        document.getElementById('paginationBar').innerHTML = '';
        document.getElementById('pageInfoSpan').textContent = '';
        return;
      }

      document.getElementById('emptyState').style.display = 'none';

      const totalPages = Math.ceil(total / pageSize);
      if (currentPage > totalPages) currentPage = totalPages;
      if (currentPage < 1) currentPage = 1;

      document.getElementById('pageInfoSpan').textContent = `(第 ${currentPage} / ${totalPages} 页)`;

      const start = (currentPage - 1) * pageSize;
      const end = start + pageSize;
      const pageData = filteredGames.slice(start, end);

      if (currentView === 'grid') {
        document.getElementById('gamesGrid').style.display = 'grid';
        document.getElementById('tableContainer').style.display = 'none';
        renderGridView(pageData);
      } else {
        document.getElementById('gamesGrid').style.display = 'none';
        document.getElementById('tableContainer').style.display = 'block';
        renderTableView(pageData);
      }

      renderPagination(totalPages);
    }

    // 渲染网格视图
    function renderGridView(games) {
      const grid = document.getElementById('gamesGrid');
      grid.innerHTML = '';

      games.forEach(game => {
        const card = document.createElement('div');
        card.className = 'game-card' + (game.is_cross_region ? ' is-cross' : '');
        card.onclick = () => openGameDetail(game);

        let badgesHtml = '';
        if (game.is_cross_region) {
          badgesHtml += `<span class="badge badge-cross">美日同款跨区</span>`;
        }
        (game.platforms || []).forEach(p => {
          if (p === 'NES') badgesHtml += `<span class="badge badge-nes">NES</span>`;
          if (p === 'FC') badgesHtml += `<span class="badge badge-fc">FC</span>`;
          if (p === 'FDS') badgesHtml += `<span class="badge badge-fds">FDS</span>`;
        });

        const titleZh = game.title_zh ? game.title_zh : `<span class="empty">未定中文译名</span>`;
        const titleEn = game.title_en || 'Unknown Title';
        const titleJa = game.title_ja ? `<div class="game-title-ja">${escapeHtml(game.title_ja)}</div>` : '';

        const dateStr = game.release_dates.japan || game.release_dates.north_america || '未知发售日';
        const publishersStr = (game.publishers || []).join(', ') || '未知发行商';

        card.innerHTML = `
          <div class="card-top">
            <div class="badges-row">${badgesHtml}</div>
            <div class="game-title-zh">${titleZh}</div>
            <div class="game-title-en">${escapeHtml(titleEn)}</div>
            ${titleJa}
          </div>
          <div class="card-meta">
            <div class="meta-row">
              <span class="meta-label">首发日期</span>
              <span>${escapeHtml(dateStr)}</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">主要发行商</span>
              <span class="publisher-tag" title="${escapeHtml(publishersStr)}">${escapeHtml(publishersStr)}</span>
            </div>
          </div>
        `;
        grid.appendChild(card);
      });
    }

    // 渲染密集表格视图
    function renderTableView(games) {
      const tbody = document.getElementById('gamesTableBody');
      tbody.innerHTML = '';

      games.forEach(game => {
        const tr = document.createElement('tr');
        tr.onclick = () => openGameDetail(game);

        const badges = (game.platforms || []).map(p => {
          if (p === 'NES') return '<span class="badge badge-nes">NES</span>';
          if (p === 'FC') return '<span class="badge badge-fc">FC</span>';
          if (p === 'FDS') return '<span class="badge badge-fds">FDS</span>';
          return '';
        }).join(' ');

        const crossBadge = game.is_cross_region 
          ? '<span class="badge badge-cross">美日跨区</span>' 
          : '<span style="color:var(--text-muted);font-size:0.8rem;">单区</span>';

        const enName = game.title_en || '-';
        const jaName = game.title_ja || '-';
        const naDate = (game.release_dates && game.release_dates.north_america) ? game.release_dates.north_america : '-';
        const jpDate = (game.release_dates && game.release_dates.japan) ? game.release_dates.japan : '-';
        const publishersStr = (game.publishers || []).join(', ') || '-';

        let videoBtn = '';
        if (game.video) {
          videoBtn = `
            <a href="${escapeHtml(game.video.url)}" target="_blank" rel="noopener" class="bili-btn bili-tag" onclick="event.stopPropagation();" title="${escapeHtml(game.video.video_title)} | 分段: ${escapeHtml(game.video.chapter_name)} (点击直达 ${game.video.timestamp} 播放)">
              <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><path d="M4.5 1a.5.5 0 0 1 .4.2L6.8 3h2.4l1.9-1.8a.5.5 0 1 1 .7.7L10.3 3.4c1.6.4 2.7 1.8 2.7 3.6v5a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3V7c0-1.8 1.1-3.2 2.7-3.6L4.1 1.9a.5.5 0 0 1 .4-.9zm-.5 6v5a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2zm2 1.5a1 1 0 1 1 2 0 1 1 0 0 1-2 0zm4 0a1 1 0 1 1 2 0 1 1 0 0 1-2 0z"/></svg>
              ${game.video.timestamp}
            </a>`;
        }

        tr.innerHTML = `
          <td>${badges}</td>
          <td>
            <div style="display:inline-flex;align-items:center;flex-wrap:wrap;gap:6px;">
              <strong style="color:var(--text-main);font-size:0.95rem;">${escapeHtml(game.title_zh || '-')}</strong>
              ${videoBtn}
            </div>
          </td>
          <td>
            <div class="split-cell-box">
              <div class="sub-cell sub-cell-top" title="英文名: ${escapeHtml(enName)}">
                <span class="sub-tag tag-en">EN</span>
                <span class="sub-val">${escapeHtml(enName)}</span>
              </div>
              <div class="sub-cell sub-cell-bottom" title="日文名: ${escapeHtml(jaName)}">
                <span class="sub-tag tag-ja">JA</span>
                <span class="sub-val sub-val-ja">${escapeHtml(jaName)}</span>
              </div>
            </div>
          </td>
          <td>
            <div class="split-cell-box">
              <div class="sub-cell sub-cell-top" title="美版发售日: ${escapeHtml(naDate)}">
                <span class="sub-tag tag-na">美版</span>
                <span class="sub-val">${escapeHtml(naDate)}</span>
              </div>
              <div class="sub-cell sub-cell-bottom" title="日版发售日: ${escapeHtml(jpDate)}">
                <span class="sub-tag tag-jp">日版</span>
                <span class="sub-val">${escapeHtml(jpDate)}</span>
              </div>
            </div>
          </td>
          <td>
            <span class="publisher-tag" title="${escapeHtml(publishersStr)}" style="display:inline-block;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
              ${escapeHtml(publishersStr)}
            </span>
          </td>
          <td style="text-align: center; white-space: nowrap;">${crossBadge}</td>
        `;

        tbody.appendChild(tr);
      });
    }

    // 渲染分页器
    function renderPagination(totalPages) {
      const bar = document.getElementById('paginationBar');
      bar.innerHTML = '';
      if (totalPages <= 1) return;

      const prevBtn = document.createElement('button');
      prevBtn.className = 'page-btn';
      prevBtn.innerHTML = '&laquo;';
      prevBtn.disabled = (currentPage === 1);
      prevBtn.onclick = () => { if (currentPage > 1) { currentPage--; renderCurrentPage(); window.scrollTo({top: 280, behavior: 'smooth'}); }; };
      bar.appendChild(prevBtn);

      const maxButtons = 7;
      let startPage = Math.max(1, currentPage - 3);
      let endPage = Math.min(totalPages, startPage + maxButtons - 1);
      if (endPage - startPage < maxButtons - 1) {
        startPage = Math.max(1, endPage - maxButtons + 1);
      }

      if (startPage > 1) {
        const btn1 = document.createElement('button');
        btn1.className = 'page-btn';
        btn1.textContent = '1';
        btn1.onclick = () => { currentPage = 1; renderCurrentPage(); window.scrollTo({top: 280, behavior: 'smooth'}); };
        bar.appendChild(btn1);
        if (startPage > 2) {
          const span = document.createElement('span');
          span.textContent = '...';
          span.style.color = 'var(--text-muted)';
          bar.appendChild(span);
        }
      }

      for (let p = startPage; p <= endPage; p++) {
        const btn = document.createElement('button');
        btn.className = 'page-btn' + (p === currentPage ? ' active' : '');
        btn.textContent = p;
        btn.onclick = () => { currentPage = p; renderCurrentPage(); window.scrollTo({top: 280, behavior: 'smooth'}); };
        bar.appendChild(btn);
      }

      if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
          const span = document.createElement('span');
          span.textContent = '...';
          span.style.color = 'var(--text-muted)';
          bar.appendChild(span);
        }
        const lastBtn = document.createElement('button');
        lastBtn.className = 'page-btn';
        lastBtn.textContent = totalPages;
        lastBtn.onclick = () => { currentPage = totalPages; renderCurrentPage(); window.scrollTo({top: 280, behavior: 'smooth'}); };
        bar.appendChild(lastBtn);
      }

      const nextBtn = document.createElement('button');
      nextBtn.className = 'page-btn';
      nextBtn.innerHTML = '&raquo;';
      nextBtn.disabled = (currentPage === totalPages);
      nextBtn.onclick = () => { if (currentPage < totalPages) { currentPage++; renderCurrentPage(); window.scrollTo({top: 280, behavior: 'smooth'}); }; };
      bar.appendChild(nextBtn);
    }

    // 模态弹窗 - 查看跨版本并排对比
    function openGameDetail(game) {
      document.getElementById('modalTitleZh').textContent = game.title_zh || '未定中文名';
      document.getElementById('modalTitleEn').textContent = game.title_en || '';
      document.getElementById('modalTitleJa').textContent = game.title_ja || '';

      document.getElementById('modalDateJp').textContent = game.release_dates.japan || '未在日本发售';
      document.getElementById('modalDateNa').textContent = game.release_dates.north_america || '未在北美发售';
      document.getElementById('modalDatePal').textContent = game.release_dates.europe || '未在欧洲发售';

      const badgesContainer = document.getElementById('modalBadges');
      badgesContainer.innerHTML = '';
      if (game.is_cross_region) {
        badgesContainer.innerHTML += `<span class="badge badge-cross" style="font-size:0.8rem;padding:4px 10px;">美日同款跨区整合</span>`;
      }
      (game.platforms || []).forEach(p => {
        if (p === 'NES') badgesContainer.innerHTML += `<span class="badge badge-nes">NES (欧美版)</span>`;
        if (p === 'FC') badgesContainer.innerHTML += `<span class="badge badge-fc">FC (日版卡带)</span>`;
        if (p === 'FDS') badgesContainer.innerHTML += `<span class="badge badge-fds">FDS (FC磁碟机)</span>`;
      });

      const grid = document.getElementById('modalVersionGrid');
      grid.innerHTML = '';

      const versions = game.versions || {};
      for (const [pKey, v] of Object.entries(versions)) {
        const vCard = document.createElement('div');
        vCard.className = 'version-card';

        let badgeClass = 'badge-fc';
        if (pKey === 'NES') badgeClass = 'badge-nes';
        if (pKey === 'FDS') badgeClass = 'badge-fds';

        vCard.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
            <span class="badge ${badgeClass}" style="font-size:0.75rem;">${escapeHtml(v.platform_name || pKey)}</span>
            <span style="font-size:0.8rem; color:var(--text-muted);">${escapeHtml(v.region || '')}</span>
          </div>
          <div class="version-field-label">版本标题 (原名)</div>
          <div class="version-field-val"><strong>${escapeHtml(v.title_zh || v.title_en || v.title_ja || '-')}</strong></div>

          <div class="version-field-label">英文名称</div>
          <div class="version-field-val">${escapeHtml(v.title_en || '-')}</div>

          ${v.title_ja ? `
            <div class="version-field-label">日文名称</div>
            <div class="version-field-val">${escapeHtml(v.title_ja)}</div>
          ` : ''}

          <div class="version-field-label">发行商</div>
          <div class="version-field-val" style="color:var(--accent-cyan)">${escapeHtml(v.publisher || '未知')}</div>

          <div class="version-field-label">发售日期</div>
          <div class="version-field-val">${escapeHtml(v.release_date || v.release_date_na || v.release_date_pal || '-')}</div>

          ${v.wiki_url ? `
            <a href="${escapeHtml(v.wiki_url)}" target="_blank" rel="noopener" class="wiki-link-btn">
              维基条目 (${escapeHtml(pKey)}) &nearr;
            </a>
          ` : ''}
        `;
        grid.appendChild(vCard);
      }

      const wikiSection = document.getElementById('modalWikiSection');
      let linksHtml = '';
      if (game.wiki_url) {
        linksHtml += `
          <a href="${escapeHtml(game.wiki_url)}" target="_blank" rel="noopener" class="wiki-link-btn" style="background:rgba(230,0,18,0.15);color:#ff4d5a;border:1px solid rgba(230,0,18,0.3);">
            访问主维基百科页面 &nearr;
          </a>
        `;
      }
      if (game.video) {
        linksHtml += `
          <div class="bili-card">
            <div>
              <div style="color: #fb7299; font-size: 0.8rem; font-weight: 700; text-transform: uppercase; display: flex; align-items: center; gap: 6px;">
                <svg width="15" height="15" viewBox="0 0 16 16" fill="currentColor"><path d="M4.5 1a.5.5 0 0 1 .4.2L6.8 3h2.4l1.9-1.8a.5.5 0 1 1 .7.7L10.3 3.4c1.6.4 2.7 1.8 2.7 3.6v5a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3V7c0-1.8 1.1-3.2 2.7-3.6L4.1 1.9a.5.5 0 0 1 .4-.9zm-.5 6v5a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2zm2 1.5a1 1 0 1 1 2 0 1 1 0 0 1-2 0zm4 0a1 1 0 1 1 2 0 1 1 0 0 1-2 0z"/></svg>
                B站红白机游戏编年史对应解说
              </div>
              <div style="font-size: 0.95rem; font-weight: 600; color: var(--text-main); margin-top: 4px;">
                ${escapeHtml(game.video.video_title)}
              </div>
              <div style="font-size: 0.82rem; color: var(--text-sub); margin-top: 2px;">
                分段章节: <strong style="color: #fb7299;">${escapeHtml(game.video.chapter_name)}</strong> (起播时间点: ${game.video.timestamp})
              </div>
            </div>
            <a href="${escapeHtml(game.video.url)}" target="_blank" rel="noopener" class="bili-btn" style="padding: 8px 18px; font-size: 0.88rem; border-radius: 6px; box-shadow: 0 4px 12px rgba(251,114,153,0.3);">
              📺 直达起播点播放 &nearr;
            </a>
          </div>
        `;
      }
      wikiSection.innerHTML = linksHtml;

      document.getElementById('gameModalBackdrop').style.display = 'flex';
    }

    function closeModal() {
      document.getElementById('gameModalBackdrop').style.display = 'none';
      document.getElementById('downloadModalBackdrop').style.display = 'none';
    }

    function openDownloadModal() {
      document.getElementById('downloadModalBackdrop').style.display = 'flex';
    }

    function escapeHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    // 事件绑定与监听
    document.addEventListener('DOMContentLoaded', () => {
      init();

      // 搜索输入防抖
      let debounceTimer = null;
      document.getElementById('searchInput').addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(applyFilters, 150);
      });

      // 发行商下拉
      document.getElementById('publisherSelect').addEventListener('change', applyFilters);

      // 排序下拉
      document.getElementById('sortSelect').addEventListener('change', applyFilters);

      // 每页数量下拉
      document.getElementById('pageSizeSelect').addEventListener('change', (e) => {
        pageSize = parseInt(e.target.value, 10);
        currentPage = 1;
        renderCurrentPage();
      });

      // 分类过滤器 Pills
      document.querySelectorAll('.filter-pill').forEach(btn => {
        btn.addEventListener('click', (e) => {
          document.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
          e.currentTarget.classList.add('active');
          activeFilter = e.currentTarget.getAttribute('data-filter');
          applyFilters();
        });
      });

      // 视图切换按钮
      const btnGrid = document.getElementById('viewBtnGrid');
      const btnTable = document.getElementById('viewBtnTable');

      btnGrid.addEventListener('click', () => {
        currentView = 'grid';
        btnGrid.classList.add('active');
        btnTable.classList.remove('active');
        renderCurrentPage();
      });

      btnTable.addEventListener('click', () => {
        currentView = 'table';
        btnTable.classList.add('active');
        btnGrid.classList.remove('active');
        renderCurrentPage();
      });

      // 打开与关闭下载中心
      document.getElementById('openDownloadModalBtn').addEventListener('click', openDownloadModal);
      document.getElementById('downloadModalCloseBtn').addEventListener('click', closeModal);
      document.getElementById('downloadModalBackdrop').addEventListener('click', (e) => {
        if (e.target === document.getElementById('downloadModalBackdrop')) {
          closeModal();
        }
      });

      // 游戏详情弹窗关闭
      document.getElementById('modalCloseBtn').addEventListener('click', closeModal);
      document.getElementById('gameModalBackdrop').addEventListener('click', (e) => {
        if (e.target === document.getElementById('gameModalBackdrop')) {
          closeModal();
        }
      });

      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
      });
    });
  </script>
</body>
</html>
"""

def generate_fc_nes_html(
    output_file: str = "data/fc_nes_games.html",
    dataset: Optional[Dict[str, Any]] = None
) -> str:
    """生成并保存现代化、自包含的 fc_nes_games.html 前端可视化文件"""
    if dataset is None:
        json_path = "data/fc_nes_games.json"
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                dataset = json.load(f)
        else:
            raise FileNotFoundError(f"未找到数据文件: {json_path}，无法生成 HTML")

    json_str = json.dumps(dataset, ensure_ascii=False)
    # 将完整数据直接内嵌注入 HTML 脚本中
    html_content = HTML_TEMPLATE.replace(
        "/* FC_NES_DATA_INJECTION */",
        f"window.FC_NES_DATA = {json_str};"
    )

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    logger.info(f"已成功生成自包含交互式前端页面: {output_file} (文件大小: {os.path.getsize(output_file):,} 字节)")
    return output_file


# ==============================================================================
# 第四部分: 维基百科爬虫、No-Intro DAT 克隆树、rom-name-cn 融合核心与多格式导出
# ==============================================================================

# 维基百科根域名
BASE_WIKI_URL = "https://zh.wikipedia.org"

# FC / FDS / NES 维基百科页面来源
FC_NES_WIKI_URLS = {
    "NES": {
        "name": "Nintendo Entertainment System",
        "name_zh": "NES欧美版红白机",
        "url": "https://zh.wikipedia.org/zh-cn/Nintendo_Entertainment_System%E6%B8%B8%E6%88%8F%E5%88%97%E8%A1%A8",
    },
    "FDS": {
        "name": "Family Computer Disk System",
        "name_zh": "FC磁碟机",
        "url": "https://zh.wikipedia.org/zh-cn/FC%E7%A3%81%E7%A2%9F%E6%9C%BA%E6%B8%B8%E6%88%8F%E5%88%97%E8%A1%A8",
    },
    "FC": {
        "name": "Family Computer",
        "name_zh": "红白机 (FC卡带)",
        "url": "https://zh.wikipedia.org/zh-cn/%E7%BA%A2%E7%99%BD%E6%9C%BA%E6%B8%B8%E6%88%8F%E5%88%97%E8%A1%A8",
    },
}

# 默认网络请求头
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36 (EmuRomInfoBot/1.0)"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


@dataclass
class FcNesRawRecord:
    """单平台原始记录"""
    platform: str
    platform_name: str
    title_zh: str
    title_en: str
    title_ja: str
    release_date: str
    release_date_na: str
    release_date_pal: str
    publisher: str
    wiki_url: str
    publisher_wiki_url: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def create_resilient_session(retries: int = 3, backoff_factor: float = 1.0) -> requests.Session:
    """创建带自动重试的 requests.Session"""
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def clean_wiki_text(text: Optional[str]) -> str:
    """去除维基角标并规范空白"""
    if not text:
        return ""
    cleaned = re.sub(r'\[(?:注\s*)?[a-zA-Z0-9]+\]', '', text)
    cleaned = cleaned.replace('\xa0', ' ').replace('\u3000', ' ')
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def extract_wiki_link(element) -> str:
    """提取有效的维基百科超链接"""
    if not element:
        return ""
    a_tag = element.find("a")
    if not a_tag or not a_tag.get("href"):
        return ""
    href = a_tag["href"].strip()
    if "redlink=1" in href or "action=edit" in href:
        return ""
    if href.startswith("/"):
        return urljoin(BASE_WIKI_URL, href)
    elif href.startswith("http"):
        return href
    return ""


def fetch_html(
    url: str,
    session: requests.Session,
    cache_path: Optional[str] = None,
    timeout: int = 30,
    force_refresh: bool = False
) -> str:
    """获取页面 HTML，支持本地文件缓存"""
    if not force_refresh and cache_path and os.path.exists(cache_path):
        logger.info(f"从本地缓存读取: {cache_path}")
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read()

    logger.info(f"正在从网络请求: {url}")
    resp = session.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    html_content = resp.text

    if cache_path:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"页面已写入本地缓存: {cache_path}")

    return html_content


def parse_nes_page(html: str) -> List[FcNesRawRecord]:
    """解析 NES 列表"""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_=lambda c: c and "wikitable" in c)
    if not table:
        return []

    games = []
    rows = table.find_all("tr")[1:]
    for row in rows:
        cols = row.find_all(["th", "td"])
        if len(cols) != 5:
            continue
        col_en, col_zh, col_na, col_pal, col_pub = cols

        title_en = clean_wiki_text(col_en.get_text())
        title_zh = clean_wiki_text(col_zh.get_text())
        date_na = clean_wiki_text(col_na.get_text())
        date_pal = clean_wiki_text(col_pal.get_text())
        publisher = clean_wiki_text(col_pub.get_text())

        wiki_url = extract_wiki_link(col_zh) or extract_wiki_link(col_en)
        publisher_wiki_url = extract_wiki_link(col_pub)
        main_release_date = date_na if date_na else date_pal

        game = FcNesRawRecord(
            platform="NES",
            platform_name=FC_NES_WIKI_URLS["NES"]["name"],
            title_zh=title_zh,
            title_en=title_en,
            title_ja="",
            release_date=main_release_date,
            release_date_na=date_na,
            release_date_pal=date_pal,
            publisher=publisher,
            wiki_url=wiki_url,
            publisher_wiki_url=publisher_wiki_url,
        )
        games.append(game)
    logger.info(f"成功解析 NES 游戏: {len(games)} 款")
    return games


def parse_fc_or_fds_page(html: str, platform_code: str) -> List[FcNesRawRecord]:
    """解析 FC 或 FDS 列表"""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_=lambda c: c and "wikitable" in c)
    if not table:
        return []

    games = []
    rows = table.find_all("tr")[1:]
    for row in rows:
        cols = row.find_all(["th", "td"])
        if len(cols) != 5:
            continue
        col_ja, col_zh, col_en, col_date, col_pub = cols

        title_ja = clean_wiki_text(col_ja.get_text())
        title_zh = clean_wiki_text(col_zh.get_text())
        title_en = clean_wiki_text(col_en.get_text())
        release_date = clean_wiki_text(col_date.get_text())
        publisher = clean_wiki_text(col_pub.get_text())

        wiki_url = (
            extract_wiki_link(col_zh)
            or extract_wiki_link(col_ja)
            or extract_wiki_link(col_en)
        )
        publisher_wiki_url = extract_wiki_link(col_pub)

        game = FcNesRawRecord(
            platform=platform_code,
            platform_name=FC_NES_WIKI_URLS[platform_code]["name"],
            title_zh=title_zh,
            title_en=title_en,
            title_ja=title_ja,
            release_date=release_date,
            release_date_na="",
            release_date_pal="",
            publisher=publisher,
            wiki_url=wiki_url,
            publisher_wiki_url=publisher_wiki_url,
        )
        games.append(game)
    logger.info(f"成功解析 {platform_code} 游戏: {len(games)} 款")
    return games


# =====================================================================
# DAT 克隆树与 rom-name-cn 对照库加载与对齐逻辑
# =====================================================================

def normalize_text(text: str) -> str:
    """标准化文本：忽略大小写、标点，并将常见字符展开（如 $->dollar, &->and）"""
    if not text:
        return ""
    s = text.lower()
    s = s.replace('$', 'dollar').replace('&', 'and')
    s = re.sub(r'[\s\-:：·,，.!\?\'\"_—–\(\)（）/／\\\[\]【】\+]+', '', s)
    return s


def normalize_wiki_title(url: str) -> str:
    """从维基百科条目链接中提取并规范化条目名"""
    if not url:
        return ""
    u = unquote(url).strip().split("#")[0].rstrip("/")
    if "/wiki/" in u and "redlink=1" not in u:
        title = u.split("/wiki/")[-1]
        title = re.sub(r'\s*\(_?.*?\)', '', title)
        return title.lower()
    return ""


def extract_seq_num(title: str) -> str:
    """提取代数序号（如 II, 2, III 等），防止不同代数误匹配"""
    match = re.search(r'\b(ii|iii|iv|v|vi|2|3|4|5|6)\b', title.lower())
    return match.group(1) if match else ""


class RomNameCnHelper:
    """rom-name-cn 与 DAT 克隆关系辅助分析器"""

    def __init__(self, workspace_dir: str = "."):
        self.workspace_dir = workspace_dir
        self.alias_map: Dict[str, str] = {}
        self.en_to_cn: Dict[str, str] = {}
        self.dat_clone_links: Dict[str, Set[str]] = {}

        self._load_alias()
        self._load_rom_name_cn()
        self._load_dat_clones()

    def _load_alias(self):
        """加载中文别名映射表 (name_alias(Chinese).json)"""
        alias_path = os.path.join(self.workspace_dir, "rom-name-cn", "name_alias(Chinese).json")
        if not os.path.exists(alias_path):
            return
        try:
            with open(alias_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for group_key, val in data.items():
                canonical = val.get("default", group_key)
                norm_canon = normalize_text(canonical)
                self.alias_map[normalize_text(group_key)] = norm_canon
                for a in val.get("alias", []):
                    self.alias_map[normalize_text(a)] = norm_canon
                for o in val.get("others", []):
                    self.alias_map[normalize_text(o)] = norm_canon
            logger.info(f"已成功加载 rom-name-cn 别名字典: {len(self.alias_map)} 条映射")
        except Exception as e:
            logger.warning(f"加载别名字典失败: {e}")

    def canonical_cn(self, name: str) -> str:
        """获取中文名的规范基准名"""
        norm = normalize_text(name)
        return self.alias_map.get(norm, norm)

    def _load_rom_name_cn(self):
        """加载 rom-name-cn 目录下的 NES 与 FDS 对照表"""
        csv_patterns = [
            os.path.join(self.workspace_dir, "rom-name-cn", "Nintendo - Nintendo Entertainment System.csv"),
            os.path.join(self.workspace_dir, "rom-name-cn", "Nintendo - Family Computer Disk System.csv"),
        ]
        count = 0
        for csv_path in csv_patterns:
            if not os.path.exists(csv_path):
                continue
            try:
                with open(csv_path, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    next(reader, None)  # 跳过表头
                    for row in reader:
                        if len(row) >= 2 and row[0].strip() and row[1].strip():
                            en_full = row[0].strip()
                            cn = row[1].strip()
                            # 提取括号外的基准英文名
                            en_base = re.sub(r'\s*\(.*?\)', '', en_full).strip()
                            self.en_to_cn[normalize_text(en_full)] = cn
                            self.en_to_cn[normalize_text(en_base)] = cn
                            count += 1
            except Exception as e:
                logger.warning(f"读取 CSV 对照表 {csv_path} 失败: {e}")
        logger.info(f"已成功加载 rom-name-cn 中英文对照: {count} 条条目")

    def _load_dat_clones(self):
        """扫描并解析工作区中的 No-Intro DAT 文件并构建克隆组"""
        dat_files = glob.glob(os.path.join(self.workspace_dir, "*Nintendo*.dat"))
        total_links = 0
        for dat_path in dat_files:
            try:
                tree = ET.parse(dat_path)
                root = tree.getroot()
                groups: Dict[str, List[str]] = {}

                for game in root.findall("game"):
                    gid = game.get("id")
                    name = game.get("name")
                    # 排除非官方、自制及盗版换皮克隆条目，防止跨游戏错误关联
                    if any(bad in name for bad in ["(Pirate)", "(Unl)", "(Bootleg)", "(Homebrew)", "(Aftermarket)"]):
                        continue
                    cid = game.get("cloneofid")
                    pid = cid if cid else gid
                    base_name = re.sub(r'\s*\(.*?\)', '', name).strip()
                    groups.setdefault(pid, []).append(base_name)

                for pid, names in groups.items():
                    norm_names = set(normalize_text(n) for n in names if n)
                    for n1 in norm_names:
                        for n2 in norm_names:
                            if n1 != n2:
                                self.dat_clone_links.setdefault(n1, set()).add(n2)
                                total_links += 1
            except Exception as e:
                logger.warning(f"解析 DAT 文件 {dat_path} 失败: {e}")
        logger.info(f"已从 DAT 文件构建克隆关系索引: 覆盖 {len(self.dat_clone_links)} 个基准游戏名称")

    def lookup_cn_by_en(self, en_title: str) -> Optional[str]:
        """根据英文名从 rom-name-cn 查找中文译名"""
        norm = normalize_text(en_title)
        return self.en_to_cn.get(norm)

    def are_clones_in_dat(self, en_title1: str, en_title2: str) -> bool:
        """检查两个英文名在 No-Intro DAT 中是否属于同一个克隆组"""
        n1 = normalize_text(en_title1)
        n2 = normalize_text(en_title2)
        if not n1 or not n2:
            return False
        return (n2 in self.dat_clone_links.get(n1, set())) or (n1 in self.dat_clone_links.get(n2, set()))


def is_same_fc_nes_game(
    g1: Dict[str, Any],
    g2: Dict[str, Any],
    helper: RomNameCnHelper
) -> Tuple[bool, str]:
    """
    判断两个来自不同平台/区域的游戏是否属于同一款游戏
    使用 No-Intro DAT 克隆树与 rom-name-cn 对照库进行判定
    """
    # 规则 0: 同一平台内部绝不进行合并（单品各自独立）
    if g1["platform"] == g2["platform"]:
        return False, "同平台"

    # 规则 1: 合卡（如 "Super Mario Bros./Duck Hunt"）与单独游戏不合并
    if ("/" in g1["title_en"] and "/" not in g2["title_en"]) or ("/" in g2["title_en"] and "/" not in g1["title_en"]):
        return False, "合卡"

    seq1 = extract_seq_num(g1["title_en"]) or extract_seq_num(g1.get("title_zh", ""))
    seq2 = extract_seq_num(g2["title_en"]) or extract_seq_num(g2.get("title_zh", ""))
    if seq1 and seq2 and seq1 != seq2:
        return False, "序号冲突"

    en1 = normalize_text(g1["title_en"])
    en2 = normalize_text(g2["title_en"])

    # 【判定标准 1】: No-Intro DAT CloneOf 官方克隆关系（最权威判据）
    # 彻底解决美版与日版标题完全不同（如 Casino Kid 与 100 Man Dollar Kid）的问题
    if en1 and en2 and helper.are_clones_in_dat(g1["title_en"], g2["title_en"]):
        return True, f"DAT官方克隆关系匹配({g1['title_en']} <-> {g2['title_en']})"

    # 【判定标准 2】: rom-name-cn 权威中文名称与别名对齐
    # 结合维基中文名与 rom-name-cn 补全名进行别名归一化匹配
    cn1 = g1.get("title_zh") or helper.lookup_cn_by_en(g1["title_en"])
    cn2 = g2.get("title_zh") or helper.lookup_cn_by_en(g2["title_en"])
    if cn1 and cn2:
        canon_cn1 = helper.canonical_cn(cn1)
        canon_cn2 = helper.canonical_cn(cn2)
        if canon_cn1 and canon_cn2 and canon_cn1 == canon_cn2 and len(canon_cn1) >= 2:
            generic_names = {"棒球", "网球", "高尔夫", "足球", "麻将", "五子连珠", "排球"}
            if canon_cn1 in generic_names:
                p1 = normalize_text(g1.get("publisher", ""))
                p2 = normalize_text(g2.get("publisher", ""))
                if p1 and p2 and (p1 in p2 or p2 in p1):
                    return True, f"rom-name-cn通用中文+发行商匹配({cn1})"
            else:
                return True, f"rom-name-cn中文名称对齐({cn1})"

    # 【判定标准 3】: 维基百科条目一致匹配
    w1 = normalize_wiki_title(g1.get("wiki_url", ""))
    w2 = normalize_wiki_title(g2.get("wiki_url", ""))
    if w1 and w2 and w1 == w2:
        if not (seq1 and not seq2 or seq2 and not seq1):
            return True, f"Wiki条目相同({w1})"

    # 【判定标准 4】: 规范英文名称一致匹配
    if en1 and en2 and en1 == en2 and len(en1) >= 3:
        return True, f"英文名相同({g1['title_en']})"

    return False, ""


class UnionFind:
    """并查集实现，用于无回路聚类合并"""
    def __init__(self, elements: List[str]):
        self.parent = {e: e for e in elements}

    def find(self, i: str) -> str:
        if self.parent[i] != i:
            self.parent[i] = self.find(self.parent[i])
        return self.parent[i]

    def union(self, i: str, j: str) -> None:
        ri = self.find(i)
        rj = self.find(j)
        if ri != rj:
            self.parent[ri] = rj


def merge_fc_nes_records(
    raw_records: List[Dict[str, Any]],
    helper: RomNameCnHelper
) -> List[Dict[str, Any]]:
    """
    结合 DAT 克隆关系与 rom-name-cn，将美版 (NES) 与日版 (FC/FDS) 同款游戏聚类合并
    """
    indexed_records = []
    enriched_zh_count = 0

    for idx, r in enumerate(raw_records):
        item = dict(r)
        item["_uid"] = f"{r['platform']}_{idx}"

        # 若维基百科缺少中文名，尝试利用 rom-name-cn 进行补全
        if not item.get("title_zh") and item.get("title_en"):
            enriched = helper.lookup_cn_by_en(item["title_en"])
            if enriched:
                item["title_zh"] = enriched
                item["title_zh_source"] = "rom-name-cn"
                enriched_zh_count += 1
            else:
                item["title_zh_source"] = "none"
        else:
            item["title_zh_source"] = "wikipedia" if item.get("title_zh") else "none"

        indexed_records.append(item)

    logger.info(f"利用 rom-name-cn 成功补齐中文游戏名: {enriched_zh_count} 款")

    # 执行并查集两两比对合并
    uf = UnionFind([it["_uid"] for it in indexed_records])
    n = len(indexed_records)

    for i in range(n):
        r1 = indexed_records[i]
        for j in range(i + 1, n):
            r2 = indexed_records[j]
            if r1["platform"] != r2["platform"]:
                matched, reason = is_same_fc_nes_game(r1, r2, helper)
                if matched:
                    root1 = uf.find(r1["_uid"])
                    root2 = uf.find(r2["_uid"])
                    if root1 != root2:
                        uf.union(r1["_uid"], r2["_uid"])

    # 聚类归组
    clusters: Dict[str, List[Dict[str, Any]]] = {}
    for item in indexed_records:
        root = uf.find(item["_uid"])
        clusters.setdefault(root, []).append(item)

    unified_games: List[Dict[str, Any]] = []

    for root, cluster_items in clusters.items():
        platforms = sorted(list(set(it["platform"] for it in cluster_items)))

        versions: Dict[str, Any] = {}
        for it in cluster_items:
            clean_it = {k: v for k, v in it.items() if not k.startswith("_")}
            clean_it["region"] = "NA/PAL" if clean_it["platform"] == "NES" else "JP"
            versions[it["platform"]] = clean_it

        nes_ver = versions.get("NES")
        fc_ver = versions.get("FC")
        fds_ver = versions.get("FDS")

        # 确定主英文名（优先美版 NES，其次日版）
        title_en = ""
        if nes_ver and nes_ver.get("title_en"):
            title_en = nes_ver["title_en"]
        elif fc_ver and fc_ver.get("title_en"):
            title_en = fc_ver["title_en"]
        elif fds_ver and fds_ver.get("title_en"):
            title_en = fds_ver["title_en"]

        # 确定主中文名（优先维基官方译名，其次 rom-name-cn 权威民间译名）
        title_zh = ""
        for v in [nes_ver, fc_ver, fds_ver]:
            if v and v.get("title_zh"):
                title_zh = v["title_zh"]
                break

        # 确定主日文名
        title_ja = ""
        if fc_ver and fc_ver.get("title_ja"):
            title_ja = fc_ver["title_ja"]
        elif fds_ver and fds_ver.get("title_ja"):
            title_ja = fds_ver["title_ja"]

        # 维基条目 URL
        wiki_url = ""
        for v in [nes_ver, fc_ver, fds_ver]:
            if v and v.get("wiki_url"):
                wiki_url = v["wiki_url"]
                break

        release_dates = {
            "japan": (fc_ver.get("release_date") if fc_ver else "") or (fds_ver.get("release_date") if fds_ver else ""),
            "north_america": nes_ver.get("release_date_na", "") if nes_ver else "",
            "europe": nes_ver.get("release_date_pal", "") if nes_ver else "",
        }

        publishers = []
        for v in [nes_ver, fc_ver, fds_ver]:
            if v and v.get("publisher") and v["publisher"] not in publishers:
                publishers.append(v["publisher"])

        slug_seed = title_en or title_zh or title_ja or root
        slug = re.sub(r'[^a-zA-Z0-9]+', '-', slug_seed).strip('-').lower()
        if not slug:
            slug = f"game-{root}"

        has_us = "NES" in platforms
        has_jp = "FC" in platforms or "FDS" in platforms
        is_cross_region = has_us and has_jp

        game_data = {
            "id": slug,
            "title_zh": title_zh,
            "title_en": title_en,
            "title_ja": title_ja,
            "is_cross_region": is_cross_region,
            "platforms": platforms,
            "publishers": publishers,
            "wiki_url": wiki_url,
            "release_dates": release_dates,
            "versions": versions,
        }
        unified_games.append(game_data)

    def parse_earliest_date_key(game: Dict[str, Any]) -> Tuple[int, str]:
        dates = [
            game["release_dates"].get("japan", ""),
            game["release_dates"].get("north_america", ""),
            game["release_dates"].get("europe", ""),
        ]
        parsed_dates = []
        for d in dates:
            if not d:
                continue
            m_year = re.search(r'(\d{4})', d)
            if not m_year:
                continue
            year = int(m_year.group(1))
            m_month = re.search(r'(\d{1,2})\s*月', d)
            month = int(m_month.group(1)) if m_month else 1
            m_day = re.search(r'(\d{1,2})\s*日', d)
            day = int(m_day.group(1)) if m_day else 1
            parsed_dates.append(year * 10000 + month * 100 + day)

        min_date = min(parsed_dates) if parsed_dates else 99999999
        sec_key = (game.get("title_en") or game.get("title_zh") or "").lower()
        return (min_date, sec_key)

    # 默认按发售日的先后排序
    unified_games.sort(key=parse_earliest_date_key)

    seen_ids: Set[str] = set()
    for g in unified_games:
        orig_id = g["id"]
        unique_id = orig_id
        counter = 1
        while unique_id in seen_ids:
            unique_id = f"{orig_id}-{counter}"
            counter += 1
        g["id"] = unique_id
        seen_ids.add(unique_id)

    return unified_games


def collect_fc_nes_games(
    cache_dir: Optional[str] = "cache",
    timeout: int = 30,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """收集 FC/FDS/NES 平台游戏数据并结合 DAT 与 rom-name-cn 执行深度整合"""
    session = create_resilient_session()
    raw_by_platform: Dict[str, List[Dict[str, Any]]] = {}
    all_raw_list: List[Dict[str, Any]] = []

    # 1. 抓取与解析 NES (欧美版)
    nes_cache = os.path.join(cache_dir, "nes.html") if cache_dir else None
    nes_html = fetch_html(
        FC_NES_WIKI_URLS["NES"]["url"],
        session=session,
        cache_path=nes_cache,
        timeout=timeout,
        force_refresh=force_refresh
    )
    nes_records = parse_nes_page(nes_html)
    raw_by_platform["NES"] = [g.to_dict() for g in nes_records]
    all_raw_list.extend(raw_by_platform["NES"])

    # 2. 抓取与解析 FDS (FC磁碟机)
    fds_cache = os.path.join(cache_dir, "fds.html") if cache_dir else None
    fds_html = fetch_html(
        FC_NES_WIKI_URLS["FDS"]["url"],
        session=session,
        cache_path=fds_cache,
        timeout=timeout,
        force_refresh=force_refresh
    )
    fds_records = parse_fc_or_fds_page(fds_html, "FDS")
    raw_by_platform["FDS"] = [g.to_dict() for g in fds_records]
    all_raw_list.extend(raw_by_platform["FDS"])

    # 3. 抓取与解析 FC (红白机卡带)
    fc_cache = os.path.join(cache_dir, "fc.html") if cache_dir else None
    fc_html = fetch_html(
        FC_NES_WIKI_URLS["FC"]["url"],
        session=session,
        cache_path=fc_cache,
        timeout=timeout,
        force_refresh=force_refresh
    )
    fc_records = parse_fc_or_fds_page(fc_html, "FC")
    raw_by_platform["FC"] = [g.to_dict() for g in fc_records]
    all_raw_list.extend(raw_by_platform["FC"])

    # 4. 加载 DAT 克隆树与 rom-name-cn 辅助器
    logger.info("正在加载 No-Intro DAT 克隆组与 rom-name-cn 对照库...")
    helper = RomNameCnHelper(workspace_dir=".")

    # 5. 执行深度多维合并
    logger.info("正在基于 DAT 克隆树与 rom-name-cn 对齐合并美版与日版游戏...")
    unified_games = merge_fc_nes_records(all_raw_list, helper)

    # 6. 对齐挂载 Bilibili 红白机游戏编年史视频与时间轴章节
    logger.info("正在对齐挂载 Bilibili 红白机游戏编年史合集视频章节...")
    from bilibili_matcher import attach_bilibili_videos_to_games
    video_stats = attach_bilibili_videos_to_games(unified_games)

    cross_region_games = [g for g in unified_games if g["is_cross_region"]]
    multi_platform_games = [g for g in unified_games if len(g["platforms"]) > 1]
    nes_only_games = [g for g in unified_games if g["platforms"] == ["NES"]]
    japan_only_games = [g for g in unified_games if "NES" not in g["platforms"]]

    dataset = {
        "metadata": {
            "title": "任天堂 NES 与红白机 (FC/FDS) 跨区整合数据库 (结合 DAT、rom-name-cn 与 B站编年史视频)",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sources": {
                "wiki_urls": {k: v["url"] for k, v in FC_NES_WIKI_URLS.items()},
                "dat_files": [
                    "Nintendo - Nintendo Entertainment System (Headered) (20260806-082610).dat",
                    "Nintendo - Family Computer Disk System (FDS) (20260617-195332).dat"
                ],
                "submodules": ["rom-name-cn"],
                "bilibili_series_url": "https://space.bilibili.com/3546818172423070/lists/4877626"
            },
            "statistics": {
                "total_unified_games": len(unified_games),
                "cross_region_games": len(cross_region_games),
                "multi_platform_games": len(multi_platform_games),
                "nes_exclusive_games": len(nes_only_games),
                "japan_exclusive_games": len(japan_only_games),
                "bilibili_videos_matched": video_stats.get("matched_games_count", 0),
                "raw_records": {
                    "NES": len(nes_records),
                    "FDS": len(fds_records),
                    "FC": len(fc_records),
                    "total": len(all_raw_list),
                }
            }
        },
        "games": unified_games,
        "cross_region_games": cross_region_games,
        "raw_by_platform": raw_by_platform
    }

    return dataset


def save_to_json(data: Dict[str, Any], filepath: str) -> None:
    """保存为 JSON"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"已保存 JSON 文件: {filepath}")


def save_to_pickle(data: Dict[str, Any], filepath: str) -> None:
    """保存为 Pickle"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "wb") as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
    logger.info(f"已保存 Pickle 文件: {filepath}")


def save_to_python_module(data: Dict[str, Any], filepath: str) -> None:
    """保存为 Python 模块"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("# -*- coding: utf-8 -*-\n")
        f.write('"""\n自动生成的任天堂 NES 与红白机 (FC/FDS) 跨区整合数据模块 (基于 DAT 与 rom-name-cn)\n')
        f.write(f"生成时间: {data['metadata']['generated_at']}\n")
        f.write(f"独立游戏总数: {data['metadata']['statistics']['total_unified_games']}\n")
        f.write(f"美日同款游戏数: {data['metadata']['statistics']['cross_region_games']}\n")
        f.write('"""\n\n')
        f.write(f"FC_NES_METADATA = {repr(data['metadata'])}\n\n")
        f.write(f"FC_NES_GAMES = {repr(data['games'])}\n\n")
        f.write(f"FC_NES_CROSS_REGION_GAMES = {repr(data['cross_region_games'])}\n\n")
        f.write(f"FC_NES_RAW_BY_PLATFORM = {repr(data['raw_by_platform'])}\n")
    logger.info(f"已保存 Python 模块文件: {filepath}")


def save_to_js(data: Dict[str, Any], filepath: str) -> None:
    """保存为 JS 变量文件，方便前端本地预览无需本地 Web 服务器"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("// 自动生成的 FC/NES 游戏数据文件\n")
        f.write("window.FC_NES_DATA = ")
        json.dump(data, f, ensure_ascii=False)
        f.write(";\n")
    logger.info(f"已保存 JS 数据文件: {filepath}")


def save_to_csv(games: List[Dict[str, Any]], filepath: str) -> None:
    """导出 CSV 报表"""
    if not games:
        return
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    fieldnames = [
        "id", "title_zh", "title_en", "title_ja", "is_cross_region",
        "platforms", "publishers", "japan_release", "north_america_release",
        "europe_release", "wiki_url", "bilibili_video_title", "bilibili_timestamp", "bilibili_url"
    ]
    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for g in games:
            v_info = g.get("video") or {}
            writer.writerow({
                "id": g["id"],
                "title_zh": g["title_zh"],
                "title_en": g["title_en"],
                "title_ja": g["title_ja"],
                "is_cross_region": "是" if g["is_cross_region"] else "否",
                "platforms": "/".join(g["platforms"]),
                "publishers": " / ".join(g["publishers"]),
                "japan_release": g["release_dates"]["japan"],
                "north_america_release": g["release_dates"]["north_america"],
                "europe_release": g["release_dates"]["europe"],
                "wiki_url": g["wiki_url"],
                "bilibili_video_title": v_info.get("video_title", ""),
                "bilibili_timestamp": v_info.get("timestamp", ""),
                "bilibili_url": v_info.get("url", ""),
            })
    logger.info(f"已保存 CSV 文件: {filepath}")


def save_to_excel(data: Dict[str, Any], filepath: str) -> None:
    """导出排版规范、带超链接且支持筛选的 Excel 工作簿文件"""
    if not openpyxl:
        logger.warning("未检测到 openpyxl 库，跳过 Excel 文件导出")
        return

    games = data.get("games", [])
    stats = data.get("metadata", {}).get("statistics", {})

    wb = openpyxl.Workbook()

    # Sheet 1: 游戏数据清单
    ws_games = wb.active
    ws_games.title = "FC & NES 游戏清单"

    headers = [
        "序号", "ID", "中文译名", "英文名称", "日文名称", "跨区属性",
        "覆盖平台", "主要发行商", "日本发售日", "北美发售日", "欧洲发售日",
        "维基百科链接", "B站解说视频", "视频分段章节", "起播时间点", "直达播放链接"
    ]
    ws_games.append(headers)

    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name="Microsoft YaHei", size=11, bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )
    cross_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    link_font = Font(name="Microsoft YaHei", size=10, color="0563C1", underline="single")
    default_font = Font(name="Microsoft YaHei", size=10)

    for col_idx in range(1, len(headers) + 1):
        cell = ws_games.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws_games.row_dimensions[1].height = 28

    for idx, g in enumerate(games, 1):
        v = g.get("video") or {}
        row_num = idx + 1
        row_values = [
            idx,
            g["id"],
            g["title_zh"] or "",
            g["title_en"] or "",
            g["title_ja"] or "",
            "美日跨区" if g["is_cross_region"] else "单区独占",
            "/".join(g["platforms"]),
            " / ".join(g["publishers"]),
            g["release_dates"]["japan"] or "",
            g["release_dates"]["north_america"] or "",
            g["release_dates"]["europe"] or "",
            g["wiki_url"] or "",
            v.get("video_title", ""),
            v.get("chapter_name", ""),
            v.get("timestamp", ""),
            v.get("url", "")
        ]
        ws_games.append(row_values)
        ws_games.row_dimensions[row_num].height = 20

        for col_idx in range(1, len(headers) + 1):
            cell = ws_games.cell(row=row_num, column=col_idx)
            cell.font = default_font
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center")

            if col_idx in (1, 6, 7, 9, 10, 11, 15):
                cell.alignment = Alignment(horizontal="center", vertical="center")

            if col_idx == 6 and g["is_cross_region"]:
                cell.fill = cross_fill

            if col_idx == 12 and g["wiki_url"]:
                cell.hyperlink = g["wiki_url"]
                cell.font = link_font
            elif col_idx == 16 and v.get("url"):
                cell.hyperlink = v["url"]
                cell.font = link_font

    ws_games.freeze_panes = "C2"
    ws_games.auto_filter.ref = ws_games.dimensions

    # 自适应列宽
    for col in ws_games.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val = str(cell.value or '')
            length = sum(2 if ord(c) > 127 else 1 for c in val)
            if length > max_len:
                max_len = length
        ws_games.column_dimensions[col_letter].width = min(max(max_len + 3, 10), 45)

    # Sheet 2: 统计汇总与元数据说明
    ws_meta = wb.create_sheet(title="统计汇总与说明")
    ws_meta.views.sheetView[0].showGridLines = True

    meta_headers = ["指标分类", "统计项目", "数值 / 内容", "说明"]
    ws_meta.append(meta_headers)
    for col_idx in range(1, 5):
        cell = ws_meta.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws_meta.row_dimensions[1].height = 28

    raw = stats.get("raw_records", {})
    meta_rows = [
        ("原始数据记录", "NES (欧美版)", raw.get("NES", 0), "维基百科 List of NES games 原始条目数"),
        ("原始数据记录", "FDS (FC磁碟机)", raw.get("FDS", 0), "维基百科 List of FDS games 原始条目数"),
        ("原始数据记录", "FC (红白机卡带)", raw.get("FC", 0), "维基百科 List of FC games 原始条目数"),
        ("原始数据记录", "原始记录总计", raw.get("total", 0), "三平台原始条目总和"),
        ("深度融合结果", "整合后独立游戏总数", stats.get("total_unified_games", 0), "经 DAT 克隆树与 rom-name-cn 去重聚类后的独立游戏总数"),
        ("深度融合结果", "美日同款跨区游戏", stats.get("cross_region_games", 0), "同时在北美和日本发售的同款游戏 (已合并版本详情)"),
        ("深度融合结果", "多平台版本游戏总计", stats.get("multi_platform_games", 0), "覆盖 2 个或 3 个发行平台的经典游戏"),
        ("深度融合结果", "NES 欧美独占游戏", stats.get("nes_exclusive_games", 0), "仅在欧美 NES 发售的游戏"),
        ("深度融合结果", "日本地区独占游戏", stats.get("japan_exclusive_games", 0), "仅在日本发售的红白机/磁碟机游戏"),
        ("深度融合结果", "B站编年史解说视频", stats.get("bilibili_videos_matched", 0), "成功对齐解说视频并附带起播时间戳的游戏数量"),
        ("元数据信息", "生成时间", data.get("metadata", {}).get("generated_at", ""), "本次数据全量导出生成时间戳"),
        ("元数据信息", "B站合集主页", data.get("metadata", {}).get("sources", {}).get("bilibili_series_url", ""), "红白机游戏编年史合集原视频链接")
    ]

    for row_idx, r in enumerate(meta_rows, 2):
        ws_meta.append(r)
        ws_meta.row_dimensions[row_idx].height = 22
        for c in range(1, 5):
            cell = ws_meta.cell(row=row_idx, column=c)
            cell.font = default_font
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center")
            if c in (1, 2, 3):
                cell.alignment = Alignment(horizontal="center", vertical="center")

    for col in ws_meta.columns:
        col_letter = get_column_letter(col[0].column)
        ws_meta.column_dimensions[col_letter].width = 28

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    wb.save(filepath)
    logger.info(f"已保存 Excel 文件: {filepath}")


def save_to_html(data: Dict[str, Any] = None, filepath: str = "data/fc_nes_games.html") -> None:
    """生成并保存现代化交互式前端 HTML 文件（自包含内嵌完整数据，无需外部 js）"""
    from generate_fc_nes_html import generate_fc_nes_html
    generate_fc_nes_html(output_file=filepath, dataset=data)
    logger.info(f"已保存 HTML 交互式前端页面: {filepath}")


# ==============================================================================
# 第五部分: 10 项深度无第三方框架标准库质量断言校验
# ==============================================================================

def run_verifications():
    print("开始验证深度融合后的 FC/NES 数据文件与数据结构...")
    
    data_dir = "data"
    json_file = os.path.join(data_dir, "fc_nes_games.json")
    excel_file = os.path.join(data_dir, "fc_nes_games.xlsx")
    pkl_file = os.path.join(data_dir, "fc_nes_games.pkl")
    py_file = os.path.join(data_dir, "fc_nes_games.py")
    csv_file = os.path.join(data_dir, "fc_nes_games.csv")
    html_file = os.path.join(data_dir, "fc_nes_games.html")
    
    # 1. 验证所有输出文件与前端可视化文件是否存在且非空
    for fpath in [json_file, excel_file, pkl_file, py_file, csv_file, html_file]:
        assert os.path.exists(fpath), f"文件不存在: {fpath}"
        size = os.path.getsize(fpath)
        assert size > 0, f"文件为空: {fpath}"
        print(f"  [OK] 文件存在且大小正常: {fpath} ({size:,} 字节)")
        
    # 2. 验证 JSON 结构与字段定义
    with open(json_file, "r", encoding="utf-8") as f:
        json_data = json.load(f)
        
    assert "metadata" in json_data, "JSON 缺少 metadata 字段"
    assert "games" in json_data, "JSON 缺少 games 字段"
    assert "cross_region_games" in json_data, "JSON 缺少 cross_region_games 字段"
    assert "raw_by_platform" in json_data, "JSON 缺少 raw_by_platform 字段"
    
    stats = json_data["metadata"]["statistics"]
    raw = stats["raw_records"]
    assert raw["NES"] == 709, f"NES 原始数量不符: {raw['NES']}"
    assert raw["FDS"] == 199, f"FDS 原始数量不符: {raw['FDS']}"
    assert raw["FC"] == 1053, f"FC 原始数量不符: {raw['FC']}"
    assert raw["total"] == 1961, f"原始总数不符: {raw['total']}"
    
    games = json_data["games"]
    assert len(games) == stats["total_unified_games"], "games 列表长度与统计不符"
    assert len(json_data["cross_region_games"]) == stats["cross_region_games"], "跨区游戏数量不符"
    assert stats["cross_region_games"] >= 300, "跨区游戏数量应通过DAT和rom-name-cn显著提升(>=300)"
    print(f"  [OK] 统计数据完全一致: 原始条目 {raw['total']} 条，整合后独立游戏 {len(games)} 款")
    print(f"  [OK] 美日同款跨区游戏数量 (融合DAT/rom-name-cn后): {len(json_data['cross_region_games'])} 款")
    
    # 3. 验证合并数据结构与字段完整性
    expected_keys = {
        "id", "title_zh", "title_en", "title_ja", "is_cross_region",
        "platforms", "publishers", "wiki_url", "release_dates", "versions", "video"
    }
    for idx, g in enumerate(games):
        keys = set(g.keys())
        assert keys == expected_keys, f"第 {idx} 项字段不一致: {keys ^ expected_keys}"
        assert len(g["platforms"]) >= 1, f"游戏平台列表为空: {g['id']}"
        assert len(g["versions"]) >= 1, f"游戏版本列表为空: {g['id']}"
        
        # 验证美日同款游戏的数据合并特性
        if g["is_cross_region"]:
            assert "NES" in g["platforms"], f"跨区游戏缺少NES平台: {g['id']}"
            assert ("FC" in g["platforms"] or "FDS" in g["platforms"]), f"跨区游戏缺少FC/FDS平台: {g['id']}"
            assert "NES" in g["versions"], f"跨区游戏 versions 缺少 NES: {g['id']}"
            assert ("FC" in g["versions"] or "FDS" in g["versions"]), f"跨区游戏 versions 缺少 FC/FDS: {g['id']}"
    print("  [OK] 所有合并游戏条目结构与字段规范校验通过")
    
    # 4. 验证通过 No-Intro DAT 克隆树识别的特殊异名同款游戏
    # Casino Kid (美版) 与 100万$キッド 幻の帝王編 (日版)
    casino = next((g for g in games if g["id"] == "casino-kid"), None)
    assert casino is not None, "未找到 Casino Kid"
    assert casino["is_cross_region"] is True, "Casino Kid 应该被识别为跨美日同款游戏"
    assert "NES" in casino["versions"] and "FC" in casino["versions"], "Casino Kid 应包含 NES 与 FC 版本"
    print("  [OK] DAT 克隆关系验证: 成功跨越英日不同标题合并《Casino Kid》(美版) 与《100万$キッド》(日版)")
    
    # 5. 验证 rom-name-cn 中文名补全
    fester = next((g for g in games if g["id"] == "fester-s-quest"), None)
    assert fester is not None, "未找到 Fester's Quest"
    assert fester["title_zh"] != "", "Fester's Quest 的中文名应通过 rom-name-cn 成功补全"
    print(f"  [OK] rom-name-cn 中文补全验证: Fester's Quest 成功补全为 '{fester['title_zh']}'")
    
    # 6. 验证 Pickle 格式反序列化
    with open(pkl_file, "rb") as f:
        pkl_data = pickle.load(f)
    assert len(pkl_data["games"]) == len(games), "Pickle 数据长度不符"
    print("  [OK] Pickle 文件可正常反序列化为完整 Python 数据结构")
    
    # 7. 验证 Python 模块文件可直接导入使用
    sys.path.insert(0, data_dir)
    import fc_nes_games
    assert hasattr(fc_nes_games, "FC_NES_GAMES"), "fc_nes_games 缺少 FC_NES_GAMES"
    assert hasattr(fc_nes_games, "FC_NES_CROSS_REGION_GAMES"), "fc_nes_games 缺少 FC_NES_CROSS_REGION_GAMES"
    assert hasattr(fc_nes_games, "FC_NES_METADATA"), "fc_nes_games 缺少 FC_NES_METADATA"
    assert len(fc_nes_games.FC_NES_GAMES) == len(games), "Python 模块 FC_NES_GAMES 长度不符"
    print("  [OK] Python 模块 fc_nes_games.py 可被直接 import 使用")
    
    # 8. 验证 data/fc_nes_games.html 默认配置（自包含内嵌数据、无需外部js、密集表格、发售日排序、下载中心）
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()
    assert "currentView = 'table'" in html_content, "HTML 默认视图应为 table (密集表格)"
    assert 'value="date_asc" selected' in html_content, "HTML 默认排序应为 date_asc (发售日由早到晚)"
    assert "split-cell-box" in html_content, "HTML 表格应包含上下两层子格子容器 (split-cell-box)"
    assert "tag-en" in html_content and "tag-ja" in html_content, "HTML 表格应包含 EN/JA 英文日文子标签"
    assert "tag-na" in html_content and "tag-jp" in html_content, "HTML 表格应包含 美版/日版 发售日子标签"
    
    # 验证数据自包含与脱离外部 js
    assert "window.FC_NES_DATA = " in html_content, "HTML 必须内嵌注入完整 FC_NES_DATA 数据"
    assert 'src="data/fc_nes_games.js"' not in html_content and 'src="fc_nes_games.js"' not in html_content, "HTML 必须完全移除对外部 fc_nes_games.js 的 script 依赖"
    
    # 验证下载中心与资源链接
    assert "downloadModalBackdrop" in html_content, "HTML 必须包含资源下载中心模态框"
    assert "fc_nes_games.xlsx" in html_content, "HTML 必须包含 Excel 文件下载链接"
    assert "fc_nes_games.csv" in html_content, "HTML 必须包含 CSV 文件下载链接"
    assert "fc_nes_games.json" in html_content, "HTML 必须包含 JSON 文件下载链接"
    print("  [OK] 前端页面 data/fc_nes_games.html 数据自包含内嵌、无外部js依赖、默认密集表格与下载中心校验通过")
    
    # 9. 验证 Bilibili 空间合集视频与章节时间轴精准匹配
    matched_videos = stats.get("bilibili_videos_matched", 0)
    assert matched_videos >= 800, f"B站解说匹配数量偏低: {matched_videos}"
    print(f"  [OK] B站编年史解说匹配数量: {matched_videos} 款 (覆盖率 {(matched_videos / len(games) * 100):.1f}%)")
    
    # 抽检首发与知名作品的视频直达信息
    sample_ids = ["donkey-kong-jr", "mario-bros", "popeye", "gomoku-narabe-renju"]
    for sid in sample_ids:
        game = next((g for g in games if g["id"] == sid), None)
        assert game is not None, f"未找到抽样游戏: {sid}"
        v = game.get("video")
        assert v is not None, f"游戏 {sid} 应匹配到 B 站解说视频"
        assert v["bvid"].startswith("BV"), f"BVID 格式异常: {v['bvid']}"
        assert v["url"].startswith("https://www.bilibili.com/video/BV"), f"视频链接异常: {v['url']}"
        assert v["seconds"] >= 0, f"时间戳秒数异常: {v['seconds']}"
        assert f"?t={v['seconds']}" in v["url"], "直达链接未附带秒数参数"
        print(f"  [OK] 经典游戏视频抽检: 《{game['title_zh']}》 -> [{v['timestamp']}] {v['chapter_name']} ({v['url']})")
        
    assert "bili-tag" in html_content, "HTML 应包含 B 站视频徽章样式 bili-tag"
    assert "bili-card" in html_content, "HTML 应包含详情弹窗中的 B 站解说卡片 bili-card"
    print("  [OK] 前端页面 B 站视频徽章、时间戳跳转按钮与弹窗卡片校验通过")
    
    # 10. 验证 data/fc_nes_games.xlsx 结构与样式完整性
    import openpyxl
    wb = openpyxl.load_workbook(excel_file, read_only=False)
    assert "FC & NES 游戏清单" in wb.sheetnames, "Excel 缺少 'FC & NES 游戏清单' 工作表"
    assert "统计汇总与说明" in wb.sheetnames, "Excel 缺少 '统计汇总与说明' 工作表"
    
    ws1 = wb["FC & NES 游戏清单"]
    assert ws1.max_row == len(games) + 1, f"Excel 游戏清单行数不符: {ws1.max_row} != {len(games) + 1}"
    assert ws1.max_column == 16, f"Excel 游戏清单列数不符: {ws1.max_column} != 16"
    assert ws1.cell(row=1, column=1).value == "序号", "Excel 首列标题不符"
    assert ws1.cell(row=1, column=16).value == "直达播放链接", "Excel 尾列标题不符"
    
    # 抽检首行数据与超链接
    cell_link = ws1.cell(row=2, column=16)
    if cell_link.value:
        assert cell_link.hyperlink is not None, "首行直达播放链接应配置有效超链接对象"
        
    ws2 = wb["统计汇总与说明"]
    assert ws2.max_row >= 12, f"Excel 统计汇总行数过少: {ws2.max_row}"
    print(f"  [OK] Excel 文件 data/fc_nes_games.xlsx 双工作表、{ws1.max_row} 行数据与超链接格式校验通过")
    
    print("\n所有 10 项深度验证均已顺利通过！Excel 导出、HTML 自包含内嵌与数据下载中心运行完美。")


# ==============================================================================
# 第六部分: 统一 CLI 命令行主入口
# ==============================================================================

def main():
    """主程序入口：支持抓取、整合、全格式导出、独立编译 HTML 及完整性断言校验"""
    import argparse

    parser = argparse.ArgumentParser(
        description="任天堂 NES 与红白机 (FC/FDS) 跨区整合数据采集与发布全能引擎 (All-in-One Engine)"
    )
    parser.add_argument(
        "--output-dir",
        default="data",
        help="数据与页面生成目录 (默认: data/)"
    )
    parser.add_argument(
        "--cache-dir",
        default="cache",
        help="网页与 API 缓存目录 (默认: cache/)"
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="强制刷新网络缓存并重新下载"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="网络请求超时时间 (秒，默认: 30)"
    )
    parser.add_argument(
        "--html-only",
        action="store_true",
        help="仅重新编译生成自包含前端 HTML 页面"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="执行 10 项深度标准库数据完整性断言校验"
    )
    parser.add_argument(
        "--fetch-bilibili-only",
        action="store_true",
        help="仅重新抓取 B 站《红白机游戏编年史系列》合集章节分段"
    )

    args = parser.parse_args()

    # 1. 完整性断言校验模式
    if args.verify:
        run_verifications()
        return

    # 2. 独立生成 HTML 模式
    html_path = os.path.join(args.output_dir, "fc_nes_games.html")
    if args.html_only:
        generate_fc_nes_html(output_file=html_path)
        print(f"\n[OK] 前端可视化页面已更新生成: {html_path}")
        return

    # 3. 独立抓取 B 站合集分段模式
    if args.fetch_bilibili_only:
        bili_cache = os.path.join(args.cache_dir, "bilibili")
        archives = collect_bilibili_season_videos(cache_dir=bili_cache)
        fetch_all_video_details(archives, cache_dir=bili_cache)
        print(f"\n[OK] B 站合集视频章节已全量抓取更新至: {bili_cache}")
        return

    # 4. 默认全流程整合与全格式发布模式
    print("=" * 65)
    print("开始收集与深度整合 NES / FC磁碟机 / 红白机 游戏数据...")
    print(" (融合 No-Intro DAT、rom-name-cn 与 B站编年史视频)")
    print("=" * 65)

    dataset = collect_fc_nes_games(
        cache_dir=args.cache_dir,
        timeout=args.timeout,
        force_refresh=args.refresh
    )

    stats = dataset["metadata"]["statistics"]
    raw = stats["raw_records"]
    print("\n" + "=" * 65)
    print("【FC/NES 数据收集与深度合并统计摘要】")
    print(f"  维基百科原始记录数:")
    print(f"    - NES 欧美版游戏:       {raw['NES']:>5} 条")
    print(f"    - FC磁碟机游戏:         {raw['FDS']:>5} 条")
    print(f"    - 红白机(FC卡带)游戏:   {raw['FC']:>5} 条")
    print(f"    - 原始条目总计:         {raw['total']:>5} 条")
    print("-" * 65)
    print(f"  融合 DAT 与 rom-name-cn 后的合并结果:")
    print(f"    - 跨美日双版本游戏:     {stats['cross_region_games']:>5} 款 (已合并放入同个结构)")
    print(f"    - 多平台版本游戏总计:   {stats['multi_platform_games']:>5} 款")
    print(f"    - NES 美欧独占游戏:     {stats['nes_exclusive_games']:>5} 款")
    print(f"    - 日本地区独占游戏:     {stats['japan_exclusive_games']:>5} 款")
    print(f"    - 整合后独立游戏总数:   {stats['total_unified_games']:>5} 款")
    print(f"    - B站编年史解说视频:    {stats.get('bilibili_videos_matched', 0):>5} 款 (已绑定起播时间戳)")
    print("=" * 65 + "\n")

    out_dir = args.output_dir
    json_path = os.path.join(out_dir, "fc_nes_games.json")
    pickle_path = os.path.join(out_dir, "fc_nes_games.pkl")
    py_module_path = os.path.join(out_dir, "fc_nes_games.py")
    csv_path = os.path.join(out_dir, "fc_nes_games.csv")
    excel_path = os.path.join(out_dir, "fc_nes_games.xlsx")

    save_to_json(dataset, json_path)
    save_to_pickle(dataset, pickle_path)
    save_to_python_module(dataset, py_module_path)
    save_to_csv(dataset["games"], csv_path)
    save_to_excel(dataset, excel_path)
    save_to_html(dataset, html_path)

    print("\n所有 FC/NES 整合数据与前端页面已成功保存！")
    print(f"1. JSON 数据结构:     {json_path}")
    print(f"2. Pickle 二进制对象: {pickle_path}")
    print(f"3. Python 代码模块:   {py_module_path} (可直接 import FC_NES_GAMES)")
    print(f"4. CSV 表格导出:      {csv_path} (含 B站视频时间轴)")
    print(f"5. Excel 格式文件:    {excel_path} (富样式、首行冻结、含超链接)")
    print(f"6. HTML 交互式前端:   {html_path} (自包含内嵌数据，含资源下载中心)")


if __name__ == "__main__":
    main()
