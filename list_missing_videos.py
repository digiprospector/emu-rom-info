#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
列出全部缺少视频介绍的 FC / NES / FDS 游戏名称

本程序从项目导出的数据文件 (data/fc_nes_games.json) 中筛选出未匹配 B 站解说视频的游戏，
支持终端详细表格、纯名称列表、多语言名称切换、平台筛选及导出功能。
"""

import os
import sys
import json
import csv
import re
import argparse
from typing import List, Dict, Any, Optional

# 确保 Windows 终端环境支持 UTF-8 输出
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


def find_data_file(custom_path: Optional[str] = None) -> str:
    """寻找可用的游戏数据文件路径"""
    if custom_path:
        if os.path.exists(custom_path):
            return custom_path
        else:
            raise FileNotFoundError(f"指定的数据文件不存在: {custom_path}")

    # 默认候选路径
    candidates = [
        os.path.join(os.path.dirname(__file__), "data", "fc_nes_games.json"),
        os.path.join(os.getcwd(), "data", "fc_nes_games.json"),
    ]

    for path in candidates:
        if os.path.exists(path):
            return path

    raise FileNotFoundError(
        "未找到游戏数据文件 'data/fc_nes_games.json'。\n"
        "请先运行 'python fetch_fc_nes.py' 生成完整数据！"
    )


def load_games(data_path: str) -> List[Dict[str, Any]]:
    """加载游戏数据并返回游戏列表"""
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "games" in data:
        return data["games"]
    elif isinstance(data, list):
        return data
    else:
        raise ValueError("数据文件格式无法解析为游戏列表")


def filter_missing_video_games(
    games: List[Dict[str, Any]],
    platform: Optional[str] = None
) -> List[Dict[str, Any]]:
    """筛选出没有视频介绍的游戏，并支持平台过滤"""
    result = []
    platform_upper = platform.upper() if platform else None

    for game in games:
        # 判断是否存在视频介绍
        video = game.get("video")
        has_video = bool(video and isinstance(video, dict) and video.get("bvid"))

        if not has_video:
            if platform_upper:
                platforms = [p.upper() for p in game.get("platforms", [])]
                if platform_upper not in platforms:
                    continue
            result.append(game)

    return result


def get_game_display_name(game: Dict[str, Any], lang: str = "zh") -> str:
    """根据语言参数获取游戏显示名称"""
    zh = (game.get("title_zh") or "").strip()
    en = (game.get("title_en") or "").strip()
    ja = (game.get("title_ja") or "").strip()

    if lang == "zh":
        return zh or en or ja or game.get("id", "未知")
    elif lang == "en":
        return en or zh or ja or game.get("id", "未知")
    elif lang == "ja":
        return ja or zh or en or game.get("id", "未知")
    elif lang == "all":
        parts = []
        if zh:
            parts.append(zh)
        if en:
            parts.append(f"({en})")
        if ja and ja != zh:
            parts.append(f"[{ja}]")
        return " ".join(parts) if parts else game.get("id", "未知")
    else:
        return zh or en or ja or game.get("id", "未知")


def parse_game_date_num(game: Dict[str, Any]) -> int:
    """
    解析游戏发售日数字，与前端页面 parseGameDateNum 算法完全一致（由早到晚高精度时间戳）。
    """
    dates_dict = game.get("release_dates") or {}
    dates = [
        dates_dict.get("japan") or "",
        dates_dict.get("north_america") or "",
        dates_dict.get("europe") or ""
    ]
    min_val = 99999999
    for d in dates:
        if not d:
            continue
        m_year = re.search(r"(\d{4})", d)
        if not m_year:
            continue
        year = int(m_year.group(1))
        m_month = re.search(r"(\d{1,2})\s*月", d)
        month = int(m_month.group(1)) if m_month else 1
        m_day = re.search(r"(\d{1,2})\s*日", d)
        day = int(m_day.group(1)) if m_day else 1
        val = year * 10000 + month * 100 + day
        if val < min_val:
            min_val = val
    return min_val


def get_display_release_date(game: Dict[str, Any]) -> str:
    """获取主要发售日期展示文本（优先日版，其次美版/欧版）"""
    dates = game.get("release_dates") or {}
    return dates.get("japan") or dates.get("north_america") or dates.get("europe") or "-"


def print_formatted_list(missing_games: List[Dict[str, Any]], total_games_count: int, lang: str = "zh"):
    """以格式化表格列表形式打印至终端"""
    count = len(missing_games)
    print("=" * 100)
    print(f" 无视频介绍游戏列表 (共 {count} 款 / 总计 {total_games_count} 款)")
    print("=" * 100)

    header = f"{'序号':<6} {'主名称':<32} {'英文名称 / 原名':<36} {'平台':<12} {'发售日期'}"
    print(header)
    print("-" * 100)

    for idx, game in enumerate(missing_games, start=1):
        main_name = get_game_display_name(game, lang=lang)
        en_name = (game.get("title_en") or "").strip()
        ja_name = (game.get("title_ja") or "").strip()
        sub_name = en_name if en_name else ja_name
        platforms = "/".join(game.get("platforms", []))
        rel_date = get_display_release_date(game)

        # 截断过长文字防止折行错乱
        if len(main_name) > 30:
            main_name = main_name[:27] + "..."
        if len(sub_name) > 34:
            sub_name = sub_name[:31] + "..."

        print(f"{idx:<6} {main_name:<32} {sub_name:<36} {platforms:<12} {rel_date}")

    print("-" * 100)
    percentage = (count / total_games_count * 100) if total_games_count > 0 else 0
    print(f"统计汇总: 共找到 {count} 款无视频介绍的游戏，占游戏库总数 ({total_games_count} 款) 的 {percentage:.1f}%")
    print("=" * 100)


def print_names_only(missing_games: List[Dict[str, Any]], lang: str = "zh"):
    """仅输出游戏名称（每行一个）"""
    for game in missing_games:
        name = get_game_display_name(game, lang=lang)
        print(name)


def export_to_file(missing_games: List[Dict[str, Any]], output_path: str, lang: str = "zh"):
    """将缺失视频的游戏列表导出为指定文件 (txt, csv, json)"""
    ext = os.path.splitext(output_path)[1].lower()

    if ext == ".json":
        export_data = []
        for g in missing_games:
            export_data.append({
                "id": g.get("id"),
                "title_zh": g.get("title_zh"),
                "title_en": g.get("title_en"),
                "title_ja": g.get("title_ja"),
                "platforms": g.get("platforms", []),
                "release_dates": g.get("release_dates", {}),
                "publishers": g.get("publishers", [])
            })
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

    elif ext in (".yaml", ".yml"):
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("missing:\n")
            for g in missing_games:
                name = get_game_display_name(g, lang=lang)
                escaped_name = name.replace("\\", "\\\\").replace('"', '\\"')
                f.write(f'  "{escaped_name}": ""\n')

    elif ext == ".csv":
        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["序号", "ID", "中文名", "英文名", "日文名", "支持平台", "发行商", "发售日期"])
            for idx, g in enumerate(missing_games, start=1):
                writer.writerow([
                    idx,
                    g.get("id", ""),
                    g.get("title_zh", ""),
                    g.get("title_en", ""),
                    g.get("title_ja", ""),
                    "/".join(g.get("platforms", [])),
                    "/".join(g.get("publishers", [])),
                    get_display_release_date(g)
                ])

    else:
        # 默认导出为普通纯文本 TXT
        with open(output_path, "w", encoding="utf-8") as f:
            for g in missing_games:
                name = get_game_display_name(g, lang=lang)
                f.write(f"{name}\n")

    print(f"成功导出 {len(missing_games)} 款游戏列表至: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="列出全部缺少视频介绍的 FC / NES / FDS 游戏名称",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例用法:
  python list_missing_videos.py                  # 终端表格列出所有缺少视频的游戏
  python list_missing_videos.py -n               # 仅输出游戏名称（每行一个）
  python list_missing_videos.py -n --lang en     # 仅输出英文名称
  python list_missing_videos.py -p NES           # 仅筛选 NES 平台无视频的游戏
  python list_missing_videos.py -o missing.txt   # 导出为纯文本名称文件
  python list_missing_videos.py -o missing.csv   # 导出为 CSV 报表
  python list_missing_videos.py -o missing.yaml  # 导出为 YAML 模板 (方便调整配置)
  python list_missing_videos.py --count          # 仅显示统计数量
"""
    )

    parser.add_argument(
        "-d", "--data",
        help="指定游戏数据 json 文件路径（默认自动查找 data/fc_nes_games.json）"
    )
    parser.add_argument(
        "-n", "--names-only",
        action="store_true",
        help="仅输出游戏名称（每行一个，便于复制或重定向）"
    )
    parser.add_argument(
        "-l", "--lang",
        choices=["zh", "en", "ja", "all"],
        default="zh",
        help="名称输出语言: zh(中文优先,默认), en(英文), ja(日文), all(中英日完整呈现)"
    )
    parser.add_argument(
        "-p", "--platform",
        choices=["FC", "NES", "FDS"],
        help="仅筛选指定平台的游戏 (FC / NES / FDS)"
    )
    parser.add_argument(
        "-o", "--output",
        help="导出文件路径 (支持 .txt, .csv, .json, .yaml)"
    )
    parser.add_argument(
        "-c", "--count",
        action="store_true",
        help="仅打印缺失视频的游戏数量和占比统计"
    )
    parser.add_argument(
        "-s", "--sort",
        choices=["date", "name", "id"],
        default="date",
        help="排序方式: date(默认按发售日先后，与页面一致), name(按名称字母序), id(按游戏ID)"
    )

    args = parser.parse_args()

    # 1. 寻找并加载数据文件
    try:
        data_path = find_data_file(args.data)
        all_games = load_games(data_path)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. 筛选缺少视频的游戏
    missing_games = filter_missing_video_games(all_games, platform=args.platform)

    # 3. 排序（默认按发售日由早到晚，日期相同时按英文名，与前端页面完全一致）
    if args.sort == "name":
        missing_games.sort(key=lambda g: get_game_display_name(g, lang=args.lang).lower())
    elif args.sort == "id":
        missing_games.sort(key=lambda g: g.get("id", ""))
    elif args.sort == "date":
        missing_games.sort(key=lambda g: (parse_game_date_num(g), (g.get("title_en") or "").lower()))

    total_count = len(all_games)
    missing_count = len(missing_games)

    # 4. 仅输出统计数量
    if args.count:
        plat_info = f" [{args.platform}]" if args.platform else ""
        percentage = (missing_count / total_count * 100) if total_count > 0 else 0
        print(f"无视频介绍游戏数量{plat_info}: {missing_count} 款 (占总库 {total_count} 款的 {percentage:.1f}%)")
        return

    # 5. 导出文件
    if args.output:
        export_to_file(missing_games, args.output, lang=args.lang)
        return

    # 6. 终端打印
    if args.names_only:
        print_names_only(missing_games, lang=args.lang)
    else:
        print_formatted_list(missing_games, total_count, lang=args.lang)


if __name__ == "__main__":
    main()
