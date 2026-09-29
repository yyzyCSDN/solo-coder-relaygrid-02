from __future__ import annotations
from dataclasses import dataclass
from relaygrid.restoration.sequence import CandidateStep, rank_steps
from relaygrid.loads.priority import LoadBlock, select_to_serve
from relaygrid.der.islanding import Resource, assess_island, island_deliverable_kw

@dataclass(frozen=True)
class RestorationRequest:
    capacity_kw: float
    load_blocks: tuple[LoadBlock,...]
    switching_candidates: tuple[CandidateStep,...]
    resources: tuple[Resource,...]=()

def _demand_kw(block: LoadBlock) -> float:
    # Cold-load demand (post-outage inrush) is the common kW basis used for
    # selection, islanding, and unserved-energy accounting.
    return max(0.0,block.kw*block.cold_load_multiplier)

class RestorationService:
    def plan(self,request: RestorationRequest):
        if request.resources:
            total_demand=sum(_demand_kw(b) for b in request.load_blocks)
            deliverable=island_deliverable_kw(total_demand,list(request.resources))
            if not any(r.grid_forming and r.available_kw>0 for r in request.resources):
                # Without a grid-forming resource the resources cannot form an
                # island, so none of their output is deliverable.
                deliverable=0.0
            capacity=min(max(0.0,request.capacity_kw),deliverable)
        else:
            capacity=max(0.0,request.capacity_kw)
        served=select_to_serve(list(request.load_blocks),capacity)
        ranked=rank_steps(list(request.switching_candidates))
        island_load=sum(served.values())
        island=assess_island(island_load,list(request.resources)) if request.resources else None
        demand=sum(_demand_kw(b) for b in request.load_blocks)
        return {"served":served,"switching":[s.branch_id for s in ranked],"island":island,
                "demand_kw":demand,"unserved_kw":max(0.0,demand-island_load)}
    def unserved_kw(self,request: RestorationRequest):
        return self.plan(request)["unserved_kw"]
    def critical_served_ratio(self,request: RestorationRequest):
        plan=self.plan(request); critical=[b for b in request.load_blocks if b.priority>=8]
        denom=sum(_demand_kw(b) for b in critical)
        if denom<=0: return 1.0
        num=sum(plan["served"].get(b.block_id,0.0) for b in critical)
        return num/denom
