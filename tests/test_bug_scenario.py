import pytest

from relaygrid.der.islanding import Resource, assess_island
from relaygrid.loads.priority import LoadBlock, select_to_serve
from relaygrid.services.restoration_service import RestorationRequest, RestorationService


def test_cold_load_and_island_reserve_bound_the_restoration_plan():
    cold = LoadBlock("cold", kw=60.0, priority=10, cold_load_multiplier=1.5)
    assert select_to_serve([cold], 80.0) == {"cold": 80.0}

    assessment = assess_island(
        68.0,
        [Resource("battery", 70.0, grid_forming=True)],
        reserve_fraction=0.10,
    )
    assert assessment.served_kw == pytest.approx(63.2)
    assert assessment.shortfall_kw == pytest.approx(4.8)
    assert not assessment.feasible

    request = RestorationRequest(
        capacity_kw=100.0,
        load_blocks=(LoadBlock("critical", 100.0, 10),),
        switching_candidates=(),
        resources=(Resource("microgrid", 50.0, grid_forming=True),),
    )
    service = RestorationService()
    plan = service.plan(request)
    assert sum(plan["served"].values()) == pytest.approx(plan["island"].served_kw)
    assert service.unserved_kw(request) == pytest.approx(55.0)
