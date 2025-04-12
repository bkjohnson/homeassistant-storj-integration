"""API for Home Assistant to interact with Storj."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Coroutine
import json
import logging
import os
from pathlib import Path
import tempfile
from typing import Any

import aiofiles
from aiofiles.os import remove as aioremove
from homeassistant.components.backup import AgentBackup, suggested_filename
from homeassistant.exceptions import HomeAssistantError
from icmplib import async_ping  # type: ignore
from json_flatten import flatten, unflatten  # type: ignore
from storj_uplink.module_classes import ListObjectsOptions
from storj_uplink.uplink import Uplink

from .helpers import ChunkAsyncStreamIterator

_LOGGER = logging.getLogger(__name__)


class StorjClient:
    """Client for Storj uplink CLI tool."""

    def __init__(
        self,
        ha_instance_id: str,
        bucket_name: str,
        access_grant: str,
    ) -> None:
        """Initialize."""
        self._ha_instance_id = ha_instance_id
        self.bucket_name = bucket_name
        self.access_grant = access_grant
        self._uplink = Uplink()
        self._access = self._uplink.parse_access(access_grant)
        self._project = self._access.open_project()

    async def install_uplink(self) -> bool:
        """Intall the uplink binary if it is not already installed"""
        which_proc = await asyncio.create_subprocess_exec(
            "which",
            "uplink",
        )
        await which_proc.communicate()
        if which_proc.returncode == 0:
            return True

        curl_proc = await asyncio.create_subprocess_exec(
            "curl",
            "-L",
            "https://github.com/storj/storj/releases/latest/download/uplink_linux_arm64.zip",
            "-o",
            "uplink_linux_arm64.zip",
        )
        await curl_proc.communicate()
        assert curl_proc.returncode == 0

        unzip_proc = await asyncio.create_subprocess_exec(
            "unzip", "-o", "uplink_linux_arm64.zip"
        )
        await unzip_proc.communicate()
        assert unzip_proc.returncode == 0

        install_proc = await asyncio.create_subprocess_exec(
            "install", "uplink", "/usr/local/bin/uplink"
        )
        await install_proc.communicate()
        assert install_proc.returncode == 0

        return True

    async def authenticate(self) -> bool:
        """Test if we can authenticate with the host."""

        result = await asyncio.create_subprocess_exec(
            "uplink", "access", "import", "ha2", self.access_grant, "--force"
        )
        await result.communicate()

        return result.returncode == 0

    async def satelitte_is_live(self) -> bool:
        """Check to see if the satellite contained in the access grant is reachable."""

        sat_addr = self._access.satellite_address()
        url = sat_addr.split("@")[-1]

        # We don't want the port
        host = url.split(":")[0]

        _LOGGER.debug("Checking to see if Storj satellite %s can be reached", host)
        host = await async_ping(host, privileged=False)

        return host.is_alive

    async def async_upload_backup(
        self,
        open_stream: Callable[[], Coroutine[Any, Any, AsyncIterator[bytes]]],
        backup: AgentBackup,
    ) -> None:
        """Upload a backup."""

        backup_metadata = flatten(backup.as_dict())
        tempfile.tempdir = None
        os.environ["TMPDIR"] = str(Path.home())
        _LOGGER.debug(
            "TMPDIR reset to: %s",
            os.environ["TMPDIR"],
        )

        _LOGGER.debug(
            "Uploading backup: %s as %s with metadata: %s",
            backup.backup_id,
            suggested_filename(backup),
            backup_metadata,
        )
        with tempfile.NamedTemporaryFile(mode="ab") as fp:
            async for chunk in await open_stream():
                fp.write(chunk)
            result = await asyncio.create_subprocess_exec(
                "uplink",
                "cp",
                fp.name,
                f"sj://{self.bucket_name}/backups/{suggested_filename(backup)}",
                "--metadata",
                json.dumps(backup_metadata),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()
            fp.close()
            if result.returncode != 0:
                _LOGGER.error(
                    "Error during upload - [stdout]: %s [stderr]: %s",
                    stdout.decode(),
                    stderr.decode(),
                )
                raise UplinkError("Unable to complete upload")

            _LOGGER.debug(
                "Uploaded backup: %s to '%s'", backup.backup_id, self.bucket_name
            )

    async def async_list_backups(self) -> list[AgentBackup]:
        """List the backups currently in the bucket."""

        options = ListObjectsOptions(prefix="backups/", custom=True)
        storj_objs = self._project.list_objects(self.bucket_name, options)

        backups: list[AgentBackup] = []
        for ob in storj_objs:
            flattened_object_metadata = {x.key: x.value for x in ob.custom.entries}
            metadata_dict = unflatten(flattened_object_metadata)
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

    async def async_download_backup(
        self, backup: AgentBackup, backup_path: Path
    ) -> AsyncIterator[bytes]:
        """Download a backup to the local system."""

        temp_location = str(backup_path.joinpath("temp", suggested_filename(backup)))
        result = await asyncio.create_subprocess_exec(
            "uplink",
            "cp",
            f"sj://{self.bucket_name}/backups/{suggested_filename(backup)}",
            temp_location,
        )
        await result.communicate()
        if result.returncode != 0:
            raise UplinkError("Unable to download temp backup")

        file_obj = await aiofiles.open(temp_location, "rb")
        iterator = ChunkAsyncStreamIterator(await file_obj.read())
        await file_obj.close()
        await aioremove(temp_location)

        return iterator


class UplinkError(HomeAssistantError):
    """Error to indicate there is a problem calling uplink."""
