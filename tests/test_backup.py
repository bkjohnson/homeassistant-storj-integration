"""Test the Storj BackupAgent"""

from collections.abc import AsyncGenerator
from io import StringIO
from homeassistant.core import HomeAssistant

from typing import Any
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import (
    ClientSessionGenerator,
    WebSocketGenerator,
)
from syrupy.assertion import SnapshotAssertion
from syrupy.matchers import path_type
from unittest.mock import Mock, patch
from homeassistant.setup import async_setup_component
from homeassistant.components.backup import (
    DOMAIN as BACKUP_DOMAIN,
    AddonInfo,
    AgentBackup,
)
from json_flatten import flatten
import json

from custom_components.storj.const import DOMAIN
from .conftest import mock_asyncio_subprocess_run, TEST_AGENT_ID
import pytest


TEST_AGENT_BACKUP = AgentBackup(
    addons=[AddonInfo(name="Test", slug="test", version="1.0.0")],
    backup_id="test-backup",
    database_included=True,
    date="2025-01-01T01:23:45.678Z",
    extra_metadata={
        "with_automatic_settings": False,
    },
    folders=[],
    homeassistant_included=True,
    homeassistant_version="2024.12.0",
    name="Test",
    protected=False,
    size=987,
)
TEST_AGENT_BACKUP_RESULT = {
    "addons": [{"name": "Test", "slug": "test", "version": "1.0.0"}],
    "agents": {TEST_AGENT_ID: {"protected": False, "size": 987}},
    "backup_id": "test-backup",
    "database_included": True,
    "date": "2025-01-01T01:23:45.678Z",
    "extra_metadata": {"with_automatic_settings": False},
    "folders": [],
    "homeassistant_included": True,
    "homeassistant_version": "2024.12.0",
    "name": "Test",
    "failed_agent_ids": [],
    "with_automatic_settings": None,
}


@pytest.fixture(autouse=True)
async def setup_backup_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> AsyncGenerator[None]:
    """Set up Storj integration."""
    with (
        patch("homeassistant.components.backup.is_hassio", return_value=False),
        patch("homeassistant.components.backup.store.STORE_DELAY_SAVE", 0),
    ):
        assert await async_setup_component(hass, BACKUP_DOMAIN, {BACKUP_DOMAIN: {}})
        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)

        await hass.async_block_till_done()
        yield


