"""Evidence graph: TASK → REQUIREMENT → CHECK → OBSERVATION → EVIDENCE → VERDICT."""

from __future__ import annotations

from typing import Any


def build_evidence_graph(report: dict[str, Any]) -> dict[str, Any]:
    meta = report.get("meta") or {}
    results = report.get("results") or []
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    task_id = "task"
    nodes.append(
        {
            "id": task_id,
            "kind": "task",
            "name": meta.get("taskName") or "ui-acceptance",
            "url": meta.get("url"),
            "commit": meta.get("commit"),
            "runId": meta.get("runId"),
        }
    )
    req_ids: dict[str, str] = {}
    for item in results:
        key = f"{item.get('check')}|{item.get('selector') or ''}"
        if key not in req_ids:
            rid = f"req-{len(req_ids)}"
            req_ids[key] = rid
            nodes.append(
                {
                    "id": rid,
                    "kind": "requirement",
                    "check": item.get("check"),
                    "selector": item.get("selector"),
                    "why": item.get("why"),
                    "domain": item.get("domain"),
                }
            )
            edges.append({"from": task_id, "to": rid, "rel": "requires"})
        rid = req_ids[key]
        idx = len([n for n in nodes if n["kind"] == "check"])
        cid = f"check-{idx}"
        oid = f"obs-{idx}"
        eid = f"ev-{idx}"
        vid = f"verdict-{idx}"
        vp = item.get("viewport") or {}
        nodes.append(
            {
                "id": cid,
                "kind": "check",
                "check": item.get("check"),
                "route": item.get("route"),
                "viewport": vp,
                "why": item.get("why"),
            }
        )
        nodes.append(
            {
                "id": oid,
                "kind": "observation",
                "message": item.get("message"),
                "route": item.get("route"),
                "viewport": vp,
                "environment": {
                    "url": meta.get("url"),
                    "colorScheme": vp.get("colorScheme"),
                    "commit": meta.get("commit"),
                },
            }
        )
        nodes.append(
            {
                "id": eid,
                "kind": "evidence",
                "values": item.get("evidence"),
                "screenshot": item.get("screenshot"),
                "command": item.get("command"),
                "timestamp": item.get("timestamp"),
            }
        )
        nodes.append(
            {
                "id": vid,
                "kind": "verdict",
                "status": item.get("status"),
                "actionable": item.get("actionable"),
                "layer": item.get("layer"),
            }
        )
        edges.append({"from": rid, "to": cid, "rel": "checked-by"})
        edges.append({"from": cid, "to": oid, "rel": "observed"})
        edges.append({"from": oid, "to": eid, "rel": "recorded"})
        edges.append({"from": eid, "to": vid, "rel": "concluded"})
    return {
        "schemaVersion": 3,
        "description": "TASK → REQUIREMENT → CHECK → OBSERVATION → EVIDENCE → VERDICT",
        "nodes": nodes,
        "edges": edges,
    }
