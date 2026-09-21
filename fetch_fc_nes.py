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
import unicodedata
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from collections import OrderedDict
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

try:
    import yaml
except ImportError:
    yaml = None

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


def collect_bilibili_season_videos(cache_dir: str = "cache/bilibili", refresh_season: bool = False) -> List[Dict[str, Any]]:
    """获取合集中的所有视频基本信息 (支持动态计算页数与增量刷新)"""
    os.makedirs(cache_dir, exist_ok=True)
    all_archives = []
    
    # 1. 首先拉取第 1 页以动态确定合集总视频数与总页数
    page_1_cache = os.path.join(cache_dir, "page_1.json")
    if os.path.exists(page_1_cache) and not refresh_season:
        with open(page_1_cache, "r", encoding="utf-8") as f:
            pdata = json.load(f)
    else:
        url = f'https://api.bilibili.com/x/polymer/web-space/seasons_archives_list?mid={MID}&season_id={SEASON_ID}&page_num=1&page_size=30'
        logger.info("正在拉取 B 站合集第 1 页视频列表...")
        pdata = fetch_json_with_retry(url)
        with open(page_1_cache, "w", encoding="utf-8") as f:
            json.dump(pdata, f, ensure_ascii=False, indent=2)
        time.sleep(0.3)
        
    archives = pdata.get('data', {}).get('archives', [])
    all_archives.extend(archives)

    total = pdata.get('data', {}).get('page', {}).get('total', len(archives))
    page_size = pdata.get('data', {}).get('page', {}).get('page_size', 30)
    total_pages = max(1, (total + page_size - 1) // page_size)

    # 2. 依次获取后续各页
    for pn in range(2, total_pages + 1):
        page_cache = os.path.join(cache_dir, f"page_{pn}.json")
        if os.path.exists(page_cache) and not refresh_season:
            with open(page_cache, "r", encoding="utf-8") as f:
                pdata = json.load(f)
        else:
            url = f'https://api.bilibili.com/x/polymer/web-space/seasons_archives_list?mid={MID}&season_id={SEASON_ID}&page_num={pn}&page_size=30'
            logger.info(f"正在拉取 B 站合集第 {pn}/{total_pages} 页视频列表...")
            pdata = fetch_json_with_retry(url)
            with open(page_cache, "w", encoding="utf-8") as f:
                json.dump(pdata, f, ensure_ascii=False, indent=2)
            time.sleep(0.3)
            
        archives = pdata.get('data', {}).get('archives', [])
        all_archives.extend(archives)

    logger.info(f"成功获取合集视频总数: {len(all_archives)} 个 (共 {total_pages} 页)")
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
                logger.info(f"检测到新视频，正在抓取详情与分段 [{idx+1}/{len(archives)}]: 《{title}》({bvid})")
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


def load_adjustments_config(yaml_path: str = "override.yaml") -> Dict[str, Any]:
    """加载用户自定义调整配置文件 (优先 override.yaml，兼容 adjustments.yaml 与 adjust.yaml)"""
    target_path = yaml_path
    if not os.path.exists(target_path):
        candidates = ["override.yaml", "adjustments.yaml", "adjust.yaml"]
        for c in candidates:
            if os.path.exists(c):
                target_path = c
                break
        else:
            return {}

    if yaml is None:
        logger.warning("未检测到 PyYAML 库，无法读取外部调整配置文件")
        return {}
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        config: Dict[str, Any] = {
            "title_zh": {},
            "video_mappings": {},
            "games": [],
            "merge_games": []
        }

        if not isinstance(data, dict):
            return config

        # 1. 提取 title_zh 调整规则
        raw_titles = (
            data.get("title_zh") or 
            data.get("rename_title_zh") or 
            data.get("titles") or 
            data.get("rename", {}).get("title_zh") or 
            {}
        )
        if isinstance(raw_titles, dict):
            for k, v in raw_titles.items():
                if v is not None:
                    config["title_zh"][str(k).strip()] = str(v).strip()

        # 2. 提取视频分段对齐调整规则
        raw_videos = (
            data.get("video_mappings") or 
            data.get("videos") or 
            data.get("video_mapping") or 
            data.get("chapters") or 
            data.get("chapter_to_game") or 
            {}
        )
        if isinstance(raw_videos, dict):
            for k, v in raw_videos.items():
                if v is not None:
                    config["video_mappings"][str(k).strip()] = str(v).strip()

        # 3. 提取通用字段覆盖规则 (games 列表)
        raw_games = data.get("games", [])
        if isinstance(raw_games, list):
            config["games"] = raw_games

        # 4. 提取跨版本/跨区游戏手动合并规则 (merge_games)
        raw_merges = (
            data.get("merge_games") or 
            data.get("merges") or 
            data.get("merge") or 
            data.get("game_merges") or 
            data.get("alias_games") or 
            {}
        )
        merge_pairs: List[Tuple[str, str]] = []
        if isinstance(raw_merges, dict):
            for k, v in raw_merges.items():
                if isinstance(v, list):
                    for item in v:
                        if item:
                            merge_pairs.append((str(k).strip(), str(item).strip()))
                elif v:
                    merge_pairs.append((str(k).strip(), str(v).strip()))
        elif isinstance(raw_merges, list):
            for item in raw_merges:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    merge_pairs.append((str(item[0]).strip(), str(item[1]).strip()))
                elif isinstance(item, dict):
                    target = item.get("target") or item.get("primary") or item.get("main")
                    sources = item.get("source") or item.get("merge") or item.get("sources") or item.get("aliases")
                    if target and sources:
                        if isinstance(sources, list):
                            for s in sources:
                                merge_pairs.append((str(target).strip(), str(s).strip()))
                        else:
                            merge_pairs.append((str(target).strip(), str(sources).strip()))
        config["merge_games"] = merge_pairs

        # 5. 兼容顶层扁平字典 (若用户没有写分类标签)
        known_sections = {
            "title_zh", "rename_title_zh", "titles", "rename", 
            "video_mappings", "videos", "video_mapping", "chapters", 
            "chapter_to_game", "games", "merge_games", "merges", "merge", 
            "game_merges", "alias_games"
        }
        top_level_pairs = {
            str(k).strip(): str(v).strip() 
            for k, v in data.items() 
            if k not in known_sections and isinstance(v, (str, int))
        }
        if top_level_pairs:
            for k, v in top_level_pairs.items():
                if k not in config["video_mappings"]:
                    config["video_mappings"][k] = v

        return config
    except Exception as e:
        logger.warning(f"读取外部 YAML 调整文件 {target_path} 失败: {e}")
        return {}


def load_external_video_mapping(yaml_path: str = "override.yaml") -> Dict[str, str]:
    """兼容旧接口：从调整配置文件中获取视频映射规则"""
    config = load_adjustments_config(yaml_path)
    return config.get("video_mappings", {})


def apply_game_adjustments(games: List[Dict[str, Any]], yaml_path: str = "override.yaml") -> int:
    """基于 override.yaml 修改游戏属性 (如将 title_zh 从培基语音修改为家用BASIC语言)"""
    config = load_adjustments_config(yaml_path)
    if not config:
        return 0

    modified_count = 0
    title_zh_rules = config.get("title_zh", {})
    game_overrides = config.get("games", [])

    if not title_zh_rules and not game_overrides:
        return 0

    for g in games:
        g_id = g.get("id", "")
        old_title_zh = g.get("title_zh", "")

        # 1. 检查 title_zh 调整 (支持按原中文名或游戏 ID 匹配)
        new_title_zh = title_zh_rules.get(old_title_zh) or title_zh_rules.get(g_id)
        if new_title_zh and new_title_zh != old_title_zh:
            logger.info(f"应用 adjustments 调整游戏中文译名: 《{old_title_zh}》 (ID: {g_id}) -> 《{new_title_zh}》")
            g["title_zh"] = new_title_zh
            modified_count += 1
            # 同步更新 versions 中对应中文名
            for v in g.get("versions", {}).values():
                if v.get("title_zh") == old_title_zh or not v.get("title_zh"):
                    v["title_zh"] = new_title_zh

        # 2. 检查高级属性覆盖规则
        for rule in game_overrides:
            if not isinstance(rule, dict):
                continue
            match_cond = rule.get("match", rule)
            match_id = match_cond.get("id")
            match_title = match_cond.get("title_zh")

            is_match = False
            if match_id and match_id == g_id:
                is_match = True
            elif match_title and (match_title == old_title_zh or match_title == g.get("title_zh")):
                is_match = True

            if is_match:
                set_fields = rule.get("set", rule)
                for f_name, f_val in set_fields.items():
                    if f_name not in ("match", "set") and f_name in g:
                        g[f_name] = f_val
                        modified_count += 1
                        logger.info(f"应用 adjustments 调整游戏属性 (ID: {g_id}): {f_name} = {f_val}")

    if modified_count > 0:
        logger.info(f"已成功应用 override.yaml 中的调整规则，共修改 {modified_count} 处游戏属性")

    return modified_count


class BilibiliMatcher:
    def __init__(
        self, 
        games: List[Dict[str, Any]], 
        alias_json_path: str = "rom-name-cn/name_alias(Chinese).json",
        yaml_mapping_path: str = "override.yaml"
    ):
        self.games = games
        self.game_by_id = {g["id"]: g for g in games}
        self.game_by_title_zh = {g["title_zh"]: g for g in games if g.get("title_zh")}
        self.lookup: Dict[str, List[Dict[str, Any]]] = {}
        self.external_map: Dict[str, List[Dict[str, Any]]] = {}
        self.external_normalized_map: Dict[str, List[Dict[str, Any]]] = {}

        # 1. 优先加载用户可编辑的外部 YAML 调整配置中的视频规则 (格式: 游戏中文名/ID: 视频章节名)
        ext_rules = load_external_video_mapping(yaml_mapping_path)
        for game_ident, chapter_val in ext_rules.items():
            # 优先识别目标游戏 (ID、中文名、英文名、日文名)
            target_games = []
            target_game = self.game_by_id.get(game_ident) or self.game_by_title_zh.get(game_ident)
            if not target_game:
                for g in self.games:
                    if game_ident in (g.get("title_en"), g.get("title_ja")):
                        target_game = g
                        break
            if target_game:
                target_games.append(target_game)

            # 容错反向兼容：如果 game_ident 未识别为游戏，而 chapter_val 识别为游戏 (支持单游戏或列表)
            if not target_games:
                chap_candidates = chapter_val if isinstance(chapter_val, list) else [chapter_val]
                for cv in chap_candidates:
                    if isinstance(cv, str):
                        tg = self.game_by_id.get(cv) or self.game_by_title_zh.get(cv)
                        if not tg:
                            for g in self.games:
                                if cv in (g.get("title_en"), g.get("title_ja")):
                                    tg = g
                                    break
                        if tg and tg not in target_games:
                            target_games.append(tg)
                if target_games:
                    chapter_val = game_ident

            if target_games:
                chapters = [chapter_val] if isinstance(chapter_val, str) else list(chapter_val)
                for ch in chapters:
                    ch_str = str(ch).strip()
                    if ch_str not in self.external_map:
                        self.external_map[ch_str] = []
                    for tg in target_games:
                        if tg not in self.external_map[ch_str]:
                            self.external_map[ch_str].append(tg)

                    norm_key = normalize_text(ch_str)
                    if norm_key:
                        if norm_key not in self.external_normalized_map:
                            self.external_normalized_map[norm_key] = []
                        for tg in target_games:
                            if tg not in self.external_normalized_map[norm_key]:
                                self.external_normalized_map[norm_key].append(tg)
            else:
                logger.warning(f"外部 YAML 视频映射中未找到目标游戏: '{game_ident}' -> '{chapter_val}'")

        if self.external_map:
            total_rules = sum(len(gl) for gl in self.external_map.values())
            logger.info(f"已加载外部视频对齐映射规则 ({yaml_mapping_path}): 成功加载 {len(self.external_map)} 个章节模式、对应 {total_rules} 条游戏对齐规则")

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

    def match_segment_all(self, segment: Dict[str, Any]) -> List[Dict[str, Any]]:
        """为单个视频分段匹配对应的全部游戏实体 (支持合辑分段一对多对齐多款游戏)"""
        raw_name = segment.get("chapter_name", "")
        video_year = segment.get("video_year")

        # 1. 拆解斜杠候选别名与副标题 (如 "大金刚2/小金刚", "女武神冒险-时之钥匙传说")
        candidates = [raw_name]
        for sep in ['/', '／', '、', ' - ', '-', '——', '：', ':', ' ']:
            if sep in raw_name:
                candidates.extend([p.strip() for p in raw_name.split(sep) if len(p.strip()) >= 2])

        # 2. 最高优先级：查找用户在 YAML 文件中配置的外部映射规则 (精确候选匹配)
        ext_hits: List[Dict[str, Any]] = []
        for cand in candidates:
            if cand in self.external_map:
                ext_hits.extend(self.external_map[cand])
            nc = normalize_text(cand)
            if nc and nc in self.external_normalized_map:
                ext_hits.extend(self.external_normalized_map[nc])

        if ext_hits:
            unique_ext = []
            seen_ids = set()
            for g in ext_hits:
                if g["id"] not in seen_ids:
                    seen_ids.add(g["id"])
                    unique_ext.append(g)
            return unique_ext

        # 3. 查显式人工内置映射表精确匹配
        for cand in candidates:
            if cand in MANUAL_ALIAS_MAP:
                gid = MANUAL_ALIAS_MAP[cand]
                if gid in self.game_by_id:
                    return [self.game_by_id[gid]]

        # 4. 游戏库自带属性精确匹配 (含后缀清理)
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

        # 5. 兜底模糊匹配：只有当前面所有精确匹配均未命中时，才进行包含/子串匹配
        if not matched_candidates:
            # 5.1 尝试外部 YAML 调整规则长词包含匹配
            for k in sorted(self.external_map.keys(), key=len, reverse=True):
                if len(k) >= 3 and k in raw_name:
                    matched_candidates.extend(self.external_map[k])
                    break

        if not matched_candidates:
            # 5.2 尝试内置别名长词包含
            for k in sorted(MANUAL_ALIAS_MAP.keys(), key=len, reverse=True):
                if len(k) >= 4 and k in raw_name:
                    gid = MANUAL_ALIAS_MAP[k]
                    if gid in self.game_by_id:
                        matched_candidates.append(self.game_by_id[gid])
                        break

        if not matched_candidates:
            # 5.3 尝试游戏库索引子串包含匹配 (长度 >= 4)
            for cand in candidates:
                nc = normalize_text(cand)
                if len(nc) >= 4:
                    for k, g_list in self.lookup.items():
                        if len(k) >= 4 and (nc in k or k in nc):
                            matched_candidates.extend(g_list)
                            break

        if not matched_candidates:
            return []

        # 去重
        unique_matched = list({g["id"]: g for g in matched_candidates}.values())
        if len(unique_matched) == 1:
            return unique_matched

        # 4. 多候选时利用发售年份定锚 (Temporal Disambiguation)
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
                return [best_game]

        return unique_matched

    def match_segment(self, segment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """为单个视频分段匹配对应的游戏实体 (单游戏兼容接口)"""
        hits = self.match_segment_all(segment)
        return hits[0] if hits else None


def attach_bilibili_videos_to_games(
    games: List[Dict[str, Any]], 
    segments: Optional[List[Dict[str, Any]]] = None,
    segments_path: str = "data/raw/bilibili_segments_raw.json",
    yaml_mapping_path: str = "override.yaml"
) -> Dict[str, Any]:
    """将 Bilibili 视频分段匹配并挂载到游戏列表中 (支持一个章节分段对齐多款游戏)"""
    if segments is None:
        # 若未直接传入分段列表，依次尝试 data/raw 与本地缓存
        if not os.path.exists(segments_path):
            alt_path = "cache/bilibili/bilibili_segments.json"
            if os.path.exists(alt_path):
                segments_path = alt_path
            else:
                logger.warning(f"未找到 B 站分段数据文件: {segments_path}，跳过视频信息挂载")
                for g in games:
                    g["video"] = None
                return {"matched_count": 0, "total_segments": 0}

        with open(segments_path, "r", encoding="utf-8") as f:
            b_data = json.load(f)
            segments = b_data.get("segments", b_data) if isinstance(b_data, dict) else b_data

    matcher = BilibiliMatcher(games, yaml_mapping_path=yaml_mapping_path)
    matched_count = 0
    matched_game_ids = set()

    for seg in segments:
        hit_games = matcher.match_segment_all(seg)
        for hit_game in hit_games:
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
<html lang="zh-CN" data-theme="light">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>任天堂 NES 与红白机 (FC/FDS) 游戏库 - 跨区整合数据库 [NEO-BRUTALIST PLAYFUL]</title>
  <meta name="description" content="任天堂 NES 与红白机 (FC/FDS) 跨区整合游戏信息库，深度融合 No-Intro DAT 克隆树与 rom-name-cn 权威对照库，美日同款游戏一站式检索。">
  <style>
    /* ==========================================================================
       NEO-BRUTALIST PLAYFUL (俏皮野兽派) 双主题自包含样式表 (明亮 / 暗黑一键瞬切)
       规范遵循：绝对直角、纯黑粗边框(4px)、微旋转(<=3度)、彩色硬边缘阴影、
       严禁任何 Emoji/渐变/模糊、Toy Spring 玩具弹性动画与 Joyful Press 压扁反馈
       ========================================================================== */

    :root {
      /* 明亮模式配色 */
      --bg-canvas: #ffffff;
      --bg-card: #ffffff;
      --bg-card-sub: #fafafa;
      --border-black: #000000;
      --text-black: #000000;
      --text-white: #ffffff;
      --text-sub: #2d3748;
      --grid-line: rgba(0, 0, 0, 0.05);

      /* 俏皮野兽派五大多彩核心色 */
      --color-red: #ff6b6b;
      --color-cyan: #4ecdc4;
      --color-yellow: #ffe66d;
      --color-mint: #95e1d3;
      --color-coral: #f38181;

      /* 彩色实体硬边缘阴影 (零模糊半径) */
      --shadow-sm: 4px 4px 0 0 #000000;
      --shadow-md: 6px 6px 0 0 #000000;
      --shadow-lg: 8px 8px 0 0 #000000;
      --shadow-xl: 12px 12px 0 0 #000000;
      --shadow-cyan: 6px 6px 0 0 var(--color-cyan);
      --shadow-red: 6px 6px 0 0 var(--color-red);
      --shadow-yellow: 6px 6px 0 0 var(--color-yellow);
      --shadow-coral: 8px 8px 0 0 var(--color-coral);

      /* 弹性过渡缓动 (Toy Spring) */
      --spring-ease: cubic-bezier(0.34, 1.56, 0.64, 1);
      --transition-spring: all 300ms var(--spring-ease);

      /* 字体栈 */
      --font-heading: "Arial Black", Impact, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
      --font-mono: "JetBrains Mono", "SF Mono", "Fira Code", Monaco, Consolas, monospace;
    }

    /* 暗黑模式覆盖变量 (Dark Neo-Brutalist Playful - 沉稳暗化色板) */
    [data-theme="dark"] {
      --bg-canvas: #0e0e12;
      --bg-card: #181820;
      --bg-card-sub: #131318;
      --border-black: #000000;
      --text-black: #f7fafc;
      --text-white: #ffffff;
      --text-sub: #94a3b8;
      --grid-line: rgba(255, 255, 255, 0.04);

      /* 核心有色区域暗化：低明度、低饱和、沉稳雅致复古色板，绝不晃眼 */
      --color-red: #822929;      /* 暗砖红 */
      --color-cyan: #1a5654;     /* 墨青 / 湖青 */
      --color-yellow: #614b14;   /* 沉稳暗金 / 古铜金 */
      --color-mint: #1c4d3f;     /* 深墨薄荷绿 */
      --color-coral: #732c2c;    /* 暗深珊瑚红 */

      --shadow-sm: 4px 4px 0 0 #000000;
      --shadow-md: 6px 6px 0 0 #000000;
      --shadow-lg: 8px 8px 0 0 #000000;
      --shadow-xl: 12px 12px 0 0 #000000;
      --shadow-cyan: 6px 6px 0 0 var(--color-cyan);
      --shadow-red: 6px 6px 0 0 var(--color-red);
      --shadow-yellow: 6px 6px 0 0 var(--color-yellow);
      --shadow-coral: 8px 8px 0 0 var(--color-coral);
    }

    /* 严禁任何圆角 */
    *, *::before, *::after {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      border-radius: 0 !important;
    }

    body {
      background-color: var(--bg-canvas);
      background-image: 
        linear-gradient(to right, var(--grid-line) 2px, transparent 2px),
        linear-gradient(to bottom, var(--grid-line) 2px, transparent 2px);
      background-size: 32px 32px;
      color: var(--text-black);
      font-family: var(--font-mono);
      min-height: 100vh;
      line-height: 1.45;
      -webkit-font-smoothing: antialiased;
      overflow-x: hidden;
      transition: background-color 150ms ease-out;
    }

    a {
      color: inherit;
      text-decoration: none;
    }

    /* 顶部俏皮微倾斜横幅装饰条 (无 Emoji，纯 SVG + 几何装饰) */
    .playful-ticker {
      background: var(--color-yellow);
      color: #000000;
      border-bottom: 4px solid var(--border-black);
      padding: 8px 16px;
      font-family: var(--font-heading);
      font-weight: 900;
      font-size: 0.82rem;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      display: flex;
      justify-content: space-between;
      overflow: hidden;
      white-space: nowrap;
    }

    [data-theme="dark"] .playful-ticker {
      background: #000000;
      color: var(--color-yellow);
    }

    .ticker-item {
      display: inline-flex;
      align-items: center;
      gap: 10px;
    }

    .geo-dot {
      display: inline-block;
      width: 8px;
      height: 8px;
      background: var(--color-red);
      border: 2px solid var(--border-black);
      transform: rotate(-2deg);
    }

    /* 顶部导航 Header */
    header {
      background: var(--bg-card);
      border-bottom: 4px solid var(--border-black);
      position: sticky;
      top: 0;
      z-index: 200;
      box-shadow: 0 4px 0 0 rgba(0,0,0,0.2);
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
      gap: 14px;
      text-decoration: none;
      color: var(--text-black);
    }

    .brand-logo {
      width: 46px;
      height: 46px;
      background: var(--color-red);
      color: #ffffff;
      border: 4px solid var(--border-black);
      box-shadow: var(--shadow-sm);
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: var(--font-heading);
      font-weight: 900;
      font-size: 1.4rem;
      line-height: 1;
      transform: rotate(-2.5deg);
      transition: var(--transition-spring);
    }

    .brand:hover .brand-logo {
      transform: rotate(2.5deg) scale(1.08);
      box-shadow: var(--shadow-cyan);
    }

    .brand-title {
      font-family: var(--font-heading);
      font-size: 1.38rem;
      font-weight: 900;
      letter-spacing: -0.5px;
      line-height: 1.15;
      text-transform: uppercase;
    }

    .brand-subtitle {
      font-size: 0.8rem;
      font-weight: 800;
      color: var(--text-sub);
      margin-top: 2px;
      letter-spacing: -0.2px;
    }

    .header-links {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }

    /* 俏皮野兽派通用按钮 */
    .playful-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      font-family: var(--font-heading);
      font-weight: 900;
      text-transform: uppercase;
      font-size: 0.86rem;
      padding: 9px 16px;
      border: 4px solid var(--border-black);
      background: var(--bg-card);
      color: var(--text-black);
      box-shadow: var(--shadow-md);
      cursor: pointer;
      user-select: none;
      transition: var(--transition-spring);
      transform: rotate(-1deg);
    }

    .playful-btn:hover {
      transform: translateY(-4px) scale(1.05) rotate(1.5deg);
      box-shadow: 8px 8px 0 0 var(--color-red);
      background-color: var(--color-yellow);
      color: #000000;
    }

    /* 核心交互物理：压扁反馈 (Joyful Press) */
    .playful-btn:active {
      transform: translate(4px, 4px) scale(0.95) rotate(0deg);
      box-shadow: 0 0 0 0 #000000;
    }

    /* 主题切换开关专属按钮 */
    .btn-theme-toggle {
      background: #1c1c24;
      color: #ffffff;
      transform: rotate(1.2deg);
    }
    .btn-theme-toggle:hover {
      background: var(--color-yellow);
      color: #000000;
      box-shadow: 8px 8px 0 0 var(--color-cyan);
    }

    .btn-download-nav {
      background: var(--color-cyan);
      color: #000000;
      transform: rotate(-1deg);
    }
    .btn-download-nav:hover {
      background: var(--color-yellow);
      transform: translateY(-4px) scale(1.05) rotate(1.5deg);
      box-shadow: 8px 8px 0 0 var(--color-cyan);
    }

    /* 视图切换按钮组 */
    .view-toggle {
      display: inline-flex;
      border: 4px solid var(--border-black);
      background: var(--bg-card);
      box-shadow: var(--shadow-sm);
      transform: rotate(0.8deg);
      transition: var(--transition-spring);
    }

    .view-btn {
      padding: 7px 14px;
      font-family: var(--font-heading);
      font-weight: 900;
      font-size: 0.82rem;
      background: transparent;
      border: none;
      color: var(--text-black);
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: background-color 0ms;
    }

    .view-btn:first-child {
      border-right: 4px solid var(--border-black);
    }

    .view-btn:hover {
      background: var(--color-yellow);
      color: #000000;
    }

    .view-btn.active {
      background: var(--border-black);
      color: var(--color-yellow);
    }

    /* 主布局 */
    main {
      max-width: 1440px;
      margin: 0 auto;
      padding: 24px 24px 80px 24px;
    }

    /* 统计看板 Stats Bar (微倾斜与多彩卡片) */
    .stats-bar {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(195px, 1fr));
      gap: 18px;
      margin-bottom: 28px;
    }

    .stat-card {
      background: var(--bg-card);
      border: 4px solid var(--border-black);
      box-shadow: var(--shadow-md);
      padding: 16px 16px;
      position: relative;
      cursor: default;
      transition: var(--transition-spring);
    }

    .stat-card:nth-child(odd) {
      transform: rotate(-1deg);
    }
    .stat-card:nth-child(even) {
      transform: rotate(1deg);
    }

    .stat-card:hover {
      transform: translateY(-6px) scale(1.04) rotate(-1.8deg);
      box-shadow: 10px 10px 0 0 var(--hover-shadow-color, var(--color-cyan));
      background-color: var(--color-yellow) !important;
    }

    .stat-card:hover .stat-value,
    .stat-card:hover .stat-label {
      color: #000000 !important;
    }

    .stat-card::after {
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 8px;
      background: var(--accent-color, var(--border-black));
      border-bottom: 2px solid var(--border-black);
    }

    .stat-value {
      font-family: var(--font-heading);
      font-size: 2.35rem;
      font-weight: 900;
      line-height: 1;
      margin-top: 6px;
      margin-bottom: 6px;
      color: var(--text-black);
      letter-spacing: -1px;
    }

    .stat-label {
      font-size: 0.75rem;
      font-weight: 900;
      color: var(--text-sub);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      line-height: 1.25;
    }

    /* 筛选与搜索面板 */
    .filter-panel {
      background: var(--bg-card);
      border: 4px solid var(--border-black);
      box-shadow: var(--shadow-lg);
      padding: 22px;
      margin-bottom: 28px;
      position: relative;
    }

    .search-row {
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
      align-items: center;
      margin-bottom: 18px;
    }

    .search-wrapper {
      flex: 1;
      min-width: 280px;
      position: relative;
      display: flex;
      align-items: center;
    }

    .search-icon {
      position: absolute;
      left: 14px;
      pointer-events: none;
      color: var(--text-black);
      display: flex;
      align-items: center;
      font-weight: 900;
    }

    .search-input {
      width: 100%;
      height: 50px;
      padding: 0 16px 0 46px;
      background: var(--bg-card-sub);
      border: 4px solid var(--border-black);
      box-shadow: var(--shadow-sm);
      color: var(--text-black);
      font-family: var(--font-mono);
      font-size: 0.95rem;
      font-weight: 800;
      outline: none;
      transition: var(--transition-spring);
    }

    .search-input:focus {
      box-shadow: 6px 6px 0 0 var(--color-cyan);
      border-color: var(--border-black);
      transform: translateY(-2px);
    }

    .select-controls {
      display: flex;
      gap: 14px;
      flex-wrap: wrap;
    }

    .custom-select {
      height: 50px;
      padding: 0 34px 0 16px;
      background: var(--bg-card-sub);
      border: 4px solid var(--border-black);
      box-shadow: var(--shadow-sm);
      color: var(--text-black);
      font-family: var(--font-mono);
      font-size: 0.88rem;
      font-weight: 900;
      outline: none;
      cursor: pointer;
      appearance: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='%23000000' viewBox='0 0 16 16'%3E%3Cpath d='M7.247 11.14 2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z'/%3E%3C/svg%3E");
      background-repeat: no-repeat;
      background-position: right 12px center;
      background-size: 14px;
      transition: var(--transition-spring);
    }

    [data-theme="dark"] .custom-select {
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='%23ffffff' viewBox='0 0 16 16'%3E%3Cpath d='M7.247 11.14 2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z'/%3E%3C/svg%3E");
    }

    .custom-select option {
      background: var(--bg-card);
      color: var(--text-black);
    }

    .custom-select:focus {
      box-shadow: 6px 6px 0 0 var(--color-yellow);
      transform: translateY(-2px);
    }

    /* 过滤器药丸胶囊按钮组 (Filter Pills) */
    .filter-pills {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }

    .filter-pill {
      background: var(--bg-card-sub);
      border: 4px solid var(--border-black);
      box-shadow: var(--shadow-sm);
      color: var(--text-black);
      padding: 8px 16px;
      font-family: var(--font-heading);
      font-weight: 900;
      font-size: 0.82rem;
      text-transform: uppercase;
      cursor: pointer;
      user-select: none;
      transition: var(--transition-spring);
    }

    .filter-pill:nth-child(odd) {
      transform: rotate(-1deg);
    }
    .filter-pill:nth-child(even) {
      transform: rotate(1deg);
    }

    .filter-pill:hover {
      transform: translateY(-3px) scale(1.06) rotate(1.5deg);
      box-shadow: 6px 6px 0 0 var(--color-red);
      background: var(--color-yellow);
      color: #000000;
    }

    .filter-pill:active {
      transform: translate(3px, 3px) scale(0.95);
      box-shadow: 0 0 0 0 #000;
    }

    .filter-pill.active {
      background: var(--border-black);
      color: var(--text-white);
      box-shadow: 0 0 0 0 #000;
      transform: translate(2px, 2px) rotate(0deg);
    }

    .filter-pill.pill-cross.active {
      background: var(--color-mint);
      color: #000000;
    }

    .filter-pill.pill-video.active {
      background: var(--color-red);
      color: #ffffff;
    }

    .filter-pill.pill-nes.active {
      background: var(--color-cyan);
      color: #000000;
    }

    .filter-pill.pill-fc.active {
      background: var(--color-coral);
      color: #000000;
    }

    .filter-pill.pill-fds.active {
      background: var(--color-yellow);
      color: #000000;
    }

    /* 结果统计信息条 */
    .results-info-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      font-weight: 900;
      font-size: 0.95rem;
      flex-wrap: wrap;
      gap: 12px;
      padding: 4px 2px;
      color: var(--text-black);
    }

    .result-count-highlight {
      background: var(--color-yellow);
      color: #000000;
      padding: 3px 10px;
      border: 3px solid var(--border-black);
      box-shadow: 3px 3px 0 0 var(--color-cyan);
      font-weight: 900;
      font-size: 1.05rem;
      display: inline-block;
      transform: rotate(-1.5deg);
    }

    /* 徽章 Badge 规范系统 */
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 4px 8px;
      font-family: var(--font-mono);
      font-weight: 900;
      font-size: 0.72rem;
      text-transform: uppercase;
      border: 3px solid var(--border-black);
      line-height: 1.2;
      box-shadow: 2px 2px 0 0 #000;
      white-space: nowrap;
    }

    .badge-cross { background: var(--color-mint); color: #000; }
    .badge-nes   { background: var(--color-cyan); color: #000; }
    .badge-fc    { background: var(--color-coral); color: #000; }
    .badge-fds   { background: var(--color-yellow); color: #000; }

    /* 密集表格样式 Table View */
    .table-container {
      background: var(--bg-card);
      border: 4px solid var(--border-black);
      box-shadow: var(--shadow-lg);
      overflow-x: auto;
      margin-bottom: 28px;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.88rem;
      text-align: left;
    }

    thead {
      background: var(--border-black);
      color: #ffffff;
    }

    th {
      padding: 14px 16px;
      font-family: var(--font-heading);
      font-weight: 900;
      text-transform: uppercase;
      font-size: 0.86rem;
      letter-spacing: 0.5px;
      border-right: 3px solid #333;
      white-space: nowrap;
    }

    th:last-child {
      border-right: none;
    }

    tbody tr {
      border-bottom: 3px solid var(--border-black);
      cursor: pointer;
      transition: background-color 0ms;
      background: var(--bg-card);
      color: var(--text-black);
    }

    tbody tr:nth-child(even) {
      background: var(--bg-card-sub);
    }

    tbody tr:hover {
      background: var(--color-yellow) !important;
      color: #000000 !important;
    }

    tbody tr:hover strong,
    tbody tr:hover .sub-val,
    tbody tr:hover .publisher-tag {
      color: #000000 !important;
    }

    td {
      padding: 12px 16px;
      vertical-align: middle;
      border-right: 3px solid rgba(0, 0, 0, 0.25);
    }

    td:last-child {
      border-right: none;
    }

    .split-cell-box {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .sub-cell {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.82rem;
    }

    .sub-tag {
      padding: 2px 6px;
      font-weight: 900;
      font-size: 0.68rem;
      border: 2px solid var(--border-black);
      line-height: 1.1;
      white-space: nowrap;
    }

    .tag-en { background: #cbd5e0; color: #000; }
    .tag-ja { background: var(--color-red); color: #fff; }
    .tag-na { background: var(--color-cyan); color: #000; }
    .tag-jp { background: var(--color-coral); color: #000; }

    .sub-val {
      font-weight: 800;
      color: var(--text-black);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 280px;
    }

    .sub-val-ja {
      font-size: 0.8rem;
    }

    /* B站解说直达按钮 (雷文编年史，无 Emoji) */
    .bili-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 12px;
      background: var(--color-red);
      color: #ffffff !important;
      font-family: var(--font-heading);
      font-weight: 900;
      font-size: 0.76rem;
      border: 3px solid var(--border-black);
      box-shadow: 3px 3px 0 0 #000;
      cursor: pointer;
      user-select: none;
      transition: var(--transition-spring);
      transform: rotate(-1deg);
    }

    .bili-btn:hover {
      background: var(--color-cyan);
      color: #000000 !important;
      transform: translateY(-2px) scale(1.06) rotate(1.5deg);
      box-shadow: 5px 5px 0 0 var(--color-yellow);
    }

    .bili-btn:active {
      transform: translate(3px, 3px) scale(0.95);
      box-shadow: 0 0 0 0 #000;
    }

    /* 海报卡片网格视图 Grid View (微倾斜与彩色硬投影) */
    .games-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(315px, 1fr));
      gap: 24px;
      margin-bottom: 28px;
    }

    .game-card {
      background: var(--bg-card);
      border: 4px solid var(--border-black);
      box-shadow: var(--shadow-md);
      padding: 20px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      cursor: pointer;
      position: relative;
      transition: var(--transition-spring);
    }

    .game-card:nth-child(3n+1) {
      transform: rotate(-0.8deg);
    }
    .game-card:nth-child(3n+2) {
      transform: rotate(0.8deg);
    }
    .game-card:nth-child(3n) {
      transform: rotate(-0.4deg);
    }

    /* 卡片悬浮彩色硬投影跳跃 (Color Ping-Pong & Toy Spring) */
    .game-card:hover {
      transform: translateY(-6px) scale(1.03) rotate(1.2deg);
      box-shadow: 10px 10px 0 0 var(--color-cyan);
      background-color: var(--color-yellow) !important;
    }

    .game-card:hover .game-title-zh,
    .game-card:hover .game-title-en,
    .game-card:hover .game-title-ja,
    .game-card:hover .publisher-tag,
    .game-card:hover .meta-label,
    .game-card:hover .meta-row span {
      color: #000000 !important;
    }

    .game-card:active {
      transform: translate(4px, 4px) scale(0.97);
      box-shadow: 0 0 0 0 #000;
    }

    .game-card.is-cross {
      border-top-width: 8px;
    }

    .card-top {
      margin-bottom: 14px;
    }

    .badges-row {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      margin-bottom: 10px;
    }

    .game-title-zh {
      font-family: var(--font-heading);
      font-size: 1.28rem;
      font-weight: 900;
      line-height: 1.25;
      color: var(--text-black);
      margin-bottom: 4px;
      word-break: break-word;
    }

    .game-title-zh .empty {
      color: var(--text-sub);
      font-style: italic;
      font-size: 0.95rem;
    }

    .game-title-en {
      font-size: 0.88rem;
      font-weight: 800;
      color: var(--text-sub);
      margin-bottom: 2px;
      word-break: break-word;
    }

    .game-title-ja {
      font-size: 0.78rem;
      font-weight: 700;
      color: var(--text-sub);
      word-break: break-word;
    }

    .card-meta {
      border-top: 3px solid var(--border-black);
      padding-top: 12px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      font-size: 0.82rem;
    }

    .meta-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
    }

    .meta-label {
      font-weight: 900;
      text-transform: uppercase;
      color: var(--text-sub);
      font-size: 0.72rem;
      letter-spacing: 0.5px;
    }

    .publisher-tag {
      font-weight: 800;
      color: var(--text-black);
    }

    /* 分页条控件 Pagination */
    .pagination-bar {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      margin: 20px 0;
    }

    .pagination-bar-top {
      margin-top: 0;
      margin-bottom: 14px;
      justify-content: flex-end;
    }

    .page-btn {
      min-width: 40px;
      height: 40px;
      padding: 0 10px;
      background: var(--bg-card-sub);
      border: 3px solid var(--border-black);
      box-shadow: 3px 3px 0 0 #000;
      color: var(--text-black);
      font-family: var(--font-heading);
      font-weight: 900;
      font-size: 0.9rem;
      cursor: pointer;
      user-select: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      transition: var(--transition-spring);
    }

    .page-btn:hover:not(:disabled) {
      background: var(--color-yellow);
      color: #000000;
      transform: translateY(-3px) scale(1.08) rotate(-2deg);
      box-shadow: 5px 5px 0 0 var(--color-red);
    }

    .page-btn:active:not(:disabled) {
      transform: translate(3px, 3px) scale(0.95);
      box-shadow: 0 0 0 0 #000;
    }

    .page-btn.active {
      background: var(--border-black);
      color: var(--color-yellow);
      box-shadow: 0 0 0 0 #000;
      transform: translate(2px, 2px);
    }

    .page-btn:disabled {
      opacity: 0.3;
      cursor: not-allowed;
      box-shadow: none;
      border-color: #718096;
    }

    /* 空状态 */
    .empty-state {
      background: var(--bg-card);
      border: 4px solid var(--border-black);
      box-shadow: var(--shadow-lg);
      padding: 48px 24px;
      text-align: center;
      margin-bottom: 28px;
      color: var(--text-black);
    }

    .empty-state h3 {
      font-family: var(--font-heading);
      font-size: 1.6rem;
      font-weight: 900;
      margin-bottom: 8px;
    }

    /* 模态弹窗系统 Modal System */
    .modal-backdrop {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.8);
      z-index: 999;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 16px;
      overflow-y: auto;
    }

    .modal-content {
      background: var(--bg-card);
      border: 5px solid var(--border-black);
      box-shadow: var(--shadow-xl);
      max-width: 900px;
      width: 100%;
      max-height: 90vh;
      display: flex;
      flex-direction: column;
      position: relative;
      overflow: hidden;
      color: var(--text-black);
    }

    .modal-header {
      background: var(--bg-card-sub);
      border-bottom: 4px solid var(--border-black);
      padding: 20px 24px;
      position: relative;
    }

    .modal-close-btn {
      position: absolute;
      top: 16px;
      right: 16px;
      width: 38px;
      height: 38px;
      background: var(--bg-card);
      border: 4px solid var(--border-black);
      box-shadow: 3px 3px 0 0 #000;
      font-family: var(--font-heading);
      font-weight: 900;
      font-size: 1.4rem;
      line-height: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--text-black);
      cursor: pointer;
      transition: var(--transition-spring);
    }

    .modal-close-btn:hover {
      background: var(--color-red);
      color: #ffffff;
      transform: translateY(-2px) scale(1.1) rotate(2deg);
      box-shadow: 5px 5px 0 0 var(--color-cyan);
    }

    .modal-close-btn:active {
      transform: translate(3px, 3px) scale(0.95);
      box-shadow: 0 0 0 0 #000;
    }

    .modal-body {
      padding: 24px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    /* 下载中心卡片排版 */
    .download-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 18px;
    }

    .download-card {
      background: var(--bg-card-sub);
      border: 4px solid var(--border-black);
      box-shadow: var(--shadow-md);
      padding: 18px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: var(--transition-spring);
      color: var(--text-black);
    }

    .download-card:hover {
      transform: translateY(-4px) scale(1.02);
      box-shadow: 8px 8px 0 0 var(--color-yellow);
    }

    .download-card-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
    }

    .download-icon {
      width: 44px;
      height: 44px;
      border: 3px solid var(--border-black);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 3px 3px 0 0 #000;
    }

    .icon-excel { background: var(--color-mint); color: #000; }
    .icon-csv   { background: var(--color-yellow); color: #000; }
    .icon-json  { background: var(--color-cyan); color: #000; }

    .download-title {
      font-family: var(--font-heading);
      font-size: 1.05rem;
      font-weight: 900;
      line-height: 1.2;
      color: var(--text-black);
    }

    .download-badge {
      display: inline-block;
      font-size: 0.7rem;
      font-weight: 900;
      padding: 2px 6px;
      border: 2px solid var(--border-black);
      margin-top: 3px;
      color: #000;
    }

    .download-desc {
      font-size: 0.8rem;
      line-height: 1.55;
      color: var(--text-sub);
      margin-bottom: 16px;
    }

    .download-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      font-family: var(--font-heading);
      font-weight: 900;
      font-size: 0.88rem;
      text-transform: uppercase;
      padding: 10px 14px;
      border: 4px solid var(--border-black);
      box-shadow: var(--shadow-sm);
      cursor: pointer;
      text-decoration: none;
      transition: var(--transition-spring);
    }

    .btn-excel { background: var(--color-mint); color: #000; }
    .btn-csv   { background: var(--color-yellow); color: #000; }
    .btn-json  { background: var(--color-cyan); color: #000; }

    .download-btn:hover {
      transform: translateY(-3px) scale(1.04) rotate(-1deg);
      box-shadow: 6px 6px 0 0 var(--color-red);
    }

    .download-btn:active {
      transform: translate(3px, 3px) scale(0.95);
      box-shadow: 0 0 0 0 #000;
    }

    /* 版本对比卡片 */
    .version-compare-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
    }

    .version-card {
      background: var(--bg-card-sub);
      border: 3px solid var(--border-black);
      box-shadow: var(--shadow-sm);
      padding: 14px;
      color: var(--text-black);
    }

    .version-field-label {
      font-size: 0.72rem;
      font-weight: 900;
      color: var(--text-sub);
      text-transform: uppercase;
      margin-top: 8px;
    }

    .version-field-val {
      font-size: 0.88rem;
      font-weight: 800;
      color: var(--text-black);
    }

    .wiki-link-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      margin-top: 10px;
      padding: 6px 12px;
      background: var(--bg-card);
      border: 3px solid var(--border-black);
      box-shadow: 3px 3px 0 0 #000;
      font-family: var(--font-heading);
      font-weight: 900;
      font-size: 0.75rem;
      color: var(--text-black);
      text-decoration: none;
      transition: var(--transition-spring);
    }

    .wiki-link-btn:hover {
      background: var(--color-yellow);
      color: #000000;
      transform: translateY(-2px) scale(1.05) rotate(1.5deg);
      box-shadow: 5px 5px 0 0 var(--color-cyan);
    }

    .wiki-link-btn:active {
      transform: translate(2px, 2px) scale(0.95);
      box-shadow: 0 0 0 0 #000;
    }

    /* B站解说专属卡片条 */
    .bili-card {
      background: var(--color-yellow);
      border: 4px solid var(--border-black);
      box-shadow: var(--shadow-md);
      padding: 18px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
      transform: rotate(-0.5deg);
      color: #000000;
    }

    [data-theme="dark"] .bili-card {
      background: #181810;
      color: #ffffff;
    }

    /* 响应式调整 */
    @media (max-width: 768px) {
      body {
        padding: 0;
      }
      .navbar {
        padding: 10px 14px;
      }
      main {
        padding: 14px 14px 60px 14px;
      }
      .brand-title {
        font-size: 1.1rem;
      }
      .brand-subtitle {
        display: none;
      }
      .filter-panel {
        padding: 14px;
      }
      .stat-value {
        font-size: 1.8rem;
      }
      .games-grid {
        grid-template-columns: 1fr;
      }
    }

    /* 暗黑模式下特定彩色组件的深度暗化适配 (遵从沉稳雅致暗调，杜绝刺眼) */
    [data-theme="dark"] .playful-ticker {
      background: #000000;
      color: #b08f3a; /* 调暗黄色为暗金，醒目而不刺眼 */
    }
    [data-theme="dark"] .geo-dot {
      background: var(--color-red);
      border-color: #000000;
    }

    [data-theme="dark"] .brand-logo {
      background: var(--color-red);
      color: #ffffff;
      border-color: #000000;
    }

    [data-theme="dark"] .btn-download-nav {
      background: var(--color-cyan);
      color: #ffffff;
      border-color: #000000;
    }
    [data-theme="dark"] .btn-download-nav:hover {
      background: var(--color-yellow);
      color: #ffffff;
      box-shadow: 8px 8px 0 0 #000000;
    }

    [data-theme="dark"] .btn-theme-toggle {
      background: var(--color-yellow);
      color: #ffffff;
      border-color: #000000;
    }
    [data-theme="dark"] .btn-theme-toggle:hover {
      background: var(--color-cyan);
      color: #ffffff;
      box-shadow: 8px 8px 0 0 #000000;
    }

    /* 结果统计高亮方块暗化 - 白字黑边沉稳古铜金 */
    [data-theme="dark"] .result-count-highlight {
      background: var(--color-yellow);
      color: #ffffff;
      border: 3px solid #000000;
      box-shadow: 3px 3px 0 0 #000000;
    }

    /* 状态与类型徽章全面暗化 */
    [data-theme="dark"] .badge {
      color: #ffffff;
      border-color: #000000;
    }
    [data-theme="dark"] .badge-cross { background: var(--color-mint); color: #ffffff; }
    [data-theme="dark"] .badge-nes   { background: var(--color-cyan); color: #ffffff; }
    [data-theme="dark"] .badge-fc    { background: var(--color-coral); color: #ffffff; }
    [data-theme="dark"] .badge-fds   { background: var(--color-yellow); color: #ffffff; }

    /* 表格内标签暗化 */
    [data-theme="dark"] .tag-en { background: #28303d; color: #e2e8f0; }
    [data-theme="dark"] .tag-ja { background: var(--color-red); color: #ffffff; }
    [data-theme="dark"] .tag-na { background: var(--color-cyan); color: #ffffff; }
    [data-theme="dark"] .tag-jp { background: var(--color-coral); color: #ffffff; }

    /* B站解说视频直达按钮暗化 */
    [data-theme="dark"] .bili-btn {
      background: var(--color-red);
      color: #ffffff !important;
      border-color: #000000;
    }
    [data-theme="dark"] .bili-btn:hover {
      background: var(--color-cyan);
      color: #ffffff !important;
      box-shadow: 5px 5px 0 0 #000000;
    }

    /* 药丸过滤器按钮激活态与悬停暗化 */
    [data-theme="dark"] .filter-pill:hover {
      background: #242432;
      color: #ffffff;
      box-shadow: 6px 6px 0 0 #000000;
    }
    [data-theme="dark"] .filter-pill.pill-cross.active { background: var(--color-mint); color: #ffffff; }
    [data-theme="dark"] .filter-pill.pill-video.active { background: var(--color-red); color: #ffffff; }
    [data-theme="dark"] .filter-pill.pill-nes.active   { background: var(--color-cyan); color: #ffffff; }
    [data-theme="dark"] .filter-pill.pill-fc.active    { background: var(--color-coral); color: #ffffff; }
    [data-theme="dark"] .filter-pill.pill-fds.active   { background: var(--color-yellow); color: #ffffff; }

    /* 分页按钮暗黑高亮 */
    [data-theme="dark"] .page-btn:hover:not(:disabled) {
      background: #242432;
      color: #ffffff;
      box-shadow: 5px 5px 0 0 #000000;
    }
    [data-theme="dark"] .page-btn.active {
      background: #000000;
      color: #bfa143;
      border-color: #bfa143;
    }

    /* 表格与卡片 Hover：沉稳深蓝灰底色，告别刺眼黄色 */
    [data-theme="dark"] tbody tr:hover {
      background: #242432 !important;
      color: #ffffff !important;
    }
    [data-theme="dark"] tbody tr:hover strong,
    [data-theme="dark"] tbody tr:hover .sub-val,
    [data-theme="dark"] tbody tr:hover .publisher-tag {
      color: #ffffff !important;
    }

    [data-theme="dark"] .game-card:hover {
      background-color: #242432 !important;
      box-shadow: 10px 10px 0 0 #000000;
    }
    [data-theme="dark"] .game-card:hover .game-title-zh,
    [data-theme="dark"] .game-card:hover .game-title-en,
    [data-theme="dark"] .game-card:hover .game-title-ja,
    [data-theme="dark"] .game-card:hover .publisher-tag,
    [data-theme="dark"] .game-card:hover .meta-label,
    [data-theme="dark"] .game-card:hover .meta-row span {
      color: #ffffff !important;
    }

    [data-theme="dark"] .stat-card:hover {
      background-color: #242432 !important;
      box-shadow: 10px 10px 0 0 #000000;
    }
    [data-theme="dark"] .stat-card:hover .stat-value,
    [data-theme="dark"] .stat-card:hover .stat-label {
      color: #ffffff !important;
    }

    /* 下载中心卡片按钮图标暗化 */
    [data-theme="dark"] .icon-excel, [data-theme="dark"] .btn-excel { background: var(--color-mint); color: #ffffff; }
    [data-theme="dark"] .icon-csv,   [data-theme="dark"] .btn-csv   { background: var(--color-yellow); color: #ffffff; }
    [data-theme="dark"] .icon-json,  [data-theme="dark"] .btn-json  { background: var(--color-cyan); color: #ffffff; }
    [data-theme="dark"] .download-card:hover { box-shadow: 8px 8px 0 0 #000000; }

  </style>
</head>
<body>

  <!-- 顶部俏皮野兽派 Ticker 装饰条 (严禁任何 Emoji，纯 SVG 几何图形与大写标题) -->
  <div class="playful-ticker">
    <div class="ticker-item"><span class="geo-dot"></span> NINTENDO FC / FDS / NES CROSS-REGION UNIFIED ARCHIVE <span class="geo-dot"></span></div>
    <div class="ticker-item">NO-INTRO DAT CLONE ENGINE // ROM-NAME-CN 权威对照库 // BILIBILI 视频编年史</div>
    <div class="ticker-item"><span class="geo-dot"></span> 100% OFFLINE CAPABLE // NEO-BRUTALIST PLAYFUL</div>
  </div>

  <!-- 顶部导航 -->
  <header>
    <div class="navbar">
      <a href="#" class="brand">
        <div class="brand-logo">FC</div>
        <div>
          <div class="brand-title">任天堂 NES / 红白机游戏库</div>
          <div class="brand-subtitle">结合 NO-INTRO DAT 克隆树与 ROM-NAME-CN 跨区整合数据库</div>
        </div>
      </a>
      <div class="header-links">
        <!-- 核心新增：明亮 / 暗黑双模式一键切换按钮 (严格采用纯 SVG，杜绝 Emoji) -->
        <button class="playful-btn btn-theme-toggle" id="themeToggleBtn" title="切换色彩主题 (明亮 / 暗黑 / 跟随系统)">
          <!-- 纯 SVG 矢量图标 (严格遵从无 Emoji、无圆角规范) -->
          <svg class="icon-sun" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" style="display:none;"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
          <svg class="icon-moon" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" style="display:none;"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
          <svg class="icon-system" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" style="display:none;"><rect x="2" y="3" width="20" height="14"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
          <span id="themeToggleText">跟随系统</span>
        </button>

        <button class="playful-btn btn-download-nav" id="openDownloadModalBtn" title="下载全量数据文件 (Excel/CSV/JSON)">
          <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          数据导出下载
        </button>

        <div class="view-toggle">
          <button class="view-btn active" id="viewBtnTable" title="密集表格视图">
            <svg width="15" height="15" fill="currentColor" viewBox="0 0 16 16"><path d="M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V2zm15 2h-4v3h4V4zm0 4h-4v3h4V8zm0 4h-4v3h3a1 1 0 0 0 1-1v-2zm-5 3v-3H6v3h4zm-5 0v-3H1v2a1 1 0 0 0 1 1h3zm-4-4h4V8H1v3zm0-4h4V4H1v3zm5-3v3h4V4H6zm4 4H6v3h4V8z"/></svg>
            密集表格
          </button>
          <button class="view-btn" id="viewBtnGrid" title="海报卡片视图">
            <svg width="15" height="15" fill="currentColor" viewBox="0 0 16 16"><path d="M1 2.5A1.5 1.5 0 0 1 2.5 1h3A1.5 1.5 0 0 1 7 2.5v3A1.5 1.5 0 0 1 5.5 7h-3A1.5 1.5 0 0 1 1 5.5v-3zm8 0A1.5 1.5 0 0 1 10.5 1h3A1.5 1.5 0 0 1 15 2.5v3A1.5 1.5 0 0 1 13.5 7h-3A1.5 1.5 0 0 1 9 5.5v-3zm-8 8A1.5 1.5 0 0 1 2.5 9h3A1.5 1.5 0 0 1 7 10.5v3A1.5 1.5 0 0 1 5.5 15h-3A1.5 1.5 0 0 1 1 13.5v-3zm8 0A1.5 1.5 0 0 1 10.5 9h3a1.5 1.5 0 0 1 1.5 1.5v3a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 9 13.5v-3z"/></svg>
            海报卡片
          </button>
        </div>
      </div>
    </div>
  </header>

  <main>
    <!-- 统计看板 (俏皮野兽派多彩与微倾斜) -->
    <section class="stats-bar" id="statsBar">
      <div class="stat-card" style="--accent-color: var(--color-red); --hover-shadow-color: var(--color-cyan);">
        <div class="stat-value" id="statTotalGames">--</div>
        <div class="stat-label">整合后独立游戏总数</div>
      </div>
      <div class="stat-card" style="--accent-color: var(--color-mint); --hover-shadow-color: var(--color-red);">
        <div class="stat-value" id="statCrossRegion">--</div>
        <div class="stat-label">美日同款跨区 (已合并)</div>
      </div>
      <div class="stat-card" style="--accent-color: var(--color-cyan); --hover-shadow-color: var(--color-coral);">
        <div class="stat-value" id="statNesOnly">--</div>
        <div class="stat-label">NES 欧美独占游戏</div>
      </div>
      <div class="stat-card" style="--accent-color: var(--color-coral); --hover-shadow-color: var(--color-yellow);">
        <div class="stat-value" id="statJpOnly">--</div>
        <div class="stat-label">日本地区独占 (FC/FDS)</div>
      </div>
      <div class="stat-card" style="--accent-color: var(--color-yellow); --hover-shadow-color: var(--color-mint);">
        <div class="stat-value" id="statRawTotal">--</div>
        <div class="stat-label">维基百科原始记录总计</div>
      </div>
      <div class="stat-card" style="--accent-color: var(--color-red); --hover-shadow-color: var(--color-cyan);">
        <div class="stat-value" id="statVideoCount">--</div>
        <div class="stat-label">B站编年史解说视频</div>
      </div>
    </section>

    <!-- 筛选面板 -->
    <section class="filter-panel" id="filterPanel">
      <div class="search-row">
        <div class="search-wrapper">
          <span class="search-icon">
            <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
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
        <button class="filter-pill pill-video" data-filter="video" id="pillVideoBtn">
          <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" style="vertical-align: -2px; margin-right: 4px;"><rect x="2" y="7" width="20" height="15" rx="0"/><polyline points="17 2 12 7 7 2"/></svg>
          B站编年史解说
        </button>
        <button class="filter-pill pill-nes" data-filter="nes">NES (欧美版)</button>
        <button class="filter-pill pill-fc" data-filter="fc">FC (卡带)</button>
        <button class="filter-pill pill-fds" data-filter="fds">FDS (磁碟机)</button>
      </div>
    </section>

    <!-- 结果统计与切换栏 -->
    <div class="results-info-bar">
      <div>
        找到 <span id="filteredCount" class="result-count-highlight">0</span> 款游戏
        <span id="pageInfoSpan" style="margin-left: 8px; font-weight: 800;">(第 1 / 1 页)</span>
      </div>
      <div>
        每页显示：
        <select id="pageSizeSelect" class="custom-select" style="height: 38px; padding: 0 28px 0 10px;">
          <option value="36">36 款</option>
          <option value="60" selected>60 款</option>
          <option value="120">120 款</option>
          <option value="999999">全部</option>
        </select>
      </div>
    </div>

    <!-- 顶部翻页控件 -->
    <div class="pagination-bar pagination-bar-top" id="paginationBarTop"></div>

    <!-- 网格视图容器 -->
    <section class="games-grid" id="gamesGrid" style="display: none;"></section>

    <!-- 表格视图容器（默认密集表格） -->
    <section class="table-container" id="tableContainer" style="display: block;">
      <table>
        <thead>
          <tr>
            <th style="min-width: 150px;">中文译名</th>
            <th style="width: 130px; text-align: center;">视频介绍</th>
            <th style="min-width: 240px;">英文名 / 日文名</th>
            <th style="min-width: 180px;">美版发售日 / 日版发售日</th>
            <th style="min-width: 130px;">主要发行商</th>
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

    <!-- 底部翻页控件 -->
    <div class="pagination-bar" id="paginationBar"></div>
  </main>

  <!-- 数据下载中心模态弹窗 -->
  <div class="modal-backdrop" id="downloadModalBackdrop">
    <div class="modal-content" style="max-width: 820px;">
      <div class="modal-header">
        <button class="modal-close-btn" id="downloadModalCloseBtn" aria-label="关闭">&times;</button>
        <div class="badges-row">
          <span class="badge badge-cross">离线资源下载</span>
          <span class="badge badge-nes">全格式就绪</span>
        </div>
        <h2 style="font-family: var(--font-heading); font-size: 1.4rem; font-weight: 900; margin-top: 6px; margin-bottom: 4px; text-transform: uppercase;">整合数据资源导出与下载中心</h2>
        <div style="color: var(--text-sub); font-size: 0.85rem; font-weight: 800;">
          任天堂 NES 与红白机 (FC/FDS) 跨区整合全量数据，已生成 EXCEL、CSV 与 JSON 格式，均包含 B 站视频章节时间轴
        </div>
      </div>
      <div class="modal-body">
        <div class="download-grid">
          <!-- Excel 卡片 -->
          <div class="download-card">
            <div>
              <div class="download-card-header">
                <div class="download-icon icon-excel">
                  <svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="16" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
                </div>
                <div>
                  <div class="download-title">Excel 格式工作簿</div>
                  <div class="download-badge" style="background: var(--color-mint);">.xlsx 格式</div>
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
              <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              立即下载 EXCEL (.XLSX)
            </a>
          </div>

          <!-- CSV 卡片 -->
          <div class="download-card">
            <div>
              <div class="download-card-header">
                <div class="download-icon icon-csv">
                  <svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                </div>
                <div>
                  <div class="download-title">CSV 逗号表格</div>
                  <div class="download-badge" style="background: var(--color-yellow);">.csv 格式</div>
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
              <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              立即下载 CSV (.CSV)
            </a>
          </div>

          <!-- JSON 卡片 -->
          <div class="download-card">
            <div>
              <div class="download-card-header">
                <div class="download-icon icon-json">
                  <svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
                </div>
                <div>
                  <div class="download-title">JSON 结构化数据</div>
                  <div class="download-badge" style="background: var(--color-cyan);">.json 格式</div>
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
              <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              立即下载 JSON (.JSON)
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
        <h2 id="modalTitleZh" style="font-family: var(--font-heading); font-size: 1.5rem; font-weight: 900; margin-bottom: 4px;"></h2>
        <div id="modalTitleEn" style="color: var(--text-sub); font-size: 1rem; font-weight: 800;"></div>
        <div id="modalTitleJa" style="color: var(--text-sub); font-size: 0.88rem; font-weight: 700;"></div>
      </div>
      <div class="modal-body">
        <div style="background: var(--bg-card-sub); padding: 14px 18px; border: 4px solid var(--border-black); box-shadow: var(--shadow-sm); font-size: 0.9rem;">
          <div style="color: var(--text-sub); font-size: 0.75rem; font-weight: 900; text-transform: uppercase;">各地区发行日期总览</div>
          <div style="display: flex; gap: 24px; margin-top: 6px; flex-wrap: wrap; font-family: var(--font-heading); font-size: 0.95rem;">
            <div>日本: <strong id="modalDateJp" style="color: var(--text-black);">--</strong></div>
            <div>北美: <strong id="modalDateNa" style="color: var(--text-black);">--</strong></div>
            <div>欧洲: <strong id="modalDatePal" style="color: var(--text-black);">--</strong></div>
          </div>
        </div>

        <div>
          <h4 style="font-family: var(--font-heading); font-size: 1rem; font-weight: 900; margin-bottom: 12px; text-transform: uppercase;">各版本详细数据对比</h4>
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
    // ==========================================================================
    // 前端核心逻辑 (无外部依赖，兼容现代各主流浏览器，内置明/暗模式一键切换)
    // ==========================================================================

    let allGames = [];
    let filteredGames = [];
    let currentView = 'table'; // 'table' | 'grid'
    let currentPage = 1;
    let pageSize = 60;
    let activeFilter = 'all';

    // 日期排序辅助解析
    function parseDateToNum(dStr) {
      if (!dStr) return null;
      const match = String(dStr).match(/(\d{4})(?:[-年/](\d{1,2}))?(?:[-月/](\d{1,2}))?/);
      if (match) {
        const y = parseInt(match[1], 10);
        const m = match[2] ? parseInt(match[2], 10) : 1;
        const d = match[3] ? parseInt(match[3], 10) : 1;
        return y * 10000 + m * 100 + d;
      }
      return null;
    }

    // 提取全部地区版本中最早的有效发售日及数值
    function getEarliestReleaseInfo(game) {
      const rd = game.release_dates || {};
      const candidates = [
        rd.japan,
        rd.north_america,
        rd.europe
      ].filter(s => s && String(s).trim());

      if (candidates.length === 0) {
        return { num: 99999999, str: '未知发售日' };
      }

      let best = null;
      for (const s of candidates) {
        const num = parseDateToNum(s);
        if (num !== null) {
          if (!best || num < best.num) {
            best = { num, str: s };
          }
        }
      }

      return best || { num: 99999999, str: candidates[0] };
    }

    function parseGameDateNum(game) {
      return getEarliestReleaseInfo(game).num;
    }

    // --------------------------------------------------------------------------
    // 主题状态机系统：支持 明亮 (light) / 暗黑 (dark) / 跟随系统 (system) 三态切换
    // 跟随系统意为：在明亮和黑暗中间，根据操作系统当前颜色偏好自动挑选
    // --------------------------------------------------------------------------
    let currentThemePref = localStorage.getItem('fc_nes_theme_pref') || 'system';

    // 探测操作系统当前是否偏好暗色
    function getSystemTheme() {
      return (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
    }

    // 将用户偏好解析为页面当前实际生效的颜色主题 ('light' | 'dark')
    function resolveActiveTheme(pref) {
      if (pref === 'system') {
        return getSystemTheme();
      }
      return pref === 'dark' ? 'dark' : 'light';
    }

    // 应用指定的主题偏好并持久化
    function applyTheme(pref) {
      currentThemePref = pref;
      try {
        localStorage.setItem('fc_nes_theme_pref', pref);
      } catch (e) {}

      const activeTheme = resolveActiveTheme(pref);
      document.documentElement.setAttribute('data-theme', activeTheme);
      updateThemeToggleUI(pref, activeTheme);
    }

    // 更新主题切换按钮的图标、文字与视觉色彩
    function updateThemeToggleUI(pref, activeTheme) {
      const btn = document.getElementById('themeToggleBtn');
      const text = document.getElementById('themeToggleText');
      if (!btn) return;
      const sun = btn.querySelector('.icon-sun');
      const moon = btn.querySelector('.icon-moon');
      const sys = btn.querySelector('.icon-system');

      if (sun) sun.style.display = 'none';
      if (moon) moon.style.display = 'none';
      if (sys) sys.style.display = 'none';

      if (pref === 'light') {
        if (sun) sun.style.display = 'inline-block';
        if (text) text.textContent = '明亮模式';
        btn.setAttribute('title', '当前: 明亮模式 (点击切换为暗黑模式)');
        btn.style.background = '#ffffff';
        btn.style.color = '#000000';
      } else if (pref === 'dark') {
        if (moon) moon.style.display = 'inline-block';
        if (text) text.textContent = '暗黑模式';
        btn.setAttribute('title', '当前: 暗黑模式 (点击切换为跟随系统)');
        btn.style.background = 'var(--color-yellow)';
        btn.style.color = '#ffffff';
      } else {
        // system (跟随系统)
        if (sys) sys.style.display = 'inline-block';
        const sysLabel = activeTheme === 'dark' ? '暗' : '亮';
        if (text) text.textContent = `跟随系统 (${sysLabel})`;
        btn.setAttribute('title', `当前: 跟随系统 [当前系统为${activeTheme === 'dark' ? '深色' : '浅色'}] (点击切换为明亮模式)`);
        if (activeTheme === 'dark') {
          btn.style.background = 'var(--color-cyan)';
          btn.style.color = '#ffffff';
        } else {
          btn.style.background = 'var(--color-mint)';
          btn.style.color = '#000000';
        }
      }
    }

    // 三态轮流切换：light -> dark -> system -> light
    function cycleNextTheme() {
      if (currentThemePref === 'light') {
        applyTheme('dark');
      } else if (currentThemePref === 'dark') {
        applyTheme('system');
      } else {
        applyTheme('light');
      }
    }

    // 初始化入口
    function init() {
      // 启动并应用主题偏好
      applyTheme(currentThemePref);

      // 动态监听系统明暗变化：当用户选择“跟随系统”时，系统主题改变页面立刻自动跟随
      if (window.matchMedia) {
        const mql = window.matchMedia('(prefers-color-scheme: dark)');
        const onSysThemeChange = () => {
          if (currentThemePref === 'system') {
            applyTheme('system');
          }
        };
        if (mql.addEventListener) {
          mql.addEventListener('change', onSysThemeChange);
        } else if (mql.addListener) {
          mql.addListener(onSysThemeChange);
        }
      }

      if (window.FC_NES_DATA) {
        renderWithData(window.FC_NES_DATA);
      } else {
        fetch('fc_nes_games.json')
          .then(res => res.json())
          .then(data => renderWithData(data))
          .catch(err => {
            console.error('加载本地 JSON 失败:', err);
            document.getElementById('statTotalGames').textContent = '错误';
          });
      }
    }

    function renderWithData(data) {
      allGames = data.games || [];
      // 兼顾 data.metadata.statistics 与顶层 data.statistics
      const stats = (data.metadata && data.metadata.statistics) || data.statistics || {};

      // 1. 整合后独立游戏总数
      const totalGames = stats.total_unified_games || stats.total_games || allGames.length;

      // 2. 美日同款跨区（已合并）
      const crossRegion = stats.cross_region_games !== undefined 
        ? stats.cross_region_games 
        : allGames.filter(g => g.is_cross_region).length;

      // 3. NES 欧美独占游戏
      const nesOnly = stats.nes_exclusive_games !== undefined 
        ? stats.nes_exclusive_games 
        : allGames.filter(g => {
            const plats = g.platforms || [];
            return plats.length === 1 && plats[0] === 'NES';
          }).length;

      // 4. 日本地区独占 (FC/FDS)
      const jpOnly = stats.japan_exclusive_games !== undefined 
        ? stats.japan_exclusive_games 
        : allGames.filter(g => !(g.platforms || []).includes('NES')).length;

      // 5. 维基百科原始记录总计
      const rawTotal = stats.raw_records_total || stats.total_wiki_records || (stats.raw_records && stats.raw_records.total) || 1961;

      // 6. B站编年史解说视频
      const videoCount = stats.bilibili_videos_matched !== undefined 
        ? stats.bilibili_videos_matched 
        : (stats.matched_bilibili_videos !== undefined ? stats.matched_bilibili_videos : allGames.filter(g => g.video).length);

      // 填充统计看板数值
      document.getElementById('statTotalGames').textContent = Number(totalGames).toLocaleString();
      document.getElementById('statCrossRegion').textContent = Number(crossRegion).toLocaleString();
      document.getElementById('statNesOnly').textContent = Number(nesOnly).toLocaleString();
      document.getElementById('statJpOnly').textContent = Number(jpOnly).toLocaleString();
      document.getElementById('statRawTotal').textContent = Number(rawTotal).toLocaleString();
      document.getElementById('statVideoCount').textContent = Number(videoCount).toLocaleString();

      populatePublishers(allGames);
      applyFilters();
    }

    // 填充发行商选项
    function populatePublishers(games) {
      const pubMap = new Map();
      games.forEach(g => {
        (g.publishers || []).forEach(p => {
          if (p && p.trim()) {
            const pub = p.trim();
            pubMap.set(pub, (pubMap.get(pub) || 0) + 1);
          }
        });
      });

      const sortedPubs = Array.from(pubMap.entries()).sort((a, b) => b[1] - a[1]);
      const pubSelect = document.getElementById('publisherSelect');
      sortedPubs.forEach(([name, count]) => {
        if (count >= 2) {
          const opt = document.createElement('option');
          opt.value = name;
          opt.textContent = `${name} (${count})`;
          pubSelect.appendChild(opt);
        }
      });
    }

    // 过滤与排序
    function applyFilters() {
      const searchKeyword = document.getElementById('searchInput').value.trim().toLowerCase();
      const selectedPub = document.getElementById('publisherSelect').value;
      const sortOrder = document.getElementById('sortSelect').value;

      filteredGames = allGames.filter(game => {
        if (activeFilter === 'cross' && !game.is_cross_region) return false;
        if (activeFilter === 'video' && !game.video) return false;
        if (activeFilter === 'nes' && !game.platforms.includes('NES')) return false;
        if (activeFilter === 'fc' && !game.platforms.includes('FC')) return false;
        if (activeFilter === 'fds' && !game.platforms.includes('FDS')) return false;

        if (selectedPub && !(game.publishers || []).includes(selectedPub)) return false;

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
        document.getElementById('paginationBarTop').innerHTML = '';
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

    // 渲染网格视图 (俏皮野兽派轻微旋转与彩色硬投影)
    function renderGridView(games) {
      const grid = document.getElementById('gamesGrid');
      grid.innerHTML = '';

      games.forEach((game) => {
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

        const titleZh = game.title_zh ? escapeHtml(game.title_zh) : `<span class="empty">未定中文译名</span>`;
        const titleEn = game.title_en || 'Unknown Title';
        const titleJa = game.title_ja ? `<div class="game-title-ja">${escapeHtml(game.title_ja)}</div>` : '';

        const dateStr = getEarliestReleaseInfo(game).str;
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
              <span style="font-weight: 800;">${escapeHtml(dateStr)}</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">主要发行商</span>
              <span class="publisher-tag" title="${escapeHtml(publishersStr)}">${escapeHtml(publishersStr)}</span>
            </div>
            ${game.video ? `
            <div class="meta-row" style="margin-top:6px;">
              <span class="meta-label">视频解说</span>
              <a href="${escapeHtml(game.video.url)}" target="_blank" rel="noopener" class="bili-btn" onclick="event.stopPropagation();" title="${escapeHtml(game.video.video_title)} | 分段: ${escapeHtml(game.video.chapter_name)} (起播时间: ${game.video.timestamp})">
                <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                视频介绍 BY 雷文
              </a>
            </div>` : ''}
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

        const enName = game.title_en || '-';
        const jaName = game.title_ja || '-';
        const naDate = (game.release_dates && game.release_dates.north_america) ? game.release_dates.north_america : '-';
        const jpDate = (game.release_dates && game.release_dates.japan) ? game.release_dates.japan : '-';
        const publishersStr = (game.publishers || []).join(', ') || '-';

        let videoCell = '<td style="text-align: center; color: var(--text-sub);">-</td>';
        if (game.video) {
          videoCell = `
            <td style="text-align: center; white-space: nowrap;">
              <a href="${escapeHtml(game.video.url)}" target="_blank" rel="noopener" class="bili-btn" onclick="event.stopPropagation();" title="${escapeHtml(game.video.video_title)} | 分段: ${escapeHtml(game.video.chapter_name)} (起播时间: ${game.video.timestamp})">
                <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                BY 雷文
              </a>
            </td>`;
        }

        tr.innerHTML = `
          <td>
            <strong style="font-family:var(--font-heading);font-weight:900;font-size:1.02rem;color:var(--text-black);">${escapeHtml(game.title_zh || '-')}</strong>
          </td>
          ${videoCell}
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
        `;

        tbody.appendChild(tr);
      });
    }

    // 渲染分页器 (无 Emoji，纯文本或 SVG)
    function renderPagination(totalPages) {
      const bars = [
        document.getElementById('paginationBarTop'),
        document.getElementById('paginationBar')
      ].filter(Boolean);

      bars.forEach(bar => {
        bar.innerHTML = '';
        if (totalPages <= 1) return;

        const prevBtn = document.createElement('button');
        prevBtn.className = 'page-btn';
        prevBtn.innerHTML = '&lt;';
        prevBtn.disabled = (currentPage === 1);
        prevBtn.onclick = () => { if (currentPage > 1) { currentPage--; renderCurrentPage(); window.scrollTo({top: 280, behavior: 'smooth'}); } };
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
            span.style.fontWeight = '900';
            span.style.padding = '0 4px';
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
            span.style.fontWeight = '900';
            span.style.padding = '0 4px';
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
        nextBtn.innerHTML = '&gt;';
        nextBtn.disabled = (currentPage === totalPages);
        nextBtn.onclick = () => { if (currentPage < totalPages) { currentPage++; renderCurrentPage(); window.scrollTo({top: 280, behavior: 'smooth'}); } };
        bar.appendChild(nextBtn);
      });
    }

    // 模态弹窗 - 查看跨版本并排对比
    function openGameDetail(game) {
      document.getElementById('modalTitleZh').textContent = game.title_zh || '未定中文名';
      document.getElementById('modalTitleEn').textContent = game.title_en || '';
      document.getElementById('modalTitleJa').textContent = game.title_ja || '';

      document.getElementById('modalDateJp').textContent = (game.release_dates && game.release_dates.japan) || '未在日本发售';
      document.getElementById('modalDateNa').textContent = (game.release_dates && game.release_dates.north_america) || '未在北美发售';
      document.getElementById('modalDatePal').textContent = (game.release_dates && game.release_dates.europe) || '未在欧洲发售';

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
            <span style="font-size:0.78rem; font-weight:800; color:var(--text-sub);">${escapeHtml(v.region || '')}</span>
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
          <div class="version-field-val" style="color:var(--text-black);">${escapeHtml(v.publisher || '未知')}</div>

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
          <a href="${escapeHtml(game.wiki_url)}" target="_blank" rel="noopener" class="wiki-link-btn" style="background:var(--color-yellow);color:#000000;padding:8px 14px;font-size:0.85rem;margin-bottom:12px;">
            访问主维基百科页面 &nearr;
          </a>
        `;
      }
      if (game.video) {
        linksHtml += `
          <div class="bili-card">
            <div>
              <div style="color: var(--color-red); font-size: 0.8rem; font-weight: 900; text-transform: uppercase; display: flex; align-items: center; gap: 6px;">
                <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                B站红白机游戏编年史对应解说
              </div>
              <div style="font-family: var(--font-heading); font-size: 1.05rem; font-weight: 900; margin-top: 4px;">
                ${escapeHtml(game.video.video_title)}
              </div>
              <div style="font-size: 0.82rem; font-weight: 800; color: var(--text-sub); margin-top: 2px;">
                分段章节: <strong style="color: var(--color-red);">${escapeHtml(game.video.chapter_name)}</strong> (起播时间点: ${game.video.timestamp})
              </div>
            </div>
            <a href="${escapeHtml(game.video.url)}" target="_blank" rel="noopener" class="bili-btn" style="padding: 10px 20px; font-size: 0.88rem;">
              <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>
              视频介绍 BY 雷文 &nearr;
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

      // 主题切换按钮监听 (三态循环：明亮 -> 暗黑 -> 跟随系统)
      const themeToggleBtn = document.getElementById('themeToggleBtn');
      if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', cycleNextTheme);
      }

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
          currentPage = 1;
          applyFilters();
        });
      });

      // 视图切换（表格 / 卡片）
      const viewBtnTable = document.getElementById('viewBtnTable');
      const viewBtnGrid = document.getElementById('viewBtnGrid');

      viewBtnTable.addEventListener('click', () => {
        if (currentView === 'table') return;
        currentView = 'table';
        viewBtnTable.classList.add('active');
        viewBtnGrid.classList.remove('active');
        renderCurrentPage();
      });

      viewBtnGrid.addEventListener('click', () => {
        if (currentView === 'grid') return;
        currentView = 'grid';
        viewBtnGrid.classList.add('active');
        viewBtnTable.classList.remove('active');
        renderCurrentPage();
      });

      // 下载弹窗开关
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


def generate_game_id(title_en: Optional[str] = "", title_zh: Optional[str] = "", title_ja: Optional[str] = "", fallback: str = "") -> str:
    """基于英文名、中文名或日文名生成 URL 安全的标准小写 Slug 游戏 ID"""
    slug_seed = (title_en or "").strip() or (title_zh or "").strip() or (title_ja or "").strip()
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', slug_seed).strip('-').lower()
    return slug or fallback


@dataclass
class FcNesRawRecord:
    """单平台原始记录"""
    id: str
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
        game_id = generate_game_id(title_en, title_zh, "", fallback=f"nes-{len(games)+1}")

        game = FcNesRawRecord(
            id=game_id,
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
        game_id = generate_game_id(title_en, title_zh, title_ja, fallback=f"{platform_code.lower()}-{len(games)+1}")

        game = FcNesRawRecord(
            id=game_id,
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

    @staticmethod
    def _clean_ascii(text: str) -> str:
        """剥离重音符号 (如 Déjà Vu -> Deja Vu)"""
        if not text:
            return ""
        nfkd = unicodedata.normalize('NFKD', text)
        return ''.join([c for c in nfkd if not unicodedata.combining(c)])

    @classmethod
    def get_name_variants(cls, name: str) -> List[str]:
        """为英文名生成多种可能在 No-Intro 中存在的规范化变体"""
        if not name:
            return []
        variants = [name]

        # 剥离重音符号
        ascii_name = cls._clean_ascii(name)
        if ascii_name != name:
            variants.append(ascii_name)

        # 剥离品牌与厂商所有格前缀 (如 Disney's Aladdin -> Aladdin)
        brand_stripped = re.sub(r"^(Disney's|Walt Disney's|Capcom's|Konami's)\s+", "", name, flags=re.I)
        if brand_stripped != name:
            variants.append(brand_stripped)

        expanded = []
        for v in variants:
            expanded.append(v)
            if ":" in v:
                expanded.append(v.replace(":", " -"))
                expanded.append(v.replace(":", ""))
            if "&" in v:
                expanded.append(v.replace("&", "and"))
                expanded.append(v.replace("&", "-"))
                expanded.append(v.replace("&", " "))
            if "°" in v:
                expanded.append(v.replace("°", ""))
                expanded.append(v.replace("°", " Degrees"))

        final_variants = []
        for v in expanded:
            final_variants.append(v)
            # 整体定冠词 The / A / An 转换
            m_the = re.match(r'^(The|A|An)\s+(.*)$', v, re.I)
            if m_the:
                art, rest = m_the.group(1), m_the.group(2)
                final_variants.append(f"{rest}, {art}")
            m_the_end = re.search(r'^(.*?),\s*(The|A|An)$', v, re.I)
            if m_the_end:
                rest, art = m_the_end.group(1), m_the_end.group(2)
                final_variants.append(f"{art} {rest}")

            # 副标题定冠词倒置: "The Title: Subtitle" -> "Title, The - Subtitle"
            for sep in [":", " - "]:
                if sep in v:
                    parts = v.split(sep, 1)
                    main_part, sub_part = parts[0].strip(), parts[1].strip()
                    m_sub = re.match(r'^(The|A|An)\s+(.*)$', main_part, re.I)
                    if m_sub:
                        art, rest = m_sub.group(1), m_sub.group(2)
                        final_variants.append(f"{rest}, {art} - {sub_part}")

        seen = set()
        res = []
        for v in final_variants:
            s = v.strip()
            if s and s not in seen:
                seen.add(s)
                res.append(s)
        return res

    def lookup_cn(
        self,
        en_titles: Union[str, List[str]],
        zh_titles: Optional[Union[str, List[str]]] = None
    ) -> str:
        """
        从 rom-name-cn 对照库中匹配权威中文名
        (支持 Unicode 重音分解、冠词倒置、厂商前缀剥离、标点转换、DAT克隆关联及别名字典)
        """
        if isinstance(en_titles, str):
            en_candidates = [en_titles]
        else:
            en_candidates = list(en_titles)

        for orig_en in en_candidates:
            if not orig_en:
                continue
            variants = self.get_name_variants(orig_en)
            for en in variants:
                # 1. 直接 lookup
                cn = self.lookup_cn_by_en(en)
                if cn:
                    return cn
                # 2. DAT 克隆组关联查找
                norm = normalize_text(en)
                if norm in self.dat_clone_links:
                    for clone_norm in self.dat_clone_links[norm]:
                        if clone_norm in self.en_to_cn:
                            return self.en_to_cn[clone_norm]
                # 3. 尝试去除 'and' 的 norm
                norm_no_and = normalize_text(en.replace('&', '').replace(' and ', ''))
                if norm_no_and in self.en_to_cn:
                    return self.en_to_cn[norm_no_and]

        # 4. 若英文未命中，尝试用已有的中文名查 rom-name-cn 的 alias_map 规范名
        if zh_titles:
            zh_candidates = [zh_titles] if isinstance(zh_titles, str) else list(zh_titles)
            for zh in zh_candidates:
                if not zh:
                    continue
                canon = self.canonical_cn(zh)
                norm_zh = normalize_text(zh)
                if norm_zh in self.alias_map:
                    for main_name, val in self.alias_map.items():
                        if val == canon:
                            return canon

        return ""


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
    helper: RomNameCnHelper,
    custom_merges: Optional[List[Tuple[str, str]]] = None
) -> List[Dict[str, Any]]:
    """
    结合 DAT 克隆关系、rom-name-cn 以及用户自定义 override.yaml，将美版 (NES) 与日版 (FC/FDS) 同款游戏聚类合并
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

    # 构建用户自定义合并规则的特征映射与目标优先级
    def gen_lookup_keys(val: Any) -> Set[str]:
        keys = set()
        if not val:
            return keys
        s = str(val).strip()
        if s:
            keys.add(s)
            keys.add(s.lower())
            norm = normalize_text(s)
            if norm:
                keys.add(norm)
            slug = re.sub(r'[^a-zA-Z0-9]+', '-', s).strip('-').lower()
            if slug:
                keys.add(slug)
        return keys

    custom_merge_links: Dict[str, Set[str]] = {}
    target_preferences: Dict[str, str] = {}
    if custom_merges:
        for t1, t2 in custom_merges:
            target_str = str(t1).strip()
            source_str = str(t2).strip()
            k1_set = gen_lookup_keys(target_str)
            k2_set = gen_lookup_keys(source_str)
            for k1 in k1_set:
                custom_merge_links.setdefault(k1, set()).update(k2_set)
                target_preferences[k1] = target_str
            for k2 in k2_set:
                custom_merge_links.setdefault(k2, set()).update(k1_set)
                target_preferences[k2] = target_str

    def get_record_lookup_keys(r: Dict[str, Any]) -> Set[str]:
        keys = set()
        for f in ("title_en", "title_zh", "title_ja"):
            keys.update(gen_lookup_keys(r.get(f)))
        return keys

    record_keys_list = [get_record_lookup_keys(r) for r in indexed_records]

    # 执行并查集两两比对合并
    uf = UnionFind([it["_uid"] for it in indexed_records])
    n = len(indexed_records)

    for i in range(n):
        r1 = indexed_records[i]
        r1_keys = record_keys_list[i]
        for j in range(i + 1, n):
            r2 = indexed_records[j]
            if r1["platform"] != r2["platform"]:
                # 优先检查用户在 override.yaml 中声明的自定义合并规则
                is_custom_merged = False
                matched_rule = ""
                if custom_merge_links:
                    r2_keys = record_keys_list[j]
                    for k1 in r1_keys:
                        if k1 in custom_merge_links and custom_merge_links[k1].intersection(r2_keys):
                            is_custom_merged = True
                            matched_rule = f"{r1.get('title_en')} <-> {r2.get('title_en')}"
                            break

                if is_custom_merged:
                    matched, reason = True, f"adjustments自定义合并规则({matched_rule})"
                else:
                    matched, reason = is_same_fc_nes_game(r1, r2, helper)

                if matched:
                    root1 = uf.find(r1["_uid"])
                    root2 = uf.find(r2["_uid"])
                    if root1 != root2:
                        uf.union(r1["_uid"], r2["_uid"])
                        if is_custom_merged:
                            logger.info(f"应用 adjustments 自定义合并规则: 《{r1.get('title_en')}》({r1['platform']}) 与 《{r2.get('title_en')}》({r2['platform']}) 成功合并为同一游戏")

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

        # 确定主英文名（优先用户在 custom_merges 中显式指定的 target，其次优先美版 NES，最后日版）
        preferred_en = ""
        for it in cluster_items:
            for k in gen_lookup_keys(it.get("title_en")):
                if k in target_preferences:
                    target_candidate = target_preferences[k]
                    for cand_v in [nes_ver, fc_ver, fds_ver]:
                        if cand_v and normalize_text(cand_v.get("title_en", "")) == normalize_text(target_candidate):
                            preferred_en = cand_v["title_en"]
                            break
                if preferred_en:
                    break
            if preferred_en:
                break

        title_en = ""
        if preferred_en:
            title_en = preferred_en
        elif nes_ver and nes_ver.get("title_en"):
            title_en = nes_ver["title_en"]
        elif fc_ver and fc_ver.get("title_en"):
            title_en = fc_ver["title_en"]
        elif fds_ver and fds_ver.get("title_en"):
            title_en = fds_ver["title_en"]

        # 确定主中文名（优先维基官方译名，其次 rom-name-cn 权威民间译名）
        title_zh = ""
        for v in [fc_ver, fds_ver, nes_ver]:
            if v and v.get("title_zh") and v.get("title_zh_source") == "wikipedia":
                title_zh = v["title_zh"]
                break
        if not title_zh:
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

        # 收集日版发售日候选 (FC卡带与FDS磁碟机)，选取其中更早的有效发售日
        jp_candidates = []
        for v in [fc_ver, fds_ver]:
            if v and v.get("release_date"):
                d_str = str(v["release_date"]).strip()
                if d_str:
                    t = parse_date_tuple(d_str)
                    jp_candidates.append((t if t else (9999, 99, 99), d_str))

        japan_date = min(jp_candidates, key=lambda x: x[0])[1] if jp_candidates else ""

        release_dates = {
            "japan": japan_date,
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


def parse_date_tuple(d: Optional[str]) -> Optional[Tuple[int, int, int]]:
    """从日期文本中提取 (year, month, day) 排序元组，解析失败返回 None"""
    if not d:
        return None
    m_year = re.search(r'(\d{4})', str(d))
    if not m_year:
        return None
    year = int(m_year.group(1))
    m_month = re.search(r'(\d{1,2})\s*月', str(d))
    month = int(m_month.group(1)) if m_month else 1
    m_day = re.search(r'(\d{1,2})\s*日', str(d))
    day = int(m_day.group(1)) if m_day else 1
    return (year, month, day)


def merge_raw_records_by_id(
    raw_records: List[Dict[str, Any]],
    helper: Optional[RomNameCnHelper] = None
) -> Dict[str, Any]:
    """
    将 Raw 记录中具有相同 ID 的多平台条目合并为一款游戏：
    1. 相同的项放外层，不同的项保留在 versions 中；
    2. 从 rom-name-cn 匹配权威中文译名 title_cn；
    3. 每个游戏的 release_date 取全部版本中的最早发售日；
    4. 整体游戏列表按该最早 release_date 进行升序排序。
    """
    if helper is None:
        try:
            helper = RomNameCnHelper(workspace_dir=".")
        except Exception as e:
            logger.warning(f"初始化 RomNameCnHelper 失败: {e}")
            helper = None

    grouped: Dict[str, List[Dict[str, Any]]] = OrderedDict()
    for r in raw_records:
        gid = r.get("id")
        if not gid:
            gid = generate_game_id(r.get("title_en"), r.get("title_zh"), r.get("title_ja"))
        grouped.setdefault(gid, []).append(r)

    merged_tuples: List[Tuple[Tuple[int, int, int], OrderedDict]] = []
    platform_order = {"FC": 1, "FDS": 2, "NES": 3}

    for gid, rec_list in grouped.items():
        sorted_recs = sorted(rec_list, key=lambda x: platform_order.get(x.get("platform", ""), 99))

        # 提取外层公共项 (相同的项放外层)
        title_zh = next((r["title_zh"] for r in sorted_recs if r.get("title_zh")), "")
        title_en = next((r["title_en"] for r in sorted_recs if r.get("title_en")), "")
        title_ja = next((r["title_ja"] for r in sorted_recs if r.get("title_ja")), "")
        wiki_url = next((r["wiki_url"] for r in sorted_recs if r.get("wiki_url")), "")

        # 从 rom-name-cn 对照库中匹配权威中文名 title_cn
        title_cn = ""
        if helper:
            ens = [r["title_en"] for r in sorted_recs if r.get("title_en")]
            zhs = [r["title_zh"] for r in sorted_recs if r.get("title_zh")]
            title_cn = helper.lookup_cn(ens, zh_titles=zhs)

        # 收集全部版本的所有发售日并选择最早的一个
        all_dates = []
        for r in sorted_recs:
            for k in ["release_date", "release_date_na", "release_date_pal"]:
                val = (r.get(k) or "").strip()
                if val:
                    all_dates.append(val)

        valid_dates = []
        for d in all_dates:
            t = parse_date_tuple(d)
            if t:
                valid_dates.append((t, d))

        if valid_dates:
            sort_tuple, earliest_release_date = min(valid_dates, key=lambda x: x[0])
        else:
            sort_tuple = (9999, 99, 99)
            earliest_release_date = all_dates[0] if all_dates else ""

        outer_common = {
            "title_zh": title_zh,
            "title_cn": title_cn,
            "title_en": title_en,
            "title_ja": title_ja,
            "release_date": earliest_release_date,
            "wiki_url": wiki_url
        }

        versions: Dict[str, Any] = OrderedDict()
        for r in sorted_recs:
            plat = r.get("platform", "")
            if not plat:
                continue

            ver_dict: Dict[str, Any] = OrderedDict()
            # 提取版本特有的不同字段 (发售日、北美日、欧洲日、发行商等)
            for k in ["release_date", "release_date_na", "release_date_pal", "publisher", "publisher_wiki_url"]:
                val = (r.get(k) or "").strip()
                if val:
                    ver_dict[k] = val

            # 如果该版本的名称或链接与外层公共项不同，才在 version 内部记录
            for k in ["title_zh", "title_en", "title_ja", "wiki_url"]:
                val = (r.get(k) or "").strip()
                outer_val = outer_common.get(k, "")
                if val and val != outer_val:
                    ver_dict[k] = val

            versions[plat] = ver_dict

        item = OrderedDict([
            ("id", gid),
            ("title_zh", title_zh),
            ("title_cn", title_cn),
            ("title_en", title_en),
            ("title_ja", title_ja),
            ("release_date", earliest_release_date),
            ("wiki_url", wiki_url),
            ("versions", versions)
        ])
        merged_tuples.append((sort_tuple, item))

    # 按照全部 release date 里最早的发售日升序排序，次级排序 key 为游戏 ID
    merged_tuples.sort(key=lambda x: (x[0], x[1]["id"]))
    sorted_games = [it[1] for it in merged_tuples]

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_games": len(sorted_games),
        "total_raw_records": len(raw_records),
        "games": sorted_games
    }


def save_raw_data(
    raw_records: List[Dict[str, Any]], 
    bilibili_segments: List[Dict[str, Any]], 
    raw_dir: str = "data/raw"
) -> None:
    """将下载与解析得到的原始数据持久化保存为 raw 格式 (JSON 与 CSV) 并生成按 ID 合并的 JSON"""
    os.makedirs(raw_dir, exist_ok=True)
    
    # 1. 保存维基原始条目 JSON
    wiki_json_path = os.path.join(raw_dir, "wiki_games_raw.json")
    with open(wiki_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_records": len(raw_records),
            "records": raw_records
        }, f, ensure_ascii=False, indent=2)
    logger.info(f"已保存维基原始条目 JSON: {wiki_json_path} (共 {len(raw_records)} 条)")

    # 2. 保存维基原始条目 CSV 报表
    wiki_csv_path = os.path.join(raw_dir, "wiki_games_raw.csv")
    if raw_records:
        fieldnames = list(raw_records[0].keys())
        with open(wiki_csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in raw_records:
                writer.writerow(r)
        logger.info(f"已保存维基原始报表 CSV: {wiki_csv_path}")

    # 3. 保存按 ID 合并相同游戏的维基 JSON (wiki_games_merged.json)
    merged_dataset = merge_raw_records_by_id(raw_records)
    wiki_merged_json_path = os.path.join(raw_dir, "wiki_games_merged.json")
    with open(wiki_merged_json_path, "w", encoding="utf-8") as f:
        json.dump(merged_dataset, f, ensure_ascii=False, indent=2)
    logger.info(f"已保存按 ID 合并的维基游戏 JSON: {wiki_merged_json_path} (共 {merged_dataset['total_games']} 款游戏)")

    # 4. 保存 B 站原始分段章节 JSON
    save_bilibili_raw_data(bilibili_segments, raw_dir=raw_dir)


def save_bilibili_raw_data(
    bilibili_segments: List[Dict[str, Any]], 
    raw_dir: str = "data/raw"
) -> str:
    """持久化保存 B 站原始分段章节 JSON 到 data/raw/bilibili_segments_raw.json"""
    os.makedirs(raw_dir, exist_ok=True)
    bili_json_path = os.path.join(raw_dir, "bilibili_segments_raw.json")
    with open(bili_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_segments": len(bilibili_segments),
            "segments": bilibili_segments
        }, f, ensure_ascii=False, indent=2)
    logger.info(f"已保存 B 站原始分段 JSON: {bili_json_path} (共 {len(bilibili_segments)} 条)")
    return bili_json_path


def fetch_bilibili_raw_data(
    cache_dir: Optional[str] = "cache",
    raw_dir: str = "data/raw",
    refresh_season: bool = True
) -> List[Dict[str, Any]]:
    """仅增量抓取 B 站合集新视频与分段章节，保存到 cache 并更新持久化至 data/raw/bilibili_segments_raw.json"""
    bili_cache = os.path.join(cache_dir, "bilibili") if cache_dir else "cache/bilibili"
    archives = collect_bilibili_season_videos(cache_dir=bili_cache, refresh_season=refresh_season)
    segments = fetch_all_video_details(archives, cache_dir=bili_cache)
    save_bilibili_raw_data(segments, raw_dir=raw_dir)
    return segments


def load_raw_data(raw_dir: str = "data/raw") -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """从本地 data/raw 目录读取原始记录与 B 站分段"""
    wiki_json_path = os.path.join(raw_dir, "wiki_games_raw.json")
    bili_json_path = os.path.join(raw_dir, "bilibili_segments_raw.json")

    if not os.path.exists(wiki_json_path):
        raise FileNotFoundError(f"未找到维基原始数据: {wiki_json_path}，请先运行 --fetch-raw 获取原始数据")

    with open(wiki_json_path, "r", encoding="utf-8") as f:
        w_data = json.load(f)
        raw_records = w_data.get("records", w_data) if isinstance(w_data, dict) else w_data

    bilibili_segments = []
    if os.path.exists(bili_json_path):
        with open(bili_json_path, "r", encoding="utf-8") as f:
            b_data = json.load(f)
            bilibili_segments = b_data.get("segments", b_data) if isinstance(b_data, dict) else b_data

    return raw_records, bilibili_segments


def fetch_raw_data(
    cache_dir: Optional[str] = "cache",
    raw_dir: str = "data/raw",
    timeout: int = 30,
    force_refresh: bool = False
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """第一阶段：抓取与解析网络数据，并保存为标准 data/raw 格式"""
    session = create_resilient_session()
    all_raw_list: List[Dict[str, Any]] = []

    # 1. 抓取与解析 NES (欧美版)
    nes_cache = os.path.join(cache_dir, "nes.html") if cache_dir else None
    nes_html = fetch_html(FC_NES_WIKI_URLS["NES"]["url"], session=session, cache_path=nes_cache, timeout=timeout, force_refresh=force_refresh)
    nes_records = [g.to_dict() for g in parse_nes_page(nes_html)]
    all_raw_list.extend(nes_records)

    # 2. 抓取与解析 FDS (FC磁碟机)
    fds_cache = os.path.join(cache_dir, "fds.html") if cache_dir else None
    fds_html = fetch_html(FC_NES_WIKI_URLS["FDS"]["url"], session=session, cache_path=fds_cache, timeout=timeout, force_refresh=force_refresh)
    fds_records = [g.to_dict() for g in parse_fc_or_fds_page(fds_html, "FDS")]
    all_raw_list.extend(fds_records)

    # 3. 抓取与解析 FC (红白机卡带)
    fc_cache = os.path.join(cache_dir, "fc.html") if cache_dir else None
    fc_html = fetch_html(FC_NES_WIKI_URLS["FC"]["url"], session=session, cache_path=fc_cache, timeout=timeout, force_refresh=force_refresh)
    fc_records = [g.to_dict() for g in parse_fc_or_fds_page(fc_html, "FC")]
    all_raw_list.extend(fc_records)

    # 4. 抓取与解析 B 站合集视频分段
    segments = fetch_bilibili_raw_data(cache_dir=cache_dir, raw_dir=raw_dir, refresh_season=force_refresh)

    # 5. 持久化保存到 data/raw 目录
    save_raw_data(all_raw_list, segments, raw_dir=raw_dir)
    return all_raw_list, segments


def build_from_raw(
    raw_dir: str = "data/raw",
    output_dir: str = "data",
    yaml_adjust_path: str = "override.yaml",
    raw_records: Optional[List[Dict[str, Any]]] = None,
    bilibili_segments: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """第二阶段：纯从 raw 数据读取，根据用户自定义 override.yaml 生成全格式数据"""
    if raw_records is None or bilibili_segments is None:
        logger.info(f"正在从本地 Raw 目录读取原始数据: {raw_dir}")
        raw_records, bilibili_segments = load_raw_data(raw_dir=raw_dir)

    # 加载 No-Intro DAT 与 rom-name-cn 对照库
    logger.info("正在加载 No-Intro DAT 克隆组与 rom-name-cn 对照库...")
    helper = RomNameCnHelper(workspace_dir=".")

    # 同步生成并更新按 ID 合并相同游戏的维基 JSON (wiki_games_merged.json，含 rom-name-cn 权威匹配 title_cn)
    if raw_records:
        try:
            merged_dataset = merge_raw_records_by_id(raw_records, helper=helper)
            merged_json_path = os.path.join(raw_dir, "wiki_games_merged.json")
            with open(merged_json_path, "w", encoding="utf-8") as f:
                json.dump(merged_dataset, f, ensure_ascii=False, indent=2)
            logger.info(f"已同步生成按 ID 合并的 Raw 维基 JSON: {merged_json_path} (共 {merged_dataset['total_games']} 款游戏)")
        except Exception as e:
            logger.warning(f"生成 wiki_games_merged.json 失败: {e}")

    # 加载用户自定义调整配置中的游戏合并规则 (merge_games)
    adjust_config = load_adjustments_config(yaml_adjust_path)
    custom_merges = adjust_config.get("merge_games", [])

    # 执行深度多维合并
    logger.info(f"正在基于 DAT 克隆树、rom-name-cn 及自定义调整配置 ({yaml_adjust_path}) 对齐合并美版与日版游戏...")
    unified_games = merge_fc_nes_records(raw_records, helper, custom_merges=custom_merges)

    # 执行游戏属性调整 (应用用户自定义 override.yaml 中的 title_zh 等修改)
    logger.info(f"正在结合用户自定义调整配置 ({yaml_adjust_path}) 调整游戏属性...")
    apply_game_adjustments(unified_games, yaml_path=yaml_adjust_path)

    # 对齐挂载 B 站视频 (应用用户自定义 override.yaml)
    logger.info(f"正在结合用户自定义调整配置 ({yaml_adjust_path}) 对齐挂载 B 站视频章节...")
    video_stats = attach_bilibili_videos_to_games(
        unified_games, 
        segments=bilibili_segments,
        yaml_mapping_path=yaml_adjust_path
    )

    cross_region_games = [g for g in unified_games if g["is_cross_region"]]
    multi_platform_games = [g for g in unified_games if len(g["platforms"]) > 1]
    nes_only_games = [g for g in unified_games if g["platforms"] == ["NES"]]
    japan_only_games = [g for g in unified_games if "NES" not in g["platforms"]]

    # 按平台归集原始记录与统计
    raw_by_platform: Dict[str, List[Dict[str, Any]]] = {"NES": [], "FDS": [], "FC": []}
    for r in raw_records:
        plat = r.get("platform")
        if plat in raw_by_platform:
            raw_by_platform[plat].append(r)
        elif plat:
            raw_by_platform.setdefault(plat, []).append(r)

    raw_records_stat = {
        "NES": len(raw_by_platform.get("NES", [])),
        "FDS": len(raw_by_platform.get("FDS", [])),
        "FC": len(raw_by_platform.get("FC", [])),
        "total": len(raw_records)
    }

    dataset = {
        "metadata": {
            "title": "任天堂 NES 与红白机 (FC/FDS) 跨区整合数据库 (基于 Raw 原始数据与自定义 Adjustments)",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sources": {
                "wiki_urls": {k: v["url"] for k, v in FC_NES_WIKI_URLS.items()},
                "dat_files": [
                    "Nintendo - Nintendo Entertainment System (Headered) (20260806-082610).dat",
                    "Nintendo - Family Computer Disk System (FDS) (20260617-195332).dat"
                ],
                "submodules": ["rom-name-cn"],
                "bilibili_series_url": "https://space.bilibili.com/3546818172423070/lists/4877626",
                "adjustments_file": yaml_adjust_path
            },
            "statistics": {
                "total_unified_games": len(unified_games),
                "cross_region_games": len(cross_region_games),
                "multi_platform_games": len(multi_platform_games),
                "nes_exclusive_games": len(nes_only_games),
                "japan_exclusive_games": len(japan_only_games),
                "bilibili_videos_matched": video_stats.get("matched_games_count", 0),
                "raw_records_total": len(raw_records),
                "raw_records": raw_records_stat
            }
        },
        "games": unified_games,
        "cross_region_games": cross_region_games,
        "raw_by_platform": raw_by_platform
    }

    # 导出全套发布数据
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, "fc_nes_games.json")
    pickle_path = os.path.join(output_dir, "fc_nes_games.pkl")
    py_module_path = os.path.join(output_dir, "fc_nes_games.py")
    csv_path = os.path.join(output_dir, "fc_nes_games.csv")
    excel_path = os.path.join(output_dir, "fc_nes_games.xlsx")
    html_path = os.path.join(output_dir, "fc_nes_games.html")
    bili_match_path = os.path.join("temp", "bilibili_match.yaml")

    save_to_json(dataset, json_path)
    save_to_pickle(dataset, pickle_path)
    save_to_python_module(dataset, py_module_path)
    save_to_csv(dataset["games"], csv_path)
    save_to_excel(dataset, excel_path)
    save_to_html(dataset, html_path)
    save_to_bilibili_match_yaml(dataset["games"], bili_match_path)

    return dataset


def collect_fc_nes_games(
    cache_dir: Optional[str] = "cache",
    timeout: int = 30,
    force_refresh: bool = False,
    yaml_mapping_path: str = "override.yaml"
) -> Dict[str, Any]:
    """兼容旧接口：自动执行 Raw 抓取与发布构建"""
    raw_dir = "data/raw"
    raw_records, segments = fetch_raw_data(
        cache_dir=cache_dir,
        raw_dir=raw_dir,
        timeout=timeout,
        force_refresh=force_refresh
    )
    return build_from_raw(
        raw_dir=raw_dir,
        yaml_adjust_path=yaml_mapping_path,
        raw_records=raw_records,
        bilibili_segments=segments
    )


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
            "视频介绍 by 雷文" if v.get("url") else ""
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
    generate_fc_nes_html(output_file=filepath, dataset=data)
    logger.info(f"已保存 HTML 交互式前端页面: {filepath}")


def save_to_bilibili_match_yaml(games: List[Dict[str, Any]], filepath: str = "temp/bilibili_match.yaml") -> None:
    """保存成功匹配到 B 站解说视频的游戏 ID 与对应分段章节名称清单至 YAML 文件 (默认存放至 temp 目录)"""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

    match_dict: Dict[str, str] = OrderedDict()
    matched_games_count = 0

    for g in games:
        v = g.get("video")
        if not v or not v.get("chapter_name"):
            continue

        chapter_name = str(v["chapter_name"]).strip()
        matched_games_count += 1

        # 1. 记录游戏主 ID
        g_id = (g.get("id") or "").strip()
        if g_id and g_id not in match_dict:
            match_dict[g_id] = chapter_name

        # 2. 同步记录各版本（FC/FDS/NES 等）的原始条目 ID (如存在且不同)
        for ver in g.get("versions", {}).values():
            ver_id = (ver.get("id") or "").strip()
            if ver_id and ver_id not in match_dict:
                match_dict[ver_id] = chapter_name

    lines = [
        "# ==============================================================================",
        "# Bilibili 视频分段章节对齐清单 (temp/bilibili_match.yaml)",
        "# 自动生成于 build 构建阶段，记录所有成功匹配到 B 站解说视频的游戏 ID 与对应章节名称",
        f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"# 游戏总数: {matched_games_count} 款 (含各版本原始 ID 共 {len(match_dict)} 条规则)",
        "# ==============================================================================",
        ""
    ]
    for k, val in match_dict.items():
        k_str = json.dumps(k, ensure_ascii=False)
        val_str = json.dumps(val, ensure_ascii=False)
        lines.append(f"  {k_str}: {val_str}")

    content = "\n".join(lines) + "\n"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"已保存 B 站视频匹配清单 YAML: {filepath} (共 {len(match_dict)} 条规则)")


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
    assert "跨区属性</th>" not in html_content, "HTML 表格表头已移除跨区属性列"
    assert "平台</th>" not in html_content, "HTML 表格表头已移除平台列"
    
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
        
    # 验证外部 YAML 调整规则生效 (title_zh 修改与视频对齐)
    basic_game = next((g for g in games if g["id"] == "basic-family"), None)
    assert basic_game is not None, "未找到 basic-family 游戏条目"
    assert basic_game["title_zh"] == "家用BASIC语言", f"培基语音 title_zh 应通过 override.yaml 调整为家用BASIC语言，实为: {basic_game['title_zh']}"
    assert basic_game.get("video") is not None, "家用BASIC语言应匹配到解说视频"
    assert basic_game["video"]["chapter_name"] == "家用BASIC语言", f"匹配章节应为家用BASIC语言，实为: {basic_game['video']['chapter_name']}"

    basic_v3 = next((g for g in games if g["id"] == "family-basic-v3"), None)
    assert basic_v3 is not None, "未找到 family-basic-v3 游戏条目"
    assert basic_v3["title_zh"] == "家用BASIC语言V3", f"培基语音第三版 title_zh 应通过 override.yaml 调整为家用BASIC语言V3，实为: {basic_v3['title_zh']}"
    print(f"  [OK] 外部 YAML 调整验证: 《{basic_game['title_zh']}》与《{basic_v3['title_zh']}》的 title_zh 属性修改及视频绑定校验成功")
        
    # 验证 Raw 原始数据持久化文件
    raw_dir = "data/raw"
    wiki_raw_json = os.path.join(raw_dir, "wiki_games_raw.json")
    wiki_raw_csv = os.path.join(raw_dir, "wiki_games_raw.csv")
    bili_raw_json = os.path.join(raw_dir, "bilibili_segments_raw.json")
    assert os.path.exists(wiki_raw_json), "缺少 data/raw/wiki_games_raw.json 原始维基条目数据"
    assert os.path.exists(wiki_raw_csv), "缺少 data/raw/wiki_games_raw.csv 原始维基报表数据"
    assert os.path.exists(bili_raw_json), "缺少 data/raw/bilibili_segments_raw.json 原始分段数据"
    print("  [OK] Raw 原始数据持久化校验通过 (data/raw/*.json, *.csv)")
        
    assert "bili-btn" in html_content, "HTML 应包含 B 站视频按钮样式 bili-btn"
    assert "bili-card" in html_content, "HTML 应包含详情弹窗中的 B 站解说卡片 bili-card"
    assert "视频介绍 BY 雷文" in html_content, "HTML 应包含 '视频介绍 BY 雷文' 链接文本"
    print("  [OK] 前端页面 B 站视频按钮、'视频介绍 BY 雷文' 跳转按钮与弹窗卡片校验通过")
    
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
    """主程序入口：支持原始数据抓取(raw)、基于调整规则构建(build)、全格式导出及完整性断言校验"""
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
        "--raw-dir",
        default="data/raw",
        help="原始数据持久化目录 (默认: data/raw/)"
    )
    parser.add_argument(
        "--cache-dir",
        default="cache",
        help="网页与 API 缓存目录 (默认: cache/)"
    )
    parser.add_argument(
        "--override",
        default="override.yaml",
        help="用户可编辑的自定义调整规则 YAML 文件路径 (默认: override.yaml)"
    )
    parser.add_argument(
        "--fetch-raw",
        action="store_true",
        help="强制重新从网络抓取原始数据并保存为 raw 格式 (JSON/CSV)"
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="仅从本地 raw 数据和 override.yaml 生成全套发布数据"
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
        "--fetch-bilibili", "--fetch-bilibili-only",
        dest="fetch_bilibili",
        action="store_true",
        help="仅增量抓取 B 站合集新视频与分段章节并对齐发布 (跳过 Wiki 抓取)"
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

    # 3. 判断是否需要抓取 Raw 原始数据
    wiki_raw_file = os.path.join(args.raw_dir, "wiki_games_raw.json")
    bili_raw_file = os.path.join(args.raw_dir, "bilibili_segments_raw.json")
    raw_exists = os.path.exists(wiki_raw_file) and os.path.exists(bili_raw_file)

    raw_records = None
    segments = None

    if args.fetch_bilibili:
        print("=" * 65)
        print("【模式】仅增量抓取 B 站合集新视频与分段章节 (跳过 Wiki 抓取)...")
        print("=" * 65)
        segments = fetch_bilibili_raw_data(
            cache_dir=args.cache_dir,
            raw_dir=args.raw_dir,
            refresh_season=True
        )
        print(f"[OK] B 站视频分段原始数据已成功持久化至: {bili_raw_file} (共 {len(segments)} 条分段)")

        # 读取本地已有 Wiki raw 数据
        if not os.path.exists(wiki_raw_file):
            print(f"[错误] 未找到本地 Wiki 原始数据: {wiki_raw_file}，请先执行一次 python fetch_fc_nes.py --fetch-raw")
            return
        with open(wiki_raw_file, "r", encoding="utf-8") as f:
            w_data = json.load(f)
            raw_records = w_data.get("records", w_data) if isinstance(w_data, dict) else w_data
        print(f"[OK] 已成功加载本地 Wiki 原始数据: {len(raw_records)} 条记录")

    elif (args.fetch_raw or args.refresh or not raw_exists) and not args.build:
        print("=" * 65)
        print("【阶段一】开始从网络抓取原始数据并保存为 Raw 格式 (JSON/CSV)...")
        print("=" * 65)
        raw_records, segments = fetch_raw_data(
            cache_dir=args.cache_dir,
            raw_dir=args.raw_dir,
            timeout=args.timeout,
            force_refresh=args.refresh
        )
        print(f"[OK] Raw 原始数据已成功持久化至: {args.raw_dir}")

    # 5. 基于 Raw 原始数据与用户自定义 override.yaml 执行构建与全格式导出
    print("=" * 65)
    print(f"【阶段二】从 Raw 数据出发，结合调整配置 ({args.override}) 生成全格式数据...")
    print(" (融合 No-Intro DAT、rom-name-cn 与 B站编年史视频)")
    print("=" * 65)

    dataset = build_from_raw(
        raw_dir=args.raw_dir,
        output_dir=args.output_dir,
        yaml_adjust_path=args.override,
        raw_records=raw_records,
        bilibili_segments=segments
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
    html_path = os.path.join(out_dir, "fc_nes_games.html")
    bili_match_path = os.path.join("temp", "bilibili_match.yaml")

    print("\n所有 FC/NES 整合数据与前端页面已成功保存！")
    print(f"1. Raw 原始数据目录:  {args.raw_dir} (wiki_games_raw.json/csv, wiki_games_merged.json, bilibili_segments_raw.json)")
    print(f"2. JSON 数据结构:     {json_path}")
    print(f"3. Pickle 二进制对象: {pickle_path}")
    print(f"4. Python 代码模块:   {py_module_path} (可直接 import FC_NES_GAMES)")
    print(f"5. CSV 表格导出:      {csv_path} (含 B站视频时间轴)")
    print(f"6. Excel 格式文件:    {excel_path} (富样式、首行冻结、含超链接)")
    print(f"7. HTML 交互式前端:   {html_path} (自包含内嵌数据，含资源下载中心)")
    print(f"8. B站匹配清单 YAML:  {bili_match_path}")


if __name__ == "__main__":
    main()
