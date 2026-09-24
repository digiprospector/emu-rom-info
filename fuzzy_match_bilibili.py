#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
基于时序邻域锚点与文本模糊匹配的 Bilibili 视频章节对齐工具

【原理说明】
雷文的 FC / NES 终极鉴赏系列视频分段是严格按照游戏发售时间编年史顺序推进的，
这与 Wiki / 项目游戏数据库中的游戏排序高度吻合。

当某款游戏（如 "best-play-pro-yakyuu" / "亚斯基职业棒球"）因译名、厂商音译或用词差异
未被现有匹配规则直接命中时，我们可以利用其时序邻近的游戏作为锚点（Anchor）：
1. 查找该游戏前后各 N 款（默认 5 款）游戏中已成功匹配到 B 站视频的锚点游戏；
2. 锚点游戏在 B 站视频分段中对应一个局部区间 [seg_min, seg_max]；
3. 在此局部区间内，未匹配的 B 站分段数量极少（通常仅 1~5 个）；
4. 结合文本相似度算法（最长公共汉字子串、字符重合度、序列相似度等），
   若名字中有大部分字相同，即可实现高精度的模糊对齐。

【产物输出】
自动在 temp/ 目录下生成独立的 YAML 文件（如 temp/fuzzy_match_result.yaml），
其格式与 override.yaml 的 video_mappings 规则完全兼容，方便直接采纳与合并。
"""

import os
import sys
import json
import re
import difflib
import argparse
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional, Set

# 确保 Windows 终端环境支持 UTF-8 输出
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# 常见厂商中英文音译对照表（辅助增强匹配）
COMPANY_ALIASES = {
    "ascii": ["亚斯基", "阿斯奇", "阿斯基", "ascii"],
    "konami": ["科乐美", "柯纳米", "konami"],
    "namco": ["南梦宫", "南梦哥", "namco"],
    "capcom": ["卡普空", "嘉普空", "capcom"],
    "taito": ["太东", "taito"],
    "hudson": ["哈德森", "哈得森", "哈德逊", "hudson", "hudson soft"],
    "bandai": ["万代", "万普", "bandai"],
    "enix": ["艾尼克斯", "enix"],
    "square": ["史克威尔", "square"],
    "irem": ["艾力姆", "irem"],
    "jaleco": ["贾雷克", "扎莱克", "佳丽宝", "jaleco"],
    "sunsoft": ["太阳电子", "桑软", "sunsoft"],
    "snk": ["新日本企划", "snk"],
    "technos": ["特库摩", "特克诺斯", "technos"],
    "tecmo": ["特库摩", "特克摩", "tecmo"],
    "toei": ["东映", "toei"],
    "toho": ["东宝", "toho"],
}


def clean_text(s: str) -> str:
    """清理字符串中的特殊字符，保留中文字符、英文字母和数字"""
    if not s:
        return ""
    return re.sub(r'[\s\-_:：·/／、~～（）\(\)\[\]【】\.\'\"!?！？＋+]+', '', str(s)).strip()


def get_chinese_chars(s: str) -> str:
    """提取字符串中的所有汉字"""
    if not s:
        return ""
    return "".join(re.findall(r'[\u4e00-\u9fa5]', str(s)))


def longest_common_substring(s1: str, s2: str) -> str:
    """计算两个字符串的最长连续公共子串"""
    m, n = len(s1), len(s2)
    if m == 0 or n == 0:
        return ""
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    max_len = 0
    end_idx = 0
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
                if dp[i][j] > max_len:
                    max_len = dp[i][j]
                    end_idx = i
            else:
                dp[i][j] = 0
    return s1[end_idx - max_len:end_idx]


def split_sub_names(name: str) -> List[str]:
    """拆解复合标题中的各个子名称候选（如副标题、多版本、斜杠分割等）"""
    candidates = [name]
    for sep in ['/', '／', '、', ' - ', '——', '：', ':']:
        if sep in name:
            for part in name.split(sep):
                p = part.strip()
                if len(p) >= 2 and p not in candidates:
                    candidates.append(p)
    return candidates


def calculate_name_similarity(name1: str, name2: str) -> Tuple[float, str]:
    """
    计算两个游戏名称之间的模糊相似度得分与判决理由
    得分范围: 0.0 ~ 1.0
    """
    c1 = clean_text(name1)
    c2 = clean_text(name2)
    if not c1 or not c2:
        return 0.0, ""

    # 1. 忽略大小写完全一致
    if c1.lower() == c2.lower():
        return 1.0, "名称完全一致"

    zh1 = get_chinese_chars(name1)
    zh2 = get_chinese_chars(name2)

    lcs_zh = longest_common_substring(zh1, zh2) if (zh1 and zh2) else ""
    lcs_len = len(lcs_zh)
    min_zh_len = min(len(zh1), len(zh2)) if (zh1 and zh2) else 0

    set1 = set(zh1)
    set2 = set(zh2)
    common_chars = set1.intersection(set2)
    min_set_len = min(len(set1), len(set2)) if (set1 and set2) else 0
    char_overlap_ratio = (len(common_chars) / min_set_len) if min_set_len > 0 else 0.0

    seq_ratio = difflib.SequenceMatcher(None, c1.lower(), c2.lower()).ratio()
    zh_cov = (lcs_len / min_zh_len) if min_zh_len > 0 else 0.0

    score = 0.0
    reasons = []

    # 规则 A: 最长连续汉字子串命中且覆盖率较高（如 "职业棒球" 覆盖 100%）
    if lcs_len >= 3 and zh_cov >= 0.5:
        base_score = 0.6 + zh_cov * 0.35
        if base_score > score:
            score = base_score
            reasons.append(f"连续汉字'{lcs_zh}'(覆盖率{zh_cov:.1%})")
    elif lcs_len >= 4:
        base_score = 0.75 + min(lcs_len * 0.03, 0.2)
        if base_score > score:
            score = base_score
            reasons.append(f"长连续汉字'{lcs_zh}'")

    # 规则 B: 汉字重合集合比例高（大部分字相同）
    if char_overlap_ratio >= 0.6 and len(common_chars) >= 3:
        base_score = 0.5 + char_overlap_ratio * 0.35
        if base_score > score:
            score = base_score
            overlap_str = "".join(sorted(common_chars))
            reasons.append(f"汉字大部分相同'{overlap_str}'({char_overlap_ratio:.1%})")

    # 规则 C: 序列比对相似度
    if seq_ratio >= 0.55:
        if seq_ratio > score:
            score = seq_ratio
            reasons.append(f"文本序列相似度{seq_ratio:.1%}")

    # 规则 D: 厂商音译替换辅助匹配
    c1_lower = c1.lower()
    c2_lower = c2.lower()
    for _, aliases in COMPANY_ALIASES.items():
        found_in_1 = [a for a in aliases if a in c1_lower]
        found_in_2 = [a for a in aliases if a in c2_lower]
        if found_in_1 and found_in_2 and found_in_1[0] != found_in_2[0]:
            # 存在跨中英/音译的厂商匹配，增加额外置信度
            score = min(1.0, score + 0.15)
            reasons.append(f"厂商对应({found_in_1[0]}<->{found_in_2[0]})")
            break

    # 规则 E: 拆分子候选词单独匹配（如 "小麻烦千惠 浪花爆破娘" 中的子项）
    sub_parts1 = split_sub_names(name1)
    sub_parts2 = split_sub_names(name2)
    if len(sub_parts1) > 1 or len(sub_parts2) > 1:
        for p1 in sub_parts1:
            for p2 in sub_parts2:
                if p1 == name1 and p2 == name2:
                    continue
                pz1 = get_chinese_chars(p1)
                pz2 = get_chinese_chars(p2)
                if pz1 and pz2:
                    sub_lcs = longest_common_substring(pz1, pz2)
                    sub_min = min(len(pz1), len(pz2))
                    if len(sub_lcs) >= 3 and len(sub_lcs) / sub_min >= 0.6:
                        sub_score = 0.65 + (len(sub_lcs) / sub_min) * 0.25
                        if sub_score > score:
                            score = sub_score
                            reasons.append(f"子项'{p1}'与'{p2}'命中'{sub_lcs}'")

    score = min(1.0, score)
    return score, "; ".join(reasons)


class NeighborFuzzyMatcher:
    """
    基于时序邻域锚点的模糊匹配器
    """
    def __init__(
        self,
        games: List[Dict[str, Any]],
        segments: List[Dict[str, Any]],
        window: int = 5,
        threshold: float = 0.5
    ):
        self.games = games
        self.segments = segments
        self.window = window
        self.threshold = threshold

        # 建立 Segment 的索引表: url -> idx, (bvid, timestamp) -> idx
        self.seg_url_to_idx: Dict[str, int] = {}
        self.seg_bt_to_idx: Dict[Tuple[str, str], int] = {}
        for idx, s in enumerate(self.segments):
            url = s.get("url")
            if url:
                self.seg_url_to_idx[url] = idx
                self.seg_url_to_idx[url.rstrip("/")] = idx
            bvid = s.get("bvid")
            ts = s.get("timestamp")
            if bvid and ts:
                self.seg_bt_to_idx[(bvid, ts)] = idx

        # 统计已有匹配
        self.game_to_seg: Dict[int, int] = {}
        self.seg_to_game: Dict[int, List[int]] = {}

        for g_idx, g in enumerate(self.games):
            v = g.get("video")
            if v and isinstance(v, dict):
                url = v.get("url")
                bvid = v.get("bvid")
                ts = v.get("timestamp")
                s_idx = (
                    self.seg_url_to_idx.get(url)
                    or self.seg_url_to_idx.get(url.rstrip("/") if url else "")
                    or self.seg_bt_to_idx.get((bvid, ts))
                )
                if s_idx is not None:
                    self.game_to_seg[g_idx] = s_idx
                    if s_idx not in self.seg_to_game:
                        self.seg_to_game[s_idx] = []
                    self.seg_to_game[s_idx].append(g_idx)

    def extract_game_names(self, game: Dict[str, Any]) -> List[str]:
        """提取游戏的所有可能名称候选"""
        names: List[str] = []
        
        def add(name: Optional[str]):
            if name:
                s = str(name).strip()
                if s and s not in names:
                    names.append(s)

        add(game.get("title_zh"))
        add(game.get("title_cn"))
        for v in game.get("versions", {}).values():
            add(v.get("title_zh"))
            add(v.get("title_cn"))

        # 加入厂商+中文名称组合，例如 "ASCII" + "最佳职业棒球"
        publishers = game.get("publishers", [])
        title_zh = game.get("title_zh")
        if title_zh:
            for pub in publishers:
                if pub and isinstance(pub, str):
                    add(f"{pub} {title_zh}")
                    add(f"{pub}{title_zh}")

        return names

    def find_match_for_game(self, g_idx: int) -> Optional[Dict[str, Any]]:
        """为单个未匹配的游戏在邻域窗口内寻找最匹配的 B 站分段"""
        game = self.games[g_idx]
        if g_idx in self.game_to_seg:
            return None  # 自身已匹配

        # 1. 寻找前向锚点（最多向前查找 window 款游戏）
        left_anchor_g_idx = None
        left_anchor_seg_idx = None
        left_dist = None
        for step in range(1, self.window + 1):
            prev_idx = g_idx - step
            if prev_idx >= 0 and prev_idx in self.game_to_seg:
                left_anchor_g_idx = prev_idx
                left_anchor_seg_idx = self.game_to_seg[prev_idx]
                left_dist = step
                break

        # 2. 寻找后向锚点（最多向后查找 window 款游戏）
        right_anchor_g_idx = None
        right_anchor_seg_idx = None
        right_dist = None
        for step in range(1, self.window + 1):
            next_idx = g_idx + step
            if next_idx < len(self.games) and next_idx in self.game_to_seg:
                right_anchor_g_idx = next_idx
                right_anchor_seg_idx = self.game_to_seg[next_idx]
                right_dist = step
                break

        # 无法定锚则跳过
        if left_anchor_seg_idx is None and right_anchor_seg_idx is None:
            return None

        # 3. 确定分段候选区间 [seg_start, seg_end]
        buffer_size = 1
        if left_anchor_seg_idx is not None and right_anchor_seg_idx is not None:
            min_s = min(left_anchor_seg_idx, right_anchor_seg_idx)
            max_s = max(left_anchor_seg_idx, right_anchor_seg_idx)
            seg_start = max(0, min_s - buffer_size)
            seg_end = min(len(self.segments) - 1, max_s + buffer_size)
        elif left_anchor_seg_idx is not None:
            seg_start = max(0, left_anchor_seg_idx - buffer_size)
            seg_end = min(len(self.segments) - 1, left_anchor_seg_idx + self.window + buffer_size)
        else:
            seg_start = max(0, right_anchor_seg_idx - self.window - buffer_size)
            seg_end = min(len(self.segments) - 1, right_anchor_seg_idx + buffer_size)

        # 4. 在候选区间中执行文本模糊匹配
        game_names = self.extract_game_names(game)
        if not game_names:
            return None

        best_score = 0.0
        best_seg_idx = None
        best_seg = None
        best_reason = ""
        best_matched_gname = ""

        # 优先选择未被占用的分段
        for s_idx in range(seg_start, seg_end + 1):
            seg = self.segments[s_idx]
            chap_name = seg.get("chapter_name", "")
            if not chap_name:
                continue

            for gname in game_names:
                score, reason = calculate_name_similarity(gname, chap_name)
                # 未被占用的分段具有更高的自然优势
                is_unoccupied = s_idx not in self.seg_to_game
                adjusted_score = score + (0.02 if is_unoccupied else 0.0)

                if adjusted_score > best_score:
                    best_score = adjusted_score
                    best_seg_idx = s_idx
                    best_seg = seg
                    best_reason = reason
                    best_matched_gname = gname

        if best_seg is not None and (best_score >= self.threshold):
            # 整理锚点描述
            left_desc = None
            if left_anchor_g_idx is not None:
                l_game = self.games[left_anchor_g_idx]
                l_seg = self.segments[left_anchor_seg_idx]
                left_desc = f"{l_game.get('title_zh') or l_game.get('id')} ({l_seg.get('chapter_name')}) [前{left_dist}款]"

            right_desc = None
            if right_anchor_g_idx is not None:
                r_game = self.games[right_anchor_g_idx]
                r_seg = self.segments[right_anchor_seg_idx]
                right_desc = f"{r_game.get('title_zh') or r_game.get('id')} ({r_seg.get('chapter_name')}) [后{right_dist}款]"

            is_already_matched = best_seg_idx in self.seg_to_game
            conflict_games = []
            if is_already_matched:
                for cg_idx in self.seg_to_game[best_seg_idx]:
                    cg = self.games[cg_idx]
                    conflict_games.append(f"{cg.get('id')} ({cg.get('title_zh')})")

            return {
                "game_id": game["id"],
                "game_name": best_matched_gname,
                "game_title_zh": game.get("title_zh") or "",
                "game_index": g_idx,
                "seg_index": best_seg_idx,
                "chapter_name": best_seg.get("chapter_name", ""),
                "score": round(min(1.0, best_score), 3),
                "reason": best_reason,
                "is_unoccupied": not is_already_matched,
                "conflict_with": conflict_games,
                "anchor_left": left_desc,
                "anchor_right": right_desc,
                "video_title": best_seg.get("video_title", ""),
                "timestamp": best_seg.get("timestamp", ""),
                "bvid": best_seg.get("bvid", ""),
                "url": best_seg.get("url", "")
            }

        return None

    def run(self, include_occupied: bool = True) -> List[Dict[str, Any]]:
        """执行全局时序邻域模糊匹配"""
        matches = []
        for g_idx in range(len(self.games)):
            hit = self.find_match_for_game(g_idx)
            if hit:
                if not include_occupied and not hit["is_unoccupied"]:
                    continue
                matches.append(hit)
        return matches


def export_to_yaml(
    matches: List[Dict[str, Any]],
    output_path: str,
    window: int,
    threshold: float
):
    """
    将匹配结果导出为易读且直接兼容 override.yaml 的 YAML 格式
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# ==============================================================================\n")
        f.write("# Bilibili 视频章节时序邻域模糊匹配结果建议清单\n")
        f.write(f"# 生成时间: {now_str}\n")
        f.write(f"# 邻域窗口大小: 前后 {window} 款游戏 | 相似度阈值: {threshold:.0%}\n")
        f.write(f"# 匹配成功总计: {len(matches)} 款游戏\n")
        f.write("#\n")
        f.write("# 【使用说明】\n")
        f.write("# 本文件的 video_mappings 配置项格式与 override.yaml 完全一致。\n")
        f.write("# 您可直接复制下方的条目粘贴至 override.yaml 的 video_mappings 区块中生效！\n")
        f.write("# ==============================================================================\n\n")

        f.write("video_mappings:\n")

        for m in matches:
            gid = m["game_id"]
            chap = m["chapter_name"]
            score = m["score"]
            gname = m["game_title_zh"]
            left = m["anchor_left"] or "无"
            right = m["anchor_right"] or "无"
            ts = m["timestamp"]
            url = m["url"]

            conflict_info = f" | 原占用: [{', '.join(m['conflict_with'])}]" if not m["is_unoccupied"] and m["conflict_with"] else ""

            comment = (
                f"相似度: {score:.1%} | Wiki中文: {gname}{conflict_info} | "
                f"前锚点: {left} | 后锚点: {right} | 视频: {ts} {url}"
            )
            f.write(f'  # {comment}\n')
            f.write(f'  "{gid}": "{chap}"\n')


