from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from trigger_service.models import DisruptionEvent
from rider_service.models import Zone


def _zone_node(zone: Zone, event_count: int) -> dict:
    return {
        "id": f"zone:{zone.id}",
        "type": "zone",
        "label": zone.name,
        "city": zone.city,
        "risk_score": zone.composite_risk_score,
        "event_count": event_count,
    }


async def build_graph_snapshot(db: AsyncSession, hours: int = 72) -> dict:
    now_utc = datetime.now(timezone.utc)
    cutoff = (now_utc - timedelta(hours=max(hours, 1))).replace(tzinfo=None)

    zone_rows = (await db.execute(select(Zone))).scalars().all()
    event_rows = (
        await db.execute(
            select(DisruptionEvent).where(DisruptionEvent.created_at >= cutoff).order_by(DisruptionEvent.created_at.desc())
        )
    ).scalars().all()

    events_by_zone: dict[UUID, list[DisruptionEvent]] = defaultdict(list)
    for event in event_rows:
        events_by_zone[event.zone_id].append(event)

    nodes: list[dict] = []
    edges: list[dict] = []

    for zone in zone_rows:
        zone_events = events_by_zone.get(zone.id, [])
        nodes.append(_zone_node(zone, len(zone_events)))

    trigger_nodes_added: set[str] = set()
    for event in event_rows:
        event_node_id = f"event:{event.id}"
        trigger_node_id = f"trigger:{event.trigger_type}"
        zone_node_id = f"zone:{event.zone_id}"

        nodes.append(
            {
                "id": event_node_id,
                "type": "event",
                "label": event.trigger_type,
                "severity": event.severity,
                "affected_riders": event.affected_riders,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
        )

        if trigger_node_id not in trigger_nodes_added:
            trigger_nodes_added.add(trigger_node_id)
            nodes.append(
                {
                    "id": trigger_node_id,
                    "type": "trigger",
                    "label": event.trigger_type,
                }
            )

        edges.extend(
            [
                {"source": zone_node_id, "target": event_node_id, "relation": "has_event"},
                {"source": event_node_id, "target": trigger_node_id, "relation": "classified_as"},
            ]
        )

    # Propagation edges: same trigger type observed across multiple zones in rolling 2-hour bins.
    by_trigger_bucket: dict[tuple[str, str], set[UUID]] = defaultdict(set)
    for event in event_rows:
        if not event.created_at:
            continue
        bucket = event.created_at.replace(minute=0, second=0, microsecond=0)
        by_trigger_bucket[(event.trigger_type, bucket.isoformat())].add(event.zone_id)

    propagation_edges: list[dict] = []
    propagation_scores: dict[tuple[str, str], int] = defaultdict(int)
    for (_trigger_type, bucket), zone_ids in by_trigger_bucket.items():
        zones = sorted(str(z) for z in zone_ids)
        for i in range(len(zones)):
            for j in range(i + 1, len(zones)):
                key = (zones[i], zones[j])
                propagation_scores[key] += 1

    for (src, dst), weight in propagation_scores.items():
        propagation_edges.append(
            {
                "source": f"zone:{src}",
                "target": f"zone:{dst}",
                "relation": "propagates_with",
                "weight": weight,
            }
        )

    edges.extend(propagation_edges)

    hotspots = sorted(
        (
            {
                "zone_id": str(zone.id),
                "zone": zone.name,
                "events": len(events_by_zone.get(zone.id, [])),
            }
            for zone in zone_rows
        ),
        key=lambda item: item["events"],
        reverse=True,
    )[:10]

    return {
        "generated_at": now_utc.isoformat(),
        "window_hours": hours,
        "nodes": nodes,
        "edges": edges,
        "hotspots": hotspots,
    }
