"""可疑路段聚类模块。

同 trkseg 内，相邻两处跃变之间间隔的轨迹点数 ≤ gap 则并入同一路段。
跨 trkseg 绝不合并。
路段内跃变点数不足 min_jumps 则丢弃。
"""

DEFAULT_GAP = 3
DEFAULT_MIN_JUMPS = 2


def cluster_jumps(jumps, gap=DEFAULT_GAP, min_jumps=DEFAULT_MIN_JUMPS):
    """将跃变点聚类为可疑路段。

    Args:
        jumps: find_elevation_jumps 返回的跃变列表
        gap: 同段内两处跃变之间允许的最大间隔轨迹点数（默认 3）
        min_jumps: 路段内最少的跃变点数（默认 2），不足则丢弃

    Returns:
        路段列表，每条包含：
            zone_id, segment_id, start_index, end_index,
            jump_count, max_abs_delta, jump_indexes, jumps
    """
    if not jumps:
        return []

    seg_groups = {}
    for jump in jumps:
        seg_id = jump['segment_id']
        seg_groups.setdefault(seg_id, []).append(jump)

    all_clusters = []

    for seg_id in sorted(seg_groups.keys()):
        group = sorted(seg_groups[seg_id], key=lambda j: j['segment_point_index'])

        cluster = [group[0]]

        for i in range(1, len(group)):
            prev_spi = cluster[-1]['segment_point_index']
            curr_spi = group[i]['segment_point_index']
            point_gap = curr_spi - prev_spi - 1

            if point_gap <= gap:
                cluster.append(group[i])
            else:
                all_clusters.append(cluster)
                cluster = [group[i]]

        all_clusters.append(cluster)

    zones = []
    zone_id = 0

    for cluster in all_clusters:
        if len(cluster) < min_jumps:
            continue

        start_index = cluster[0]['prev_point_index']
        end_index = cluster[-1]['point_index']
        max_abs_delta = max(j['abs_delta'] for j in cluster)
        jump_indexes = [j['point_index'] for j in cluster]

        zones.append({
            'zone_id': zone_id,
            'segment_id': cluster[0]['segment_id'],
            'start_index': start_index,
            'end_index': end_index,
            'jump_count': len(cluster),
            'max_abs_delta': round(max_abs_delta, 2),
            'jump_indexes': jump_indexes,
            'jumps': cluster,
        })
        zone_id += 1

    return zones
