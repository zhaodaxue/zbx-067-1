"""可疑路段 GPX 导出模块。

每个可疑路段写出独立 GPX 文件，含路段起止点及前后各 1 个上下文点。
"""

import os
import xml.etree.ElementTree as ET
from xml.dom import minidom


GPX_NS = 'http://www.topografix.com/GPX/1/1'


def _build_index_map(points):
    gi_map = {}
    for pt in points:
        gi_map[pt['global_index']] = pt

    seg_map = {}
    for pt in points:
        seg_map.setdefault(pt['segment_id'], []).append(pt)
    for seg_id in seg_map:
        seg_map[seg_id].sort(key=lambda p: p['segment_point_index'])

    return gi_map, seg_map


def _get_context_points(zone, gi_map, seg_map):
    seg_id = zone['segment_id']
    seg_pts = seg_map.get(seg_id, [])

    start_gi = zone['start_index']
    end_gi = zone['end_index']

    start_pt = gi_map.get(start_gi)
    end_pt = gi_map.get(end_gi)
    if start_pt is None or end_pt is None:
        return []

    start_spi = start_pt['segment_point_index']
    end_spi = end_pt['segment_point_index']

    context_before = None
    for pt in seg_pts:
        if pt['segment_point_index'] < start_spi:
            context_before = pt

    context_after = None
    for pt in seg_pts:
        if pt['segment_point_index'] > end_spi:
            context_after = pt
            break

    zone_pts = []
    for pt in seg_pts:
        if start_spi <= pt['segment_point_index'] <= end_spi:
            zone_pts.append(pt)

    result = []
    if context_before is not None:
        result.append(context_before)
    result.extend(zone_pts)
    if context_after is not None:
        result.append(context_after)

    return result


def _points_to_trkpts_elem(pts, parent):
    for pt in pts:
        trkpt = ET.SubElement(parent, 'trkpt')
        trkpt.set('lat', str(pt['lat']))
        trkpt.set('lon', str(pt['lon']))
        if pt.get('ele') is not None:
            ele = ET.SubElement(trkpt, 'ele')
            ele.text = str(pt['ele'])


def _prettify(elem):
    rough = ET.tostring(elem, encoding='unicode', xml_declaration=True)
    parsed = minidom.parseString(rough)
    lines = [l for l in parsed.toprettyxml(indent='  ').split('\n') if l.strip()]
    return '\n'.join(lines)


def export_zones(zones, points, filepath, export_dir):
    """将每个可疑路段导出为独立 GPX 文件。

    Args:
        zones: cluster_jumps 返回的路段列表
        points: parse_gpx 返回的轨迹点列表
        filepath: 原始 GPX 文件路径
        export_dir: 导出目录路径

    Returns:
        导出文件路径列表
    """
    os.makedirs(export_dir, exist_ok=True)

    gi_map, seg_map = _build_index_map(points)

    base_name = os.path.splitext(os.path.basename(filepath))[0]
    exported = []

    for zone in zones:
        zone_pts = _get_context_points(zone, gi_map, seg_map)
        if not zone_pts:
            continue

        gpx = ET.Element('gpx', xmlns=GPX_NS)
        gpx.set('version', '1.1')
        gpx.set('creator', 'gpx-elevation-check')

        trk = ET.SubElement(gpx, 'trk')
        name = ET.SubElement(trk, 'name')
        name.text = f"{base_name}_zone{zone['zone_id']}"

        trkseg = ET.SubElement(trk, 'trkseg')
        _points_to_trkpts_elem(zone_pts, trkseg)

        out_name = f"{base_name}_zone{zone['zone_id']}.gpx"
        out_path = os.path.join(export_dir, out_name)

        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(_prettify(gpx))

        exported.append(out_path)

    return exported
