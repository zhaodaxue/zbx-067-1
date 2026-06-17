"""GPX 轨迹文件解析模块。

按 trkseg 分组解析轨迹点，每个点附带段号、段内序号、全局序号。
"""

import sys
import xml.etree.ElementTree as ET


GPX_NS = {
    'gpx': 'http://www.topografix.com/GPX/1/1',
    'gpxtpx': 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1',
}


def parse_gpx(filepath):
    """解析 GPX 文件，按 trkseg 分组返回轨迹点列表。

    每个点是 dict，包含 lat, lon, ele, segment_id, segment_point_index, global_index。

    返回值:
        成功返回 points 列表；异常（文件不存在、XML 坏、无轨迹点、无海拔）返回 None。
        异常信息写入 stderr。
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
