from nexuscore.llm.task_model_map import (
    LEGACY_TO_TASK,
    TASK_MODEL_CONFIGS,
    build_task_model_map_dict,
)


def test_build_task_model_map_dict_shapes():
    mapping = build_task_model_map_dict()
    for task, _cfg in TASK_MODEL_CONFIGS.items():
        assert task in mapping
        entry = mapping[task]
        primary = entry["primary"]
        fallbacks = entry["fallbacks"]
        assert isinstance(primary, str) and ":" in primary
        assert fallbacks, f"{task} must define fallbacks"
        for model in [primary, *fallbacks]:
            vendor, name = model.split(":", 1)
            assert vendor and name


def test_legacy_mapping_targets_exist():
    for legacy_task, resolved in LEGACY_TO_TASK.items():
        assert (
            resolved in TASK_MODEL_CONFIGS
        ), f"Legacy task '{legacy_task}' resolves to missing '{resolved}'"
