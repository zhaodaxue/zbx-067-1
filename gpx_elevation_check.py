#!/usr/bin/env python3
"""
GPX 轨迹高度突变检测工具

检测 GPX 轨迹文件中的海拔突变点（相邻两点海拔差绝对值 > 50 米）。
"""

import argparse
import json
import sys
import os
import xml.etree.ElementTree as ET


GPX_NS = {
    'gpx': 'http://www.topografix.com/GPX/1/1',
    'gpxtpx': 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1',
}

ELEVATION_THRESHOLD = 50.0


def parse_gpx(filepath):
    """解析 GPX 文件，返回轨迹点列表。

    每个点是 dict，包含 lat, lon, ele。
    如果文件没有海拔数据，返回 None。
    """
    try:
        tree = ET.parse(filepath)
    except ET.ParseError as e:
        print(f"警告: {filepath} XML 解析失败: {e}", file=sys.stderr)
        return None
    except FileNotFoundError:
        print(f"警告: {filepath} 文件不存在", file=sys.stderr)
        return None

    root = tree.getroot()

    trkpts = root.findall('.//gpx:trkpt', GPX_NS)
    if not trkpts:
        trkpts = root.findall('.//trkpt')
    if not trkpts:
        print(f"警告: {filepath} 中未找到轨迹点", file=sys.stderr)
        return None

    points = []
    has_elevation = False

    for pt in trkpts:
        lat = pt.get('lat')
        lon = pt.get('lon')
        if lat is None or lon is None:
            continue

        ele_elem = pt.find('gpx:ele', GPX_NS)
        if ele_elem is None:
            ele_elem = pt.find('ele')

        ele = None
        if ele_elem is not None and ele_elem.text is not None:
            try:
                ele = float(ele_elem.text)
                has_elevation = True
            except ValueError:
                pass

        points.append({
            'lat': float(lat),
            'lon': float(lon),
            'ele': ele,
        })

    if not has_elevation:
        print(f"警告: {filepath} 无海拔数据，跳过", file=sys.stderr)
        return None

    return points


def find_elevation_jumps(points, filepath, threshold=ELEVATION_THRESHOLD):
    """检测海拔突变点。

    返回跃变列表，每条包含文件名、点序号、前后海拔、落差。
    """
    jumps = []

    for i in range(1, len(points)):
        prev_ele = points[i - 1].get('ele')
        curr_ele = points[i].get('ele')

        if prev_ele is None or curr_ele is None:
            continue

        diff = curr_ele - prev_ele
        if abs(diff) > threshold:
            jumps.append({
                'file': os.path.basename(filepath),
                'point_index': i,
                'prev_elevation': round(prev_ele, 2),
                'curr_elevation': round(curr_ele, 2),
                'delta': round(diff, 2),
                'abs_delta': round(abs(diff), 2),
            })

    return jumps


def format_text_output(results):
    """格式化文本输出。"""
    total_jumps = sum(len(r['jumps']) for r in results)
    files_with_jumps = [r for r in results if len(r['jumps']) > 0]

    lines = []
    lines.append(f"共检测 {len(results)} 个文件，发现 {total_jumps} 处海拔跃变（阈值 > {ELEVATION_THRESHOLD}m）")

    if files_with_jumps:
        lines.append("")
        for r in files_with_jumps:
            lines.append(f"文件: {r['file']} ({len(r['jumps'])} 处跃变)")
            for j in r['jumps']:
                direction = "上升" if j['delta'] > 0 else "下降"
                lines.append(
                    f"  点 {j['point_index']}: "
                    f"{j['prev_elevation']}m -> {j['curr_elevation']}m "
                    f"({direction} {j['abs_delta']}m)"
                )
            lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="检测 GPX 轨迹文件中的海拔突变点",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s track.gpx
  %(prog)s file1.gpx file2.gpx --json
  %(prog)s *.gpx

退出码: 0 表示全部文件无跃变，1 表示至少有一处跃变或出错。
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
        default=ELEVATION_THRESHOLD,
        help=f'海拔突变阈值（米），默认 {ELEVATION_THRESHOLD}m',
    )

    args = parser.parse_args()

    results = []
    has_any_jump = False

    for filepath in args.files:
        points = parse_gpx(filepath)
        if points is None:
            continue

        jumps = find_elevation_jumps(points, filepath, args.threshold)
        if jumps:
            has_any_jump = True

        results.append({
            'file': filepath,
            'jumps': jumps,
            'total_points': len(points),
        })

    if args.output_json:
        output = {
            'threshold': args.threshold,
            'total_files': len(results),
            'files_with_jumps': sum(1 for r in results if len(r['jumps']) > 0),
            'total_jumps': sum(len(r['jumps']) for r in results),
            'results': results,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(format_text_output(results))

    if has_any_jump:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
