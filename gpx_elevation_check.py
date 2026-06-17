#!/usr/bin/env python3
"""GPX 轨迹高度突变检测工具 — CLI 入口。

检测 GPX 轨迹文件中的海拔突变点，聚类为可疑路段，可选导出子轨迹。
"""

import argparse
import sys

from gpx_parser import parse_gpx
from jump_detector import find_elevation_jumps, DEFAULT_THRESHOLD
from zone_cluster import cluster_jumps, DEFAULT_GAP, DEFAULT_MIN_JUMPS
from gpx_export import export_zones
from output_format import format_text_output, format_json_output


def main():
    parser = argparse.ArgumentParser(
        description="检测 GPX 轨迹文件中的海拔突变点并聚类为可疑路段",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s track.gpx
  %(prog)s file1.gpx file2.gpx --json
  %(prog)s *.gpx --gap 5 --min-jumps 1
  %(prog)s track.gpx --export-dir ./zones

退出码: 0 表示全部文件有效且无可疑路段，1 表示有异常或至少有一处可疑路段。
        """,
    )
    parser.add_argument(
        'files',
        nargs='+',
        metavar='GPX_FILE',
        help='一个或多个 .gpx 文件路径',
    )
    parser.add_argument(
        '--json',
        action='store_true',
        dest='output_json',
        help='以 JSON 格式输出跃变列表',
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f'海拔突变阈值（米），默认 {DEFAULT_THRESHOLD}m，必须大于 0',
    )
    parser.add_argument(
        '--gap',
        type=int,
        default=DEFAULT_GAP,
        dest='gap',
        help=f'同段内两处跃变之间允许的最大间隔轨迹点数，默认 {DEFAULT_GAP}，必须 >= 0',
    )
    parser.add_argument(
        '--min-jumps',
        type=int,
        default=DEFAULT_MIN_JUMPS,
        dest='min_jumps',
        help=f'路段内最少的跃变点数，默认 {DEFAULT_MIN_JUMPS}，必须 >= 1',
    )
    parser.add_argument(
        '--export-dir',
        type=str,
        default=None,
        dest='export_dir',
        help='将可疑路段导出为独立 GPX 文件到指定目录',
    )

    args = parser.parse_args()

    if args.threshold <= 0:
        print(f"错误: --threshold 必须大于 0，当前值为 {args.threshold}", file=sys.stderr)
        sys.exit(1)

    if args.gap < 0:
        print(f"错误: --gap 必须大于等于 0，当前值为 {args.gap}", file=sys.stderr)
        sys.exit(1)

    if args.min_jumps < 1:
        print(f"错误: --min-jumps 必须大于等于 1，当前值为 {args.min_jumps}", file=sys.stderr)
        sys.exit(1)

    results = []
    has_any_zone = False
    has_any_error = False
    valid_files_count = 0

    for filepath in args.files:
        points = parse_gpx(filepath)
        if points is None:
            has_any_error = True
            continue

        valid_files_count += 1
        jumps = find_elevation_jumps(points, filepath, args.threshold)
        zones = cluster_jumps(jumps, args.gap, args.min_jumps)

        if zones:
            has_any_zone = True

        if args.export_dir and zones:
            exported = export_zones(zones, points, filepath, args.export_dir)
            for ep in exported:
                print(f"已导出: {ep}", file=sys.stderr)

        results.append({
            'file': filepath,
            'jumps': jumps,
            'zones': zones,
            'total_points': len(points),
        })

    if args.output_json:
        print(format_json_output(
            results, args.threshold, args.gap, args.min_jumps,
            len(args.files), valid_files_count, has_any_error,
        ))
    else:
        print(format_text_output(results, args.threshold, args.gap, args.min_jumps))

    if has_any_error or has_any_zone:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
