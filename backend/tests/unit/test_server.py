from app.server import SERVER_KEEP_ALIVE_TIMEOUT_SECONDS, build_server_config


def test_deployment_server_uses_load_safe_keep_alive_timeout() -> None:
    config = build_server_config()

    assert SERVER_KEEP_ALIVE_TIMEOUT_SECONDS == 30
    assert config.timeout_keep_alive == SERVER_KEEP_ALIVE_TIMEOUT_SECONDS
