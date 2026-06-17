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
    """解析 GPX 文件，按 trkseg 分组返回轨迹点列表。

    每个点是 dict，包含 lat, lon, ele, segment_id, segment_point_index, global_index。
    异常返回 None（文件不存在、XML 坏、无轨迹点、无海拔）。
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

    trksegs = root.findall('.//gpx:trkseg', GPX_NS)
    if not trksegs:
        trksegs = root.findall('.//trkseg')

    if not trksegs:
        trkpts = root.findall('.//gpx:trkpt', GPX_NS)
        if not trkpts:
            trkpts = root.findall('.//trkpt')
        if trkpts:
            trksegs = [root]

    if not trksegs:
        print(f"警告: {filepath} 中未找到轨迹点", file=sys.stderr)
        return None

    points = []
    has_elevation = False
    global_index = 0

    for seg_id, seg in enumerate(trksegs):
        trkpts = seg.findall('.//gpx:trkpt', GPX_NS)
        if not trkpts:
            trkpts = seg.findall('.//trkpt')

        for seg_pt_idx, pt in enumerate(trkpts):
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
                'segment_id': seg_id,
                'segment_point_index': seg_pt_idx,
                'global_index': global_index,
            })
            global_index += 1

    if not points:
        print(f"警告: {filepath} 中未找到轨迹点", file=sys.stderr)
        return None

    if not has_elevation:
        print(f"警告: {filepath} 无海拔数据，跳过", file=sys.stderr)
        return None

    return points


def find_elevation_jumps(points, filepath, threshold=ELEVATION_THRESHOLD):
    """检测海拔突变点（仅段内相邻 trkpt 比较，不跨 trkseg）。

    返回跃变列表，每条包含文件名、点序号、前后海拔、落差。
    """
    jumps = []

    for i in range(1, len(points)):
        prev_pt = points[i - 1]
        curr_pt = points[i]

        if prev_pt.get('segment_id') != curr_pt.get('segment_id'):
            continue

        prev_ele = prev_pt.get('ele')
        curr_ele = curr_pt.get('ele')

        if prev_ele is None or curr_ele is None:
            continue

        diff = curr_ele - prev_ele
        if abs(diff) > threshold:
            jumps.append({
                'file': os.path.basename(filepath),
                'point_index': curr_pt.get('global_index', i),
                'segment_id': prev_pt.get('segment_id'),
                'prev_elevation': round(prev_ele, 2),
                'curr_elevation': round(curr_ele, 2),
                'delta': round(diff, 2),
                'abs_delta': round(abs(diff), 2),
            })

    return jumps


def format_text_output(results, threshold):
    """格式化文本输出。"""
    total_jumps = sum(len(r['jumps']) for r in results)
    files_with_jumps = [r for r in results if len(r['jumps']) > 0]

    lines = []
    lines.append(f"共检测 {len(results)} 个文件，发现 {total_jumps} 处海拔跃变（阈值 > {threshold}m）")

    if files_with_jumps:
        lines.append("")
        for r in files_with_jumps:
            lines.append(f"文件: {r['file']} ({len(r['jumps'])} 处跃变)")
            for j in r['jumps']:
                direction = "上升" if j['delta'] > 0 else "下降"
                seg_info = f" [段{j['segment_id']}]" if 'segment_id' in j else ""
                lines.append(
                    f"  点 {j['point_index']}{seg_info}: "
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

退出码: 0 表示全部文件有效且无跃变，1 表示有异常或至少有一处跃变。
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
        help=f'海拔突变阈值（米），默认 {ELEVATION_THRESHOLD}m，必须大于 0',
    )

    args = parser.parse_args()

    if args.threshold <= 0:
        print(f"错误: --threshold 必须大于 0，当前值为 {args.threshold}", file=sys.stderr)
        sys.exit(1)

    results = []
    has_any_jump = False
    has_any_error = False
    valid_files_count = 0

    for filepath in args.files:
        points = parse_gpx(filepath)
        if points is None:
            has_any_error = True
            continue

        valid_files_count += 1
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
            'total_files': len(args.files),
            'valid_files': valid_files_count,
            'files_with_jumps': sum(1 for r in results if len(r['jumps']) > 0),
            'total_jumps': sum(len(r['jumps']) for r in results),
            'has_error': has_any_error,
            'results': results,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(format_text_output(results, args.threshold))

    if has_any_error or has_any_jump:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
