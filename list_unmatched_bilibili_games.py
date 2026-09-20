#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
列出 Bilibili 视频解说章节中未被游戏库匹配的游戏名称

本程序从 B 站合集分段数据中提取所有游戏章节名，
结合当前游戏数据库 (data/fc_nes_games.json) 以及 override.yaml 调整配置与别名库，
利用项目的对齐匹配引擎 (BilibiliMatcher)，筛选出尚未对齐到任何 FC / NES / FDS 游戏的 B 站游戏名称，
并导出为干净的纯文本 (.txt) 文档。
"""

import os
import sys
import json
import argparse
from typing import List, Dict, Any, Optional, Tuple

# 确保 Windows 终端环境支持 UTF-8 输出
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# 确保能够正确导入项目同级模块
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

try:
    from fetch_fc_nes import BilibiliMatcher
except ImportError as e:
    BilibiliMatcher = None


def find_file(custom_path: Optional[str], candidate_paths: List[str], desc: str) -> str:
    """按候选路径查找文件"""
    if custom_path:
        if os.path.exists(custom_path):
            return custom_path
        raise FileNotFoundError(f"指定的{desc}不存在: {custom_path}")

    for path in candidate_paths:
        abs_p = os.path.abspath(path)
        if os.path.exists(abs_p):
            return abs_p

    joined_paths = "\n  - ".join(candidate_paths)
    raise FileNotFoundError(
        f"未找到{desc}，已尝试候选路径:\n  - {joined_paths}\n"
        f"请先运行 'python fetch_fc_nes.py' 生成必要数据！"
    )


def load_bilibili_segments(segments_path: str) -> List[Dict[str, Any]]:
    """加载 Bilibili 视频分段章节列表"""
    with open(segments_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "segments" in data:
        return data["segments"]
    elif isinstance(data, list):
        return data
    else:
        raise ValueError(f"B站分段数据文件格式异常: {segments_path}")


def load_games_data(games_path: str) -> List[Dict[str, Any]]:
    """加载游戏库数据"""
    with open(games_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "games" in data:
        return data["games"]
    elif isinstance(data, list):
        return data
    else:
        raise ValueError(f"游戏库数据文件格式异常: {games_path}")


def find_unmatched_bilibili_games(
    segments: List[Dict[str, Any]],
    games: List[Dict[str, Any]],
    yaml_mapping_path: str = "override.yaml",
    alias_json_path: str = "rom-name-cn/name_alias(Chinese).json"
) -> Tuple[List[str], List[Dict[str, Any]], int]:
    """
    使用项目的匹配引擎对全部 B 站分段进行对齐检测，
    返回:
      1. 去重后的未匹配游戏名列表 (保持原出现顺序)
      2. 完整的未匹配分段对象列表 (包含视频标题、时间戳、链接等详细信息)
      3. 成功匹配的分段总数
    """
    if BilibiliMatcher is None:
        raise RuntimeError("未能导入 fetch_fc_nes.BilibiliMatcher 匹配引擎，请确认 fetch_fc_nes.py 处于当前工作目录")

    matcher = BilibiliMatcher(
        games=games,
        alias_json_path=alias_json_path,
        yaml_mapping_path=yaml_mapping_path
    )

    unmatched_segments = []
    matched_count = 0
    seen_names = set()
    unmatched_unique_names = []

    for seg in segments:
        hit = matcher.match_segment(seg)
        if hit:
            matched_count += 1
        else:
            unmatched_segments.append(seg)
            cname = seg.get("chapter_name", "").strip()
            if cname and cname not in seen_names:
                seen_names.add(cname)
                unmatched_unique_names.append(cname)

    return unmatched_unique_names, unmatched_segments, matched_count


def export_unmatched_to_txt(
    names: List[str],
    unmatched_segments: List[Dict[str, Any]],
    output_path: str,
    with_info: bool = False
):
    """导出未匹配的游戏名到纯文本 TXT 文档"""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        if not with_info:
            # 纯游戏名模式：每行一个，简洁干净
            for name in names:
                f.write(f"{name}\n")
        else:
            # 详细信息模式：包含游戏名、年份、视频分集、时间戳、在线链接
            f.write("# Bilibili 未匹配游戏名详细清单 (制表符分隔)\n")
            f.write("# 游戏名称\t年份\t时间点\t视频标题\t在线跳转地址\n")
            for seg in unmatched_segments:
                gname = seg.get("chapter_name", "")
                year = seg.get("video_year") or "-"
                ts = seg.get("timestamp") or "-"
                title = seg.get("video_title") or "-"
                url = seg.get("url") or "-"
                f.write(f"{gname}\t{year}\t{ts}\t{title}\t{url}\n")


def main():
    parser = argparse.ArgumentParser(
        description="列出 Bilibili 获取游戏名中没有被匹配的游戏名并输出为 TXT 文档",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例用法:
  python list_unmatched_bilibili_games.py                  # 默认直接生成 temp/bilibili_unmatched_games.txt
  python list_unmatched_bilibili_games.py -o custom.txt    # 导出为 temp/custom.txt
  python list_unmatched_bilibili_games.py -p               # 在终端同时打印未匹配游戏名列表
  python list_unmatched_bilibili_games.py --with-info      # 输出包含视频期数、时间戳与链接的详细 txt
  python list_unmatched_bilibili_games.py -s alpha         # 按首字母/拼音字母排序后输出
  python list_unmatched_bilibili_games.py -c               # 仅显示统计数量
"""
    )

    parser.add_argument(
        "-o", "--output",
        default=os.path.join("temp", "bilibili_unmatched_games.txt"),
        help="导出的 txt 文档路径（默认为 'temp/bilibili_unmatched_games.txt'）"
    )
    parser.add_argument(
        "-s", "--sort",
        choices=["time", "alpha"],
        default="time",
        help="排序方式: time(默认按视频时间线先后原序), alpha(按名称拼音字母排序)"
    )
    parser.add_argument(
        "--with-info",
        action="store_true",
        help="在 txt 文档中包含时间戳、视频标题和播放链接等详细定位信息"
    )
    parser.add_argument(
        "-p", "--print",
        dest="print_console",
        action="store_true",
        help="在控制台终端打印未匹配游戏名"
    )
    parser.add_argument(
        "-c", "--count",
        action="store_true",
        help="仅显示未匹配与匹配统计数量，不写出文件"
    )
    parser.add_argument(
        "--segments",
        help="指定 Bilibili 分段数据文件路径（默认自动查找 data/raw 或 cache/bilibili）"
    )
    parser.add_argument(
        "--games",
        help="指定游戏库数据 json 文件路径（默认自动查找 data/fc_nes_games.json）"
    )
    parser.add_argument(
        "--override",
        dest="override",
        default="override.yaml",
        help="指定调整规则配置文件路径（默认为 override.yaml）"
    )

    args = parser.parse_args()

    # 1. 查找并加载输入文件
    try:
        segments_path = find_file(
            args.segments,
            [
                os.path.join(CURRENT_DIR, "data", "raw", "bilibili_segments_raw.json"),
                os.path.join(CURRENT_DIR, "cache", "bilibili", "bilibili_segments.json"),
                os.path.join(os.getcwd(), "data", "raw", "bilibili_segments_raw.json"),
                os.path.join(os.getcwd(), "cache", "bilibili", "bilibili_segments.json"),
            ],
            "Bilibili 视频分段数据文件"
        )
        games_path = find_file(
            args.games,
            [
                os.path.join(CURRENT_DIR, "data", "fc_nes_games.json"),
                os.path.join(os.getcwd(), "data", "fc_nes_games.json"),
            ],
            "游戏库数据文件 (data/fc_nes_games.json)"
        )

        segments = load_bilibili_segments(segments_path)
        games = load_games_data(games_path)
    except Exception as e:
        print(f"读取数据失败: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. 执行匹配分析
    adj_path = args.override
    if not os.path.exists(adj_path):
        for cand in ["override.yaml", "adjustments.yaml", "adjust.yaml"]:
            if os.path.exists(cand):
                adj_path = cand
                break
    adj_path = os.path.abspath(adj_path) if os.path.exists(adj_path) else "override.yaml"
    alias_path = os.path.join(CURRENT_DIR, "rom-name-cn", "name_alias(Chinese).json")
    if not os.path.exists(alias_path):
        alias_path = "rom-name-cn/name_alias(Chinese).json"

    unmatched_names, unmatched_segments, matched_count = find_unmatched_bilibili_games(
        segments=segments,
        games=games,
        yaml_mapping_path=adj_path,
        alias_json_path=alias_path
    )

    total_segments = len(segments)
    unmatched_count = len(unmatched_names)
    unmatched_rate = (unmatched_count / total_segments * 100) if total_segments > 0 else 0

    # 3. 排序处理
    if args.sort == "alpha":
        unmatched_names.sort(key=lambda x: x.lower())
        unmatched_segments.sort(key=lambda s: s.get("chapter_name", "").lower())

    # 4. 仅统计模式
    if args.count:
        print("=" * 60)
        print(" Bilibili 视频游戏名匹配统计")
        print("=" * 60)
        print(f"• B 站分段章节总数:   {total_segments} 个")
        print(f"• 成功匹配游戏数:     {matched_count} 个 (覆盖率: {matched_count / total_segments * 100:.1f}%)")
        print(f"• 未被匹配游戏名数:   {unmatched_count} 个 (未匹配率: {unmatched_rate:.1f}%)")
        print("=" * 60)
        return

    # 5. 终端打印模式
    if args.print_console:
        print("=" * 60)
        print(f" 未匹配的 Bilibili 游戏名列表 (共 {unmatched_count} 个):")
        print("=" * 60)
        for idx, name in enumerate(unmatched_names, start=1):
            print(f"{idx:>4}. {name}")
        print("=" * 60)

    # 6. 导出为 TXT 文档
    try:
        out_path = args.output
        if not os.path.dirname(out_path):
            out_path = os.path.join("temp", out_path)

        export_unmatched_to_txt(
            names=unmatched_names,
            unmatched_segments=unmatched_segments,
            output_path=out_path,
            with_info=args.with_info
        )
        print(f"成功导出 {unmatched_count} 个未匹配的 Bilibili 游戏名至 txt 文档:")
        print(f"  --> {os.path.abspath(out_path)}")
        print(f"（B 站总章节: {total_segments}，已匹配: {matched_count}，未匹配: {unmatched_count}，占比: {unmatched_rate:.1f}%）")
    except Exception as e:
        print(f"导出 txt 文档失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
