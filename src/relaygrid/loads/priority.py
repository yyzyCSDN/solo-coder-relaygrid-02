from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class LoadBlock:
    block_id: str
    kw: float
    priority: int
    min_service_kw: float=0.0
    cold_load_multiplier: float=1.0

def _effective_kw(block: LoadBlock) -> float:
    # Restoration picks blocks against their cold-load (inrush) demand,
    # not the pre-outage diversified kW.
    return max(0.0,block.kw*block.cold_load_multiplier)

def select_to_serve(blocks: list[LoadBlock], capacity_kw: float):
    remaining=max(0.0,capacity_kw); served={}
    ordered=sorted(blocks,key=lambda b:(-b.priority,b.block_id))
    for b in ordered:
        demand=_effective_kw(b)
        floor=min(demand,max(0.0,b.min_service_kw))
        if remaining+1e-9 < floor: served[b.block_id]=0.0; continue
        take=min(demand,remaining); served[b.block_id]=take; remaining-=take
    return served

def shed_order(blocks: list[LoadBlock]):
    return [b.block_id for b in sorted(blocks,key=lambda x:(x.priority,-x.kw,x.block_id))]
