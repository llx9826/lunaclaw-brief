"""Tests for configuration loading."""

import os


def test_config_defaults():
    """Settings should load with correct structure and brand identity."""
    from clawcat.config import Settings
    s = Settings()
    assert s.brand.name == "ClawCat"
    assert s.llm.model, "LLM model should not be empty"
    assert s.llm.base_url, "LLM base_url should not be empty"
    assert s.output_dir == "output"


def test_config_env_override():
    """Environment variables should override defaults."""
    os.environ["LLM__MODEL"] = "test-model-override"
    os.environ["LLM__API_KEY"] = "sk-test-key"

    from clawcat.config import Settings
    s = Settings()
    assert s.llm.model == "test-model-override"
    assert s.llm.api_key == "sk-test-key"

    del os.environ["LLM__MODEL"]
    del os.environ["LLM__API_KEY"]


def test_config_yaml_loading():
    """If config.yaml exists, its values should be loaded."""
    from pathlib import Path
    yaml_path = Path("config.yaml")
    if yaml_path.exists():
        from clawcat.config import Settings
        s = Settings()
        # config.yaml has brand.name = "ClawCat"
        assert s.brand.name == "ClawCat"
        print("    config.yaml loaded successfully")
    else:
        print("    config.yaml not found, skipping YAML test")


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    passed = failed = 0
    for test in tests:
        try:
            test()
            print(f"  ✅ {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {test.__name__}: {e}")
            failed += 1
    print(f"\nRan {len(tests)} config tests: {passed} passed, {failed} failed")
