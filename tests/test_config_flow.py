"""Test Storj config flow."""

from unittest.mock import AsyncMock, patch
from typing import Any

from homeassistant import config_entries
from custom_components.storj.const import DOMAIN, CONF_ACCESS_GRANT, CONF_BUCKET_NAME
from syrupy.assertion import SnapshotAssertion
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import json

from .conftest import mock_asyncio_subprocess_run


async def test_form(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    access_json: dict[str, Any],
    snapshot: SnapshotAssertion,
) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    responses = iter([b"", json.dumps(access_json).encode("utf-8")])

    with (
        mock_asyncio_subprocess_run(responses=responses) as subprocess_exec,
        patch(
            "custom_components.storj.api.async_ping",
            return_value=AsyncMock(is_alive=True),
        ) as mocked_ping,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_ACCESS_GRANT: "abc123xyz",
                CONF_BUCKET_NAME: "my-backups",
            },
        )
        await hass.async_block_till_done()
        assert [mock_call.args for mock_call in subprocess_exec.mock_calls] == snapshot
        assert snapshot() == mocked_ping.mock_calls[0].args

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Storj"
    assert result["data"] == {
        CONF_ACCESS_GRANT: "abc123xyz",
        CONF_BUCKET_NAME: "my-backups",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,
    access_json: dict[str, Any],
    snapshot: SnapshotAssertion,
) -> None:
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    responses = iter([b"", json.dumps(access_json).encode("utf-8")])
    with (
        mock_asyncio_subprocess_run(
            responses=responses, returncode=1
        ) as subprocess_exec,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_ACCESS_GRANT: "abc123xyz",
                CONF_BUCKET_NAME: "my-backups",
            },
        )
        assert [mock_call.args for mock_call in subprocess_exec.mock_calls] == snapshot

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    responses = iter([b"", json.dumps(access_json).encode("utf-8")])
    # Make sure the config flow tests finish with either an
    # FlowResultType.CREATE_ENTRY or FlowResultType.ABORT so
    # we can show the config flow is able to recover from an error.
    with (
        mock_asyncio_subprocess_run(responses=responses, returncode=0),
        patch(
            "custom_components.storj.api.async_ping",
            return_value=AsyncMock(is_alive=True),
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_ACCESS_GRANT: "abc123xyz",
                CONF_BUCKET_NAME: "my-backups",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Storj"
    assert result["data"] == {
        CONF_ACCESS_GRANT: "abc123xyz",
        CONF_BUCKET_NAME: "my-backups",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(
    hass: HomeAssistant,
    access_json: dict[str, Any],
    mock_setup_entry: AsyncMock,
    snapshot: SnapshotAssertion,
) -> None:
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    responses = iter([b"", json.dumps(access_json).encode("utf-8")])

    with (
        mock_asyncio_subprocess_run(responses=responses) as subprocess_exec,
        patch(
            "custom_components.storj.api.async_ping",
            return_value=AsyncMock(is_alive=False),
        ) as mocked_ping,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_ACCESS_GRANT: "abc123xyz",
                CONF_BUCKET_NAME: "my-backups",
            },
        )
        await hass.async_block_till_done()
        assert [mock_call.args for mock_call in subprocess_exec.mock_calls] == snapshot
        assert snapshot() == mocked_ping.mock_calls[0].args

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    # Make sure the config flow tests finish with either an
    # FlowResultType.CREATE_ENTRY or FlowResultType.ABORT so
    # we can show the config flow is able to recover from an error.

    responses = iter([b"", json.dumps(access_json).encode("utf-8")])
    with (
        mock_asyncio_subprocess_run(responses=responses),
        patch(
            "custom_components.storj.api.async_ping",
            return_value=AsyncMock(is_alive=True),
        ) as mocked_ping,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_ACCESS_GRANT: "abc123xyz",
                CONF_BUCKET_NAME: "my-backups",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Storj"
    assert result["data"] == {
        CONF_ACCESS_GRANT: "abc123xyz",
        CONF_BUCKET_NAME: "my-backups",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_unknown_error(
    hass: HomeAssistant,
    access_json: dict[str, Any],
    mock_setup_entry: AsyncMock,
    snapshot: SnapshotAssertion,
) -> None:
    """Test we handle unknown error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch(
            "custom_components.storj.api.StorjClient.authenticate",
            side_effect=Exception,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_ACCESS_GRANT: "abc123xyz",
                CONF_BUCKET_NAME: "my-backups",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unknown"