async def test_agents_upload(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    caplog: pytest.LogCaptureFixture,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test agent upload backup."""

    assert await async_setup_component(hass, BACKUP_DOMAIN, {})
    client = await hass_client()

    with (
        patch(
            "homeassistant.components.backup.manager.BackupManager.async_get_backup",
        ) as fetch_backup,
        patch(
            "homeassistant.components.backup.manager.read_backup",
            return_value=TEST_AGENT_BACKUP,
        ),
        patch("pathlib.Path.open") as mocked_open,
        mock_asyncio_subprocess_run(returncode=0) as subprocess_exec,
    ):

        mocked_open.return_value.read = Mock(side_effect=[b"test", b""])
        fetch_backup.return_value = TEST_AGENT_BACKUP
        resp = await client.post(
            f"/api/backup/upload?agent_id={DOMAIN}.{mock_config_entry.unique_id}",
            data={"file": StringIO("test")},
        )

        matcher = path_type(
            mapping={"2": (str,)},
            replacer=lambda data, _: data[data.find("backups") :],
        )

        assert resp.status == 201
        assert f"Uploading backup: {TEST_AGENT_BACKUP.backup_id}" in caplog.text
        assert f"Uploaded backup: {TEST_AGENT_BACKUP.backup_id}" in caplog.text
        subprocess_exec.assert_called_once()
        assert snapshot(matcher=matcher) == subprocess_exec.mock_calls[0].args


async def test_agents_upload_fail(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    caplog: pytest.LogCaptureFixture,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test agent upload backup fails."""

    assert await async_setup_component(hass, BACKUP_DOMAIN, {})
    client = await hass_client()

    with (
        patch(
            "homeassistant.components.backup.manager.BackupManager.async_get_backup",
        ) as fetch_backup,
        patch(
            "homeassistant.components.backup.manager.read_backup",
            return_value=TEST_AGENT_BACKUP,
        ),
        patch("pathlib.Path.open") as mocked_open,
        mock_asyncio_subprocess_run(
            returncode=1, responses=iter([b""])
        ) as subprocess_exec,
    ):

        mocked_open.return_value.read = Mock(side_effect=[b"test", b""])
        fetch_backup.return_value = TEST_AGENT_BACKUP
        resp = await client.post(
            f"/api/backup/upload?agent_id={DOMAIN}.{mock_config_entry.unique_id}",
            data={"file": StringIO("test")},
        )

        assert resp.status == 201
        assert f"Uploading backup: {TEST_AGENT_BACKUP.backup_id}" in caplog.text
        subprocess_exec.assert_called_once()
        assert "Failed to upload backup: Unable to complete upload" in caplog.text


async def test_agents_list_backups(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test agent list backups."""

    flattened_metadata = json.dumps(flatten(TEST_AGENT_BACKUP.as_dict())).encode(
        "utf-8"
    )

    responses = iter(
        [
            b'{"kind":"OBJ","created":"2025-02-09 20:02:19","size":12,"key":"backup.tar"}',
            flattened_metadata,
        ]
    )

    with (mock_asyncio_subprocess_run(responses=responses) as subprocess_exec,):
        client = await hass_ws_client(hass)
        await client.send_json_auto_id({"type": "backup/info"})
        response = await client.receive_json()

        assert response["success"]
        assert response["result"]["agent_errors"] == {}
        assert response["result"]["backups"] == [TEST_AGENT_BACKUP_RESULT]
        assert [mock_call.args for mock_call in subprocess_exec.mock_calls] == snapshot


async def test_agents_list_backups_fail(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Test agent list backups fails."""

    with mock_asyncio_subprocess_run(
        responses=iter([b""]), returncode=1
    ) as subprocess_exec:
        client = await hass_ws_client(hass)
        await client.send_json_auto_id({"type": "backup/info"})
        response = await client.receive_json()

        assert response["success"]
        assert response["result"]["backups"] == []
        assert response["result"]["agent_errors"] == {
            TEST_AGENT_ID: "Failed to list backups: Unable to fetch backup data"
        }
        assert subprocess_exec.called


@pytest.mark.parametrize(
    ("backup_id", "expected_result"),
    [
        (TEST_AGENT_BACKUP.backup_id, TEST_AGENT_BACKUP_RESULT),
        ("12345", None),
    ],
    ids=["found", "not_found"],
)
async def test_agents_get_backup(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    backup_id: str,
    expected_result: dict[str, Any] | None,
) -> None:
    """Test agent get backup."""

    flattened_metadata = json.dumps(flatten(TEST_AGENT_BACKUP.as_dict())).encode(
        "utf-8"
    )

    responses = iter(
        [
            b'{"kind":"OBJ","created":"2025-02-09 20:02:19","size":12,"key":"backup.tar"}',
            flattened_metadata,
        ]
    )

    with mock_asyncio_subprocess_run(responses=responses) as subprocess_exec:
        client = await hass_ws_client(hass)
        await client.send_json_auto_id(
            {"type": "backup/details", "backup_id": backup_id}
        )
        response = await client.receive_json()

        assert response["success"]
        assert response["result"]["agent_errors"] == {}
        assert response["result"]["backup"] == expected_result
        assert subprocess_exec.called


async def test_agents_delete(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test agent delete backup."""

    flattened_metadata = json.dumps(flatten(TEST_AGENT_BACKUP.as_dict())).encode(
        "utf-8"
    )
    responses = iter(
        [
            b'{"kind":"OBJ","created":"2025-02-09 20:02:19","size":12,"key":"backup.tar"}',
            flattened_metadata,
            b"",
        ]
    )
    with mock_asyncio_subprocess_run(responses=responses) as subprocess_exec:
        client = await hass_ws_client(hass)
        await client.send_json_auto_id(
            {
                "type": "backup/delete",
                "backup_id": TEST_AGENT_BACKUP.backup_id,
            }
        )
        response = await client.receive_json()

        assert response["success"]
        assert response["result"] == {"agent_errors": {}}

        assert [mock_call.args for mock_call in subprocess_exec.mock_calls] == snapshot


async def test_agents_delete_fail(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test agent delete backup fails."""
    flattened_metadata = json.dumps(flatten(TEST_AGENT_BACKUP.as_dict())).encode(
        "utf-8"
    )
    responses = iter(
        [
            b'{"kind":"OBJ","created":"2025-02-09 20:02:19","size":12,"key":"backup.tar"}',
            flattened_metadata,
            b"",
        ]
    )

    with mock_asyncio_subprocess_run(
        responses=responses, returncode=iter([0, 1])
    ) as subprocess_exec:
        client = await hass_ws_client(hass)
        await client.send_json_auto_id(
            {
                "type": "backup/delete",
                "backup_id": TEST_AGENT_BACKUP.backup_id,
            }
        )
        response = await client.receive_json()

        assert response["success"]
        assert response["result"] == {
            "agent_errors": {
                TEST_AGENT_ID: f"Failed to delete backup {TEST_AGENT_BACKUP.backup_id}: Unable to delete backup"
            }
        }
        assert [mock_call.args for mock_call in subprocess_exec.mock_calls] == snapshot


async def test_agents_delete_not_found(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test agent delete backup not found."""
    responses = iter(
        [
            b'{"kind":"OBJ","created":"2025-02-09 20:02:19","size":12,"key":"backup.tar"}',
            b"{}",
            b"",
        ]
    )

    with mock_asyncio_subprocess_run(
        responses=responses, returncode=iter([0, 0])
    ) as subprocess_exec:

        client = await hass_ws_client(hass)
        backup_id = "1234"

        await client.send_json_auto_id(
            {
                "type": "backup/delete",
                "backup_id": backup_id,
            }
        )
        response = await client.receive_json()

        assert response["success"]
        assert response["result"] == {"agent_errors": {}}
        assert [mock_call.args for mock_call in subprocess_exec.mock_calls] == snapshot
