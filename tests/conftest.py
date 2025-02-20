"""Global fixtures for Storj integration."""

from collections.abc import Generator, Coroutine
from unittest.mock import AsyncMock, MagicMock, patch
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import (
    ClientSessionGenerator,
    WebSocketGenerator,
    MockHAClientWebSocket,
)
from custom_components.storj.const import DOMAIN
from contextlib import contextmanager
from typing import Any, cast

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.components.websocket_api.http import URL

from homeassistant.components.websocket_api.auth import (
    TYPE_AUTH,
    TYPE_AUTH_OK,
    TYPE_AUTH_REQUIRED,
)
from typing import Iterable

import asyncio

import pytest


TEST_ACCESS_GRANT = "123xyz"
TEST_AGENT_ID = f"storj.{TEST_ACCESS_GRANT}"
CONFIG_ENTRY_TITLE = "Storj entry title"


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "custom_components.storj.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture(name="mock_config_entry")
def mock_config_entry() -> MockConfigEntry:
    """Fixture for MockConfigEntry."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_ACCESS_GRANT,
        title=CONFIG_ENTRY_TITLE,
        data={"access_grant": TEST_ACCESS_GRANT, "bucket_name": "ha-backups"},
    )


@pytest.fixture(name="access_json")
def access_json() -> dict[str, Any]:
    """Fixture for MockConfigEntry."""
    return {
        "satellite_addr": "123abcDEFxyz@my.storj-satellite.io:7777",
        "encryption_access": {
            "default_key": "ABCxyz=",
            "default_path_cipher": "ENC_AEGSCM",
        },
        "api_key": "135abc975XyZ",
        "macaroon": {
            "head": "abc123=",
            "caveats": [
                {"not_before": "2025-02-02T02:28:23.709Z", "nonce": "dOMuVw=="}
            ],
            "tail": "xyz987=",
        },
    }


@pytest.fixture
def hass_ws_client(
    aiohttp_client: ClientSessionGenerator,
    hass_access_token: str,
    hass: HomeAssistant,
    socket_enabled: None,
) -> WebSocketGenerator:
    """Websocket client fixture connected to websocket server."""

    async def create_client(
        hass: HomeAssistant = hass, access_token: str | None = hass_access_token
    ) -> MockHAClientWebSocket:
        """Create a websocket client."""
        assert await async_setup_component(hass, "websocket_api", {})
        client = await aiohttp_client(hass.http.app)
        websocket = await client.ws_connect(URL)
        auth_resp = await websocket.receive_json()
        assert auth_resp["type"] == TYPE_AUTH_REQUIRED

        if access_token is None:
            await websocket.send_json({"type": TYPE_AUTH, "access_token": "incorrect"})
        else:
            await websocket.send_json({"type": TYPE_AUTH, "access_token": access_token})

        auth_ok = await websocket.receive_json()
        assert auth_ok["type"] == TYPE_AUTH_OK

        def _get_next_id() -> Generator[int]:
            i = 0
            while True:
                yield (i := i + 1)

        id_generator = _get_next_id()

        def _send_json_auto_id(data: dict[str, Any]) -> Coroutine[Any, Any, None]:
            data["id"] = next(id_generator)
            return websocket.send_json(data)

        async def _remove_device(device_id: str, config_entry_id: str) -> Any:
            await _send_json_auto_id(
                {
                    "type": "config/device_registry/remove_config_entry",
                    "config_entry_id": config_entry_id,
                    "device_id": device_id,
                }
            )
            return await websocket.receive_json()

        # wrap in client
        wrapped_websocket = cast(MockHAClientWebSocket, websocket)
        wrapped_websocket.client = client
        wrapped_websocket.send_json_auto_id = _send_json_auto_id
        wrapped_websocket.remove_device = _remove_device
        return wrapped_websocket

    return create_client


# Copied from homeassistant:
# https://github.com/home-assistant/core/blob/2f121874987b5f19aed6b5769b9880c5322d95d0/tests/components/command_line/__init__.py#L9
@contextmanager
def mock_asyncio_subprocess_run(
    responses: bytes = iter([b""]),
    returncode: int | Iterable = 0,
    exception: Exception | None = None,
):
    """Mock create_subprocess_shell."""

    class MockProcess(asyncio.subprocess.Process):
        @property
        def returncode(self):
            if isinstance(returncode, int):
                return returncode
            return returncode.__next__()

        async def communicate(self):
            if exception:
                raise exception
            return responses.__next__(), b""

    mock_process = MockProcess(MagicMock(), MagicMock(), MagicMock())

    with patch(
        "asyncio.create_subprocess_exec",
        return_value=mock_process,
    ) as mock:
        yield mock


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield
