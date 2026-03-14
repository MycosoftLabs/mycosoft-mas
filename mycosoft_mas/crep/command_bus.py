"""
CREP Command Bus — Mar 13, 2026

Validates, logs, and emits CREP map commands for website consumption.
All safe CREP tools (crep_fly_to, crep_show_layer, etc.) delegate here.
Implements the canonical CREP command contract.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Canonical CREP map command types (camelCase)
VALID_MAP_TYPES = frozenset({
    "flyTo", "geocodeAndFlyTo", "setZoom", "zoomBy", "panBy",
    "showLayer", "hideLayer", "toggleLayer", "applyFilter", "clearFilters",
    "getEntityDetails", "getViewContext", "setTimeCursor", "timelineSearch",
    "getSystemStatus", "setMute",
})

# High-risk commands requiring confirmation (bulk/timeline mutation)
REQUIRES_CONFIRMATION = frozenset({"clearFilters"})


class CrepCommandBus:
    """
    Safe CREP command bus: validates, logs, and produces website-consumable
    frontend_command objects. Used by CREP tools and autonomous MYCA.
    """

    def __init__(self):
        self._command_log: list = []

    def execute(
        self,
        tool_name: str,
        args: Dict[str, Any],
        confirmed: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute a CREP tool and return frontend_command + speak.
        For high-risk commands, confirmed must be True.
        """
        try:
            cmd = self._build_command(tool_name, args)
            if cmd is None:
                return {"success": False, "error": f"Unknown or invalid tool: {tool_name}"}

            frontend_type = cmd.get("type", "")
            if frontend_type in REQUIRES_CONFIRMATION and not confirmed:
                return {
                    "success": False,
                    "requires_confirmation": True,
                    "message": f"Command '{frontend_type}' requires user confirmation.",
                }

            self._log_command(tool_name, cmd)
            speak = self._speak_for_command(tool_name, args, cmd)
            return {
                "success": True,
                "frontend_command": cmd,
                "speak": speak,
            }
        except Exception as e:
            logger.exception("CrepCommandBus execute failed: %s", e)
            return {"success": False, "error": str(e)}

    def _build_command(self, tool_name: str, args: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Build canonical frontend_command from tool name and args."""
        handlers = {
            "crep_fly_to": self._cmd_fly_to,
            "crep_geocode_and_fly_to": self._cmd_geocode_and_fly_to,
            "crep_set_layer_visibility": self._cmd_set_layer_visibility,
            "crep_toggle_layer": self._cmd_toggle_layer,
            "crep_apply_filter": self._cmd_apply_filter,
            "crep_clear_filters": self._cmd_clear_filters,
            "crep_get_view_context": self._cmd_get_view_context,
            "crep_get_entity_details": self._cmd_get_entity_details,
            "crep_set_time_cursor": self._cmd_set_time_cursor,
            "crep_timeline_search": self._cmd_timeline_search,
            "crep_set_zoom": self._cmd_set_zoom,
            "crep_zoom_by": self._cmd_zoom_by,
            "crep_pan_by": self._cmd_pan_by,
        }
        handler = handlers.get(tool_name)
        if handler is None:
            return None
        return handler(args)

    def _cmd_fly_to(self, args: Dict[str, Any]) -> Dict[str, Any]:
        center = args.get("center")
        if not center or not isinstance(center, (list, tuple)) or len(center) < 2:
            raise ValueError("crep_fly_to requires center: [lon, lat]")
        lon, lat = float(center[0]), float(center[1])
        cmd = {"type": "flyTo", "center": [lon, lat]}
        if "zoom" in args:
            cmd["zoom"] = int(args["zoom"])
        if "duration" in args:
            cmd["duration"] = int(args["duration"])
        return cmd

    def _cmd_geocode_and_fly_to(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = args.get("query") or args.get("location")
        if not query:
            raise ValueError("crep_geocode_and_fly_to requires query or location")
        cmd = {"type": "geocodeAndFlyTo", "query": str(query)}
        if "zoom" in args:
            cmd["zoom"] = int(args["zoom"])
        if "duration" in args:
            cmd["duration"] = int(args["duration"])
        return cmd

    def _cmd_set_layer_visibility(self, args: Dict[str, Any]) -> Dict[str, Any]:
        layer = args.get("layer")
        visible = args.get("visible", True)
        if not layer:
            raise ValueError("crep_set_layer_visibility requires layer")
        cmd_type = "showLayer" if visible else "hideLayer"
        return {"type": cmd_type, "layer": str(layer)}

    def _cmd_toggle_layer(self, args: Dict[str, Any]) -> Dict[str, Any]:
        layer = args.get("layer")
        if not layer:
            raise ValueError("crep_toggle_layer requires layer")
        return {"type": "toggleLayer", "layer": str(layer)}

    def _cmd_apply_filter(self, args: Dict[str, Any]) -> Dict[str, Any]:
        ft = args.get("filter_type") or args.get("filterType")
        fv = args.get("filter_value") or args.get("filterValue")
        if not ft:
            raise ValueError("crep_apply_filter requires filter_type")
        return {"type": "applyFilter", "filterType": str(ft), "filterValue": fv}

    def _cmd_clear_filters(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"type": "clearFilters"}

    def _cmd_get_view_context(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"type": "getViewContext"}

    def _cmd_get_entity_details(self, args: Dict[str, Any]) -> Dict[str, Any]:
        entity = args.get("entity")
        if entity is None:
            raise ValueError("crep_get_entity_details requires entity")
        return {"type": "getEntityDetails", "entity": entity}

    def _cmd_set_time_cursor(self, args: Dict[str, Any]) -> Dict[str, Any]:
        time_val = args.get("time")
        if not time_val:
            raise ValueError("crep_set_time_cursor requires time (ISO8601)")
        return {"type": "setTimeCursor", "time": str(time_val)}

    def _cmd_timeline_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = args.get("query")
        if not query:
            raise ValueError("crep_timeline_search requires query")
        return {"type": "timelineSearch", "query": str(query)}

    def _cmd_set_zoom(self, args: Dict[str, Any]) -> Dict[str, Any]:
        zoom = args.get("zoom")
        if zoom is None:
            raise ValueError("crep_set_zoom requires zoom")
        cmd = {"type": "setZoom", "zoom": int(zoom)}
        if "duration" in args:
            cmd["duration"] = int(args["duration"])
        return cmd

    def _cmd_zoom_by(self, args: Dict[str, Any]) -> Dict[str, Any]:
        delta = args.get("delta", 2)
        cmd = {"type": "zoomBy", "delta": int(delta)}
        if "duration" in args:
            cmd["duration"] = int(args["duration"])
        return cmd

    def _cmd_pan_by(self, args: Dict[str, Any]) -> Dict[str, Any]:
        offset = args.get("offset")
        if not offset or not isinstance(offset, (list, tuple)) or len(offset) < 2:
            raise ValueError("crep_pan_by requires offset: [dx, dy]")
        cmd = {"type": "panBy", "offset": [int(offset[0]), int(offset[1])]}
        if "duration" in args:
            cmd["duration"] = int(args["duration"])
        return cmd

    def _speak_for_command(
        self, tool_name: str, args: Dict[str, Any], cmd: Dict[str, Any]
    ) -> str:
        """Generate speak text for the command."""
        t = cmd.get("type", "")
        if t == "flyTo":
            return "Flying to the specified location."
        if t == "geocodeAndFlyTo":
            return f"Navigating to {cmd.get('query', 'that location')}."
        if t == "showLayer":
            return f"Showing {cmd.get('layer', '')} layer."
        if t == "hideLayer":
            return f"Hiding {cmd.get('layer', '')} layer."
        if t == "toggleLayer":
            return f"Toggling {cmd.get('layer', '')} layer."
        if t == "applyFilter":
            return f"Applying filter: {cmd.get('filterType', '')} = {cmd.get('filterValue', '')}."
        if t == "clearFilters":
            return "Clearing all filters."
        if t == "getViewContext":
            return "Getting current view context."
        if t == "getEntityDetails":
            return f"Looking up details for {cmd.get('entity', 'that entity')}."
        if t == "setTimeCursor":
            return f"Setting timeline to {cmd.get('time', '')}."
        if t == "timelineSearch":
            return f"Searching timeline for {cmd.get('query', '')}."
        if t in ("setZoom", "zoomBy"):
            return "Adjusting zoom."
        if t == "panBy":
            return "Panning the map."
        return "CREP command executed."

    def _log_command(self, tool_name: str, cmd: Dict[str, Any]) -> None:
        """Log command for audit trail."""
        entry = {
            "tool": tool_name,
            "type": cmd.get("type"),
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        self._command_log.append(entry)
        if len(self._command_log) > 500:
            self._command_log = self._command_log[-400:]
        logger.info("CREP command: %s -> %s", tool_name, cmd.get("type"))


_bus: Optional[CrepCommandBus] = None


def get_crep_command_bus() -> CrepCommandBus:
    """Get the CrepCommandBus singleton."""
    global _bus
    if _bus is None:
        _bus = CrepCommandBus()
    return _bus
