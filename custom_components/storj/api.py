"""API for Home Assistant to interact with Storj."""

from __future__ import annotations

import asyncio
import logging
import json
from icmplib import async_ping

from homeassistant.components.backup import AgentBackup, suggested_filename
from homeassistant.exceptions import HomeAssistantError

from json_flatten import flatten, unflatten

_LOGGER = logging.getLogger(__name__)


class StorjClient:
    """Client for Storj uplink CLI tool."""

    def __init__(
        self,
        ha_instance_id: str,
        bucket_name: str,
    ) -> None:
        """Initialize."""
        self._ha_instance_id = ha_instance_id
        self.bucket_name = bucket_name

    async def authenticate(self, access_grant: str) -> bool:
        """Test if we can authenticate with the host."""
        result = await asyncio.create_subprocess_exec(
            "uplink", "access", "import", "ha2", access_grant
        )
        await result.communicate()

        return result.returncode == 0

    async def satelitte_is_live(self) -> bool:
        """Check to see if the satellite contained in the access grant is reachable."""

        result = await asyncio.create_subprocess_exec(
            "uplink",
            "access",
            "inspect",
            "ha2",
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await result.communicate()
        json_access = json.loads(stdout.decode())
        url = json_access["satellite_addr"].split("@")[-1]
        # We don't want the port
        host = url.split(":")[0]

        _LOGGER.debug("Checking to see if Storj satellite %s can be reached", host)
        host = await async_ping(host, privileged=False)

        return host.is_alive

    async def async_upload_backup(
        self,
        backup_dir: str,
        backup: AgentBackup,
    ) -> None:
        """Upload a backup."""

        backup_metadata = flatten(backup.as_dict())
        _LOGGER.debug(
            "Uploading backup: %s as %s with metadata: %s",
            backup.backup_id,
            suggested_filename(backup),
            backup_metadata,
        )

        backup_location = f"{backup_dir}/{suggested_filename(backup)}"
        result = await asyncio.create_subprocess_exec(
            "uplink",
            "cp",
            backup_location,
            f"sj://{self.bucket_name}/backups/",
            "--metadata",
            json.dumps(backup_metadata),
        )
        await result.communicate()
        if result.returncode != 0:
            raise UplinkError("Unable to complete upload")

        _LOGGER.debug("Uploaded backup: %s to '%s'", backup.backup_id, self.bucket_name)

    async def _get_metadata(self, filename: str) -> dict[str, str]:
        result = await asyncio.create_subprocess_exec(
            "uplink",
            "meta",
            "get",
            f"sj://{self.bucket_name}/backups/{filename}",
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await result.communicate()

        return json.loads(stdout.decode())

    async def async_list_backups(self) -> list[AgentBackup]:
        """List the backups currently in the bucket."""

        result = await asyncio.create_subprocess_exec(
            "uplink",
            "ls",
            f"sj://{self.bucket_name}/backups/",
            "--o",
            "json",
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await result.communicate()
        if result.returncode != 0:
            raise UplinkError("Unable to fetch backup data")

        storj_objs = [json.loads(ob) for ob in stdout.decode().split("\n") if ob]

        backups: list[AgentBackup] = []
        for ob in storj_objs:
            metadata = await self._get_metadata(ob["key"])
            metadata_dict = unflatten(metadata)
            if "homeassistant_version" in metadata_dict.keys():
                backup = AgentBackup.from_dict(metadata_dict)
                backups.append(backup)

        return backups

    async def async_delete_backup(self, backup: AgentBackup) -> None:
        """Delete a specified backup from the bucket."""

        result = await asyncio.create_subprocess_exec(
            "uplink",
            "rm",
            f"sj://{self.bucket_name}/backups/{suggested_filename(backup)}",
        )
        await result.communicate()
        if result.returncode != 0:
            raise UplinkError("Unable to delete backup")

    async def async_download_backup(self) -> None:
        """Download a backup to the local system."""
        _LOGGER.debug("TODO")


class UplinkError(HomeAssistantError):
    """Error to indicate there is a problem calling uplink."""
