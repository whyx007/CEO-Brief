from __future__ import annotations

from typing import Any


GROUP_LABELS = {
    'SubTrack': '产业链',
    'ChainStage': '环节',
    'Enterprise': '企业',
    'KeyCapability': '能力',
    'ApplicationScenario': '场景',
    'Supplier': '供应商',
    'Customer': '客户',
}


def make_graph() -> dict[str, list[dict[str, Any]]]:
    return {'nodes': [], 'edges': []}


def add_node(
    graph: dict[str, list[dict[str, Any]]],
    node_id: str,
    label: str,
    node_type: str,
    properties: dict[str, Any] | None = None,
) -> None:
    if not node_id or any(item.get('id') == node_id for item in graph['nodes']):
        return
    graph['nodes'].append({
        'id': node_id,
        'label': label or node_id,
        'type': node_type,
        'group': node_type,
        'groupLabel': GROUP_LABELS.get(node_type, node_type),
        'properties': properties or {},
    })


def add_edge(
    graph: dict[str, list[dict[str, Any]]],
    source: str,
    target: str,
    edge_type: str,
    label: str = '',
    properties: dict[str, Any] | None = None,
) -> None:
    if not source or not target:
        return
    edge_id = f'{source}::{edge_type}::{target}'
    if any(item.get('id') == edge_id for item in graph['edges']):
        return
    graph['edges'].append({
        'id': edge_id,
        'source': source,
        'target': target,
        'type': edge_type,
        'label': label or edge_type,
        'properties': properties or {},
    })
