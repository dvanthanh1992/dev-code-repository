from app.config import Settings, normalize_mode


def test_normalize_mode() -> None:
    assert normalize_mode("blue-green") == "bluegreen"
    assert normalize_mode("blue_green") == "bluegreen"
    assert normalize_mode("canary") == "canary"
    assert normalize_mode("anything") == "canary"


def test_settings_public_config(monkeypatch) -> None:
    monkeypatch.setenv("APP_VERSION", "v-test")
    monkeypatch.setenv("TRAFFIC_RPS", "9")
    monkeypatch.setenv("KUBERNETES_DISCOVERY_ENABLED", "false")
    settings = Settings.from_env()

    assert settings.app_version == "v-test"
    assert settings.traffic_rps == 9
    assert settings.kubernetes_discovery_enabled is False
    assert settings.public_config()["trafficRps"] == 9
