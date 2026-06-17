"""输出格式化模块。

文本输出：先列可疑路段，再列跃变明细。
JSON 输出：每条 result 增加 zones 字段。
"""

import json


def format_text_output(results, threshold, gap, min_jumps):
    """格式化文本输出。"""
    total_jumps = sum(len(r['jumps']) for r in results)
    total_zones = sum(len(r.get('zones', [])) for r in results)
    files_with_jumps = [r for r in results if len(r['jumps']) > 0]

    lines = []
    lines.append(
        f"共检测 {len(results)} 个文件，"
        f"发现 {total_jumps} 处海拔跃变、{total_zones} 处可疑路段"
        f"（阈值 > {threshold}m，gap={gap}，min-jumps={min_jumps}）"
    )

    if files_with_jumps:
        lines.append("")
        for r in files_with_jumps:
            zones = r.get('zones', [])
            jump_count = len(r['jumps'])
            zone_count = len(zones)
            lines.append(
                f"文件: {r['file']} "
                f"({jump_count} 处跃变, {zone_count} 处可疑路段)"
            )

            if zones:
                lines.append("")
                lines.append("  可疑路段:")
                for z in zones:
                    lines.append(
                        f"    路段 {z['zone_id']} [段{z['segment_id']}]: "
                        f"点 {z['start_index']}-{z['end_index']}, "
                        f"跃变数 {z['jump_count']}, "
                        f"最大落差 {z['max_abs_delta']}m"
                    )

            lines.append("")
            lines.append("  跃变明细:")
            for j in r['jumps']:
                direction = "上升" if j['delta'] > 0 else "下降"
                seg_info = f" [段{j['segment_id']}]" if 'segment_id' in j else ""
                lines.append(
                    f"    点 {j['point_index']}{seg_info}: "
                    f"{j['prev_elevation']}m -> {j['curr_elevation']}m "
                    f"({direction} {j['abs_delta']}m)"
                )
            lines.append("")

    return "\n".join(lines)


def format_json_output(results, threshold, gap, min_jumps,
                       total_files, valid_files, has_error):
    """格式化 JSON 输出。"""
    output = {
        'threshold': threshold,
        'gap': gap,
        'min_jumps': min_jumps,
        'total_files': total_files,
        'valid_files': valid_files,
        'files_with_jumps': sum(1 for r in results if len(r['jumps']) > 0),
        'total_jumps': sum(len(r['jumps']) for r in results),
        'total_zones': sum(len(r.get('zones', [])) for r in results),
        'has_error': has_error,
        'results': [],
    }

    for r in results:
        result_entry = {
            'file': r['file'],
            'jumps': [],
            'zones': [],
            'total_points': r['total_points'],
        }

        for j in r['jumps']:
            jump_entry = {
                'file': j['file'],
                'point_index': j['point_index'],
                'prev_point_index': j.get('prev_point_index'),
                'segment_id': j['segment_id'],
                'segment_point_index': j.get('segment_point_index'),
                'prev_elevation': j['prev_elevation'],
                'curr_elevation': j['curr_elevation'],
                'delta': j['delta'],
                'abs_delta': j['abs_delta'],
            }
            result_entry['jumps'].append(jump_entry)

        for z in r.get('zones', []):
            zone_entry = {
                'zone_id': z['zone_id'],
                'segment_id': z['segment_id'],
                'start_index': z['start_index'],
                'end_index': z['end_index'],
                'jump_count': z['jump_count'],
                'max_abs_delta': z['max_abs_delta'],
                'jump_indexes': z['jump_indexes'],
            }
            result_entry['zones'].append(zone_entry)

        output['results'].append(result_entry)

    return json.dumps(output, ensure_ascii=False, indent=2)
