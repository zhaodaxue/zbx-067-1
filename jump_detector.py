"""海拔跃变检测模块。

仅同 trkseg 段内相邻点比较，不跨段。
"""

import os

DEFAULT_THRESHOLD = 50.0


def find_elevation_jumps(points, filepath, threshold=DEFAULT_THRESHOLD):
    """检测海拔突变点（仅段内相邻 trkpt 比较，不跨 trkseg）。

    Args:
        points: parse_gpx 返回的轨迹点列表
        filepath: 原文件路径（用于跃变记录的文件名）
        threshold: 海拔突变阈值（米），相邻点海拔差绝对值 > 阈值记为跃变

    Returns:
        跃变列表，每条包含：
            file, point_index, prev_point_index, segment_id,
            segment_point_index, prev_elevation, curr_elevation,
            delta, abs_delta
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
                'prev_point_index': prev_pt.get('global_index', i - 1),
                'segment_id': prev_pt.get('segment_id'),
                'segment_point_index': curr_pt.get('segment_point_index', 0),
                'prev_elevation': round(prev_ele, 2),
                'curr_elevation': round(curr_ele, 2),
                'delta': round(diff, 2),
                'abs_delta': round(abs(diff), 2),
            })

    return jumps
