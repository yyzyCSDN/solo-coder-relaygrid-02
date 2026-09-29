from __future__ import annotations
from dataclasses import dataclass
from relaygrid.restoration.sequence import CandidateStep, rank_steps
from relaygrid.loads.priority import LoadBlock, select_to_serve
from relaygrid.der.islanding import Resource, assess_island, firm_capacity

@dataclass(frozen=True)
class RestorationRequest:
    capacity_kw: float
    load_blocks: tuple[LoadBlock,...]
    switching_candidates: tuple[CandidateStep,...]
    resources: tuple[Resource,...]=()

def _cold_demand(b: LoadBlock) -> float:
    return max(0.0,b.kw)*max(0.0,b.cold_load_multiplier)

class RestorationService:
    def plan(self,request: RestorationRequest):
        demand={b.block_id:_cold_demand(b) for b in request.load_blocks}
        # The load list can never exceed what the island can actually supply:
        # firm capacity already has the must-keep reserve subtracted.
        serve_capacity=max(0.0,request.capacity_kw)
        if request.resources:
            serve_capacity=min(serve_capacity,firm_capacity(list(request.resources)))
        served=select_to_serve(list(request.load_blocks),serve_capacity)
        island=assess_island(sum(served.values()),list(request.resources)) if request.resources else None
        # Reconcile: if the island cannot carry the selected load, curtail the
        # load list so served and island supply are the same number.
        if island is not None and sum(served.values()) > island.served_kw+1e-9:
            served=select_to_serve(list(request.load_blocks),island.served_kw)
            island=assess_island(sum(served.values()),list(request.resources))
        ranked=rank_steps(list(request.switching_candidates))
        return {"served":served,"switching":[s.branch_id for s in ranked],"island":island}
    def unserved_kw(self,request: RestorationRequest):
        plan=self.plan(request); demand=sum(_cold_demand(b) for b in request.load_blocks)
        return max(0.0,demand-sum(plan["served"].values()))
    def critical_served_ratio(self,request: RestorationRequest):
        plan=self.plan(request); critical=[b for b in request.load_blocks if b.priority>=8]
        denom=sum(_cold_demand(b) for b in critical)
        if denom<=0: return 1.0
        num=sum(plan["served"].get(b.block_id,0.0) for b in critical)
        return num/denom
