import os
import collections
from typing import Optional, Any

from ayon_core.lib.transcoding import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from ayon_core.pipeline.load import get_representation_path_with_anatomy
from ayon_core.pipeline.actions import (
    LoaderActionPlugin,
    LoaderActionItem,
    LoaderActionSelection,
    LoaderActionResult,
)

from ayon_djv.utils import (
    DJVExecutableCache,
    is_djv_executable_available,
    open_local_path_in_djv,
    resolve_djv_sequence_entry_path,
)


class OpenInDJV(LoaderActionPlugin):
    """Open Image Sequence or Video with system default"""
    identifier = "djv.open-in-djv"

    _executable_cache = DJVExecutableCache()
    extensions = set(IMAGE_EXTENSIONS) | set(VIDEO_EXTENSIONS)

    @classmethod
    def get_djv_path(cls):
        return cls._executable_cache.get_path()

    def get_action_items(
        self, selection: LoaderActionSelection
    ) -> list[LoaderActionItem]:
        if not is_djv_executable_available():
            return []

        repres = []
        if selection.selected_type == "representation":
            repres = selection.entities.get_representations(
                selection.selected_ids
            )

        if selection.selected_type == "version":
            repres = selection.entities.get_versions_representations(
                selection.selected_ids
            )

        if not repres:
            return []

        repre_ids_by_name = collections.defaultdict(set)
        for repre in repres:
            repre_context = repre.get("context")
            if not repre_context:
                continue
            ext = repre_context.get("ext")
            if not ext:
                path = repre["attrib"].get("path")
                if path:
                    ext = os.path.splitext(path)[1]

            if ext:
                ext = ext.lower()
                if not ext.startswith("."):
                    ext = f".{ext}"
                if ext not in self.extensions:
                    continue
                name = repre["name"]
                repre_ids_by_name[name].add(repre["id"])

        if not repre_ids_by_name:
            return []

        return [
            LoaderActionItem(
                label=repre_name,
                group_label="Open in DJV",
                order=30,
                data={"representation_id": next(iter(repre_ids))},
                icon={
                    "type": "awesome-font",
                    "name": "fa.play-circle",
                    "color": "orange",
                }
            )
            for repre_name, repre_ids in repre_ids_by_name.items()
            if len(repre_ids) == 1
        ]

    def execute_action(
        self,
        selection: LoaderActionSelection,
        data: dict[str, Any],
        form_values: dict[str, Any],
    ) -> Optional[LoaderActionResult]:
        repre_id = data["representation_id"]
        repre = next(
            iter(selection.entities.get_representations({repre_id})),
            None
        )
        if not repre:
            return LoaderActionResult(
                "Failed to find representation in AYON...",
                success=False,
            )

        repre_path = get_representation_path_with_anatomy(
            repre, selection.get_project_anatomy()
        )
        if not repre_path:
            return LoaderActionResult(
                "Failed to fill representation path...",
                success=False,
            )

        filepath = resolve_djv_sequence_entry_path(repre_path)
        if filepath:
            self.log.info("Opening '%s'", filepath)
        success, message = open_local_path_in_djv(
            repre_path,
            executable_cache=self._executable_cache,
        )
        return LoaderActionResult(message, success=success)
