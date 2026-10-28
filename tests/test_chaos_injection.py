import pytest
from chaos.injector import ChaosInjector, ChaosType
from chaos.models import ChaosStatus


@pytest.mark.asyncio
async def test_chaos_inject_fault_execution():
    injector = ChaosInjector()
    drill = await injector.inject_fault(ChaosType.DB_POOL_STARVATION)

    assert drill.drill_id is not None
    assert drill.scenario.scenario_type == ChaosType.DB_POOL_STARVATION
    assert drill.status == ChaosStatus.REMEDIATED
    assert drill.mttr_seconds is not None
    assert drill.mttr_seconds > 0.0
    assert drill.incident_id is not None

    # Retrieve drill from catalog
    fetched = injector.get_drill(drill.drill_id)
    assert fetched is not None
    assert fetched.drill_id == drill.drill_id
    assert len(injector.list_drills()) >= 1


@pytest.mark.asyncio
async def test_chaos_inject_invalid_type_raises_error():
    injector = ChaosInjector()
    with pytest.raises(ValueError):
        await injector.inject_fault("nonexistent_chaos_type")
