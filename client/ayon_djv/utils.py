import os
import time
import platform
from typing import Optional, Tuple

import ayon_api
import clique

from ayon_core.lib import run_detached_process

from .version import __version__
from .constants import ADDON_NAME

_DEFAULT_EXECUTABLE_CACHE = None


def get_djv_icon_url(server_url=None):
    """Get URL to DJV icon.

    Args:
        server_url (Optional[str]): AYON server URL.

    Returns:
        str: URL where DJV icon is located.
    """

    server_url = server_url or ayon_api.get_base_url()
    return "{}/addons/{}/{}/public/djv.png".format(
        server_url, ADDON_NAME, __version__
    )


def get_djv_paths_from_settings(addon_settings=None):
    """

    Args:
        addon_settings (Optional[dict[str, Any]): Addon settings.

    Returns:
        list[str]: List to DJV executable paths. Paths are not validated.
    """

    if addon_settings is None:
        addon_settings = ayon_api.get_addon_settings(ADDON_NAME, __version__)

    platform_name = platform.system().lower()
    return addon_settings.get("djv_path", {}).get(platform_name, [])


def get_djv_executable_path(paths=None, addon_settings=None):
    """

    Args:
        paths (Optional[list[str]]): List of paths to DJV executable.
        addon_settings (Optional[dict[str, Any]): Addon settings.

    Returns:
        list[str]: List of available paths to DJV executable.
    """

    if paths is None:
        paths = get_djv_paths_from_settings(addon_settings)

    for path in paths:
        if path and os.path.exists(path):
            return path
    return None


class DJVExecutableCache:
    lifetime = 10

    def __init__(self):
        self._cached_time = None
        self._djv_paths = None
        self._djv_path = None

    def is_cache_valid(self):
        """Cache is valid.

        Returns:
            bool: True if cache is valid, False otherwise.
        """

        if self._cached_time is None:
            return False

        start = time.time()
        return (start - self._cached_time) <= self.lifetime

    def get_paths(self):
        """Get all paths to DJV executable from settings.

        Returns:
            list[str]: Path to DJV executables.
        """

        if not self.is_cache_valid():
            self._djv_paths = get_djv_paths_from_settings()
            self._cached_time = time.time()
        return self._djv_paths

    def get_path(self):
        """Get path to DJV executable.

        Returns:
            Union[str, None]: Path to DJV executable or None.
        """

        if not self.is_cache_valid():
            self._djv_path = get_djv_executable_path(self.get_paths())
        return self._djv_path


def _executable_cache() -> DJVExecutableCache:
    global _DEFAULT_EXECUTABLE_CACHE
    if _DEFAULT_EXECUTABLE_CACHE is None:
        _DEFAULT_EXECUTABLE_CACHE = DJVExecutableCache()
    return _DEFAULT_EXECUTABLE_CACHE


def is_djv_executable_available() -> bool:
    """Return True when addon settings resolve to an existing DJV executable."""
    return bool(_executable_cache().get_path())


def resolve_djv_sequence_entry_path(file_path: str) -> str:
    """Pick the first frame path DJV should open for a file or sequence member."""
    repre_path = os.path.normpath(str(file_path or "").strip())
    if not repre_path:
        return ""
    if not os.path.exists(repre_path):
        return ""
    directory = os.path.dirname(repre_path)
    if not directory or not os.path.isdir(directory):
        return repre_path
    pattern = clique.PATTERNS["frames"]
    try:
        files = os.listdir(directory)
    except OSError:
        return repre_path
    collections, remainder = clique.assemble(
        files,
        patterns=[pattern],
        minimum_items=1,
    )
    first_image = repre_path
    if not remainder and collections:
        sequence = collections[0]
        first_image = list(sequence)[0]
    return os.path.normpath(os.path.join(directory, first_image))


def open_local_path_in_djv(
    file_path: str,
    *,
    executable_cache: Optional[DJVExecutableCache] = None,
) -> Tuple[bool, str]:
    """Launch DJV for a local image sequence or video path.

    Returns:
        (success, user-facing message)
    """
    cache = executable_cache or _executable_cache()
    executable = cache.get_path()
    if not executable:
        return False, "Couldn't find DJV executable."

    filepath = resolve_djv_sequence_entry_path(file_path)
    if not filepath or not os.path.exists(filepath):
        return False, "File to open was not found..."

    run_detached_process([str(executable), filepath])
    time.sleep(0.1)
    return True, "File opened in DJV..."