def find_default_file(candidates: List[str], desc: str) -> str:
    """寻找默认候选文件"""
    for p in candidates:
        abs_p = os.path.abspath(p)
        if os.path.exists(abs_p):
            return abs_p
    raise FileNotFoundError(f"未找到{desc}，已尝试候选路径: {candidates}")


def main():
    parser = argparse.ArgumentParser(
        description="基于时序邻域锚点与文本模糊匹配，对齐 Wiki 游戏库与 Bilibili 视频章节"
    )
    parser.add_argument(
        "-g", "--games",
        default=None,
        help="游戏数据文件路径 (默认: data/fc_nes_games.json)"
    )
    parser.add_argument(
        "-s", "--segments",
        default=None,
        help="Bilibili 视频分段原始数据文件路径 (默认: data/raw/bilibili_segments_raw.json)"
    )
    parser.add_argument(
        "-w", "--window",
        type=int,
        default=5,
        help="时序邻近锚点搜索窗口大小 (上一个和下一个游戏数量，默认: 5)"
    )
    parser.add_argument(
        "-t", "--threshold",
        type=float,
        default=0.5,
        help="文本模糊相似度判定阈值 (默认: 0.5)"
    )
    parser.add_argument(
        "-o", "--output",
        default="temp/fuzzy_match_result.yaml",
        help="结果输出 YAML 文件路径 (默认: temp/fuzzy_match_result.yaml)"
    )
    parser.add_argument(
        "--unoccupied-only",
        action="store_true",
        help="仅导出未被其他游戏占用的分段结果"
    )

    args = parser.parse_args()

    # 1. 定位数据文件
    games_file = args.games or find_default_file(
        [
            os.path.join("data", "fc_nes_games.json"),
            os.path.join(os.path.dirname(__file__), "data", "fc_nes_games.json"),
        ],
        "游戏数据文件"
    )

    segments_file = args.segments or find_default_file(
        [
            os.path.join("data", "raw", "bilibili_segments_raw.json"),
            os.path.join(os.path.dirname(__file__), "data", "raw", "bilibili_segments_raw.json"),
        ],
        "B站视频分段文件"
    )

    print(f"正在加载游戏数据: {games_file}")
    with open(games_file, "r", encoding="utf-8") as f:
        gdata = json.load(f)
    games = gdata["games"] if isinstance(gdata, dict) and "games" in gdata else gdata

    print(f"正在加载B站视频分段: {segments_file}")
    with open(segments_file, "r", encoding="utf-8") as f:
        sdata = json.load(f)
    segments = sdata["segments"] if isinstance(sdata, dict) and "segments" in sdata else sdata

    print(f"载入游戏: {len(games)} 款 | 载入B站分段: {len(segments)} 条")
    print(f"运行参数: 邻域窗口={args.window} | 相似度阈值={args.threshold:.0%} | 输出={args.output}")

    # 2. 执行匹配
    matcher = NeighborFuzzyMatcher(
        games=games,
        segments=segments,
        window=args.window,
        threshold=args.threshold
    )

    matches = matcher.run(include_occupied=not args.unoccupied_only)

    unoccupied_count = sum(1 for m in matches if m["is_unoccupied"])
    occupied_count = len(matches) - unoccupied_count

    print(f"\n匹配完成！共挖掘出 {len(matches)} 个模糊匹配候选:")
    print(f"  - 独占未匹配分段: {unoccupied_count} 条 (高置信度)")
    print(f"  - 已匹配分段关联: {occupied_count} 条 (需人工复核)")

    # 3. 控制台打印前 15 条匹配示范
    print("\n--- 匹配结果预览 (前 15 条) ---")
    for idx, m in enumerate(matches[:15], 1):
        status_tag = "【独占】" if m["is_unoccupied"] else "【冲突/复用】"
        print(
            f"{idx:2d}. {status_tag} {m['game_id']} ('{m['game_title_zh']}') "
            f"-> '{m['chapter_name']}' (相似度: {m['score']:.1%})"
        )
        print(f"    理由: {m['reason']}")
        if m["anchor_left"]:
            print(f"    前向锚点: {m['anchor_left']}")
        if m["anchor_right"]:
            print(f"    后向锚点: {m['anchor_right']}")

    # 4. 导出 YAML 文件
    export_to_yaml(
        matches=matches,
        output_path=args.output,
        window=args.window,
        threshold=args.threshold
    )

    print(f"\n结果已成功保存至 YAML 文件: {os.path.abspath(args.output)}")
    print("您可以查阅该文件，并按需将满意的条目复制合并到 override.yaml 中的 video_mappings 配置块！\n")


if __name__ == "__main__":
    main()
