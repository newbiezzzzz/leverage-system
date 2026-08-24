from control_plane.product_factory import FACTORY_STAGES, create_dry_run_plan, ready_for_product_one


def test_dry_run_is_non_financial():
    plan = create_dry_run_plan()
    assert plan["mode"] == "dry-run"
    assert plan["real_paid_publish"] is False
    assert plan["money_movement"] is False
    assert [s["name"] for s in plan["stages"]] == list(FACTORY_STAGES)


def test_readiness_requires_all_stages():
    result = ready_for_product_one({stage: True for stage in FACTORY_STAGES})
    assert result["ready"] is True
    assert result["next"] == "create_product_1"


def test_readiness_blocks_missing_stage():
    result = ready_for_product_one({stage: True for stage in FACTORY_STAGES[:-1]})
    assert result["ready"] is False
    assert FACTORY_STAGES[-1] in result["missing"]
