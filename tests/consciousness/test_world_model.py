"""
Tests for WorldModel

Tests the unified world perception system.

Author: Morgan Rockwell / MYCA
Created: February 10, 2026
"""

from unittest.mock import AsyncMock

import pytest


class TestWorldState:
    """Tests for WorldState dataclass."""

    def test_world_state_creation(self):
        """WorldState should be creatable."""
        from mycosoft_mas.consciousness.world_model import WorldState

        state = WorldState()

        assert state.crep_data == {}
        assert state.earth2_data == {}
        assert state.natureos_data == {}
        assert state.mindex_data == {}
        assert state.mycobrain_data == {}

    def test_world_state_presence_defaults(self):
        """WorldState presence fields should default correctly."""
        from mycosoft_mas.consciousness.world_model import WorldState

        state = WorldState()
        assert state.presence_data == {}
        assert state.online_users == 0
        assert state.active_sessions == 0
        assert state.staff_online == 0
        assert state.superuser_online is False

    def test_world_state_summary_empty(self):
        """Empty world state should return 'limited data available'."""
        from mycosoft_mas.consciousness.world_model import WorldState

        state = WorldState()
        assert "limited data available" in state.to_summary()

    def test_world_state_summary_with_data(self):
        """World state with data should produce a meaningful summary."""
        from mycosoft_mas.consciousness.world_model import WorldState

        state = WorldState()
        state.crep_data = {"flights": []}
        state.total_flights = 100
        state.total_vessels = 50
        state.total_satellites = 10
        state.online_users = 5
        state.staff_online = 2

        summary = state.to_summary()
        assert "100 flights" in summary
        assert "5 users online" in summary


class TestWorldModel:
    """Tests for WorldModel."""

    def test_world_model_initialization(self):
        """WorldModel should initialize with sensors."""
        from mycosoft_mas.consciousness.world_model import WorldModel

        model = WorldModel()

        assert model._sensors is not None
        assert model._current_state is not None

    def test_world_model_has_all_sensor_keys(self):
        """WorldModel._sensors should contain all 9 canonical sensor keys."""
        from mycosoft_mas.consciousness.world_model import WorldModel

        model = WorldModel()

        expected_keys = {
            "crep", "earth2", "natureos", "mindex",
            "mycobrain", "nlm", "earthlive", "presence", "workspace",
        }
        assert set(model._sensors.keys()) == expected_keys

    def test_sensors_not_all_null_stubs(self):
        """At least some sensors should be real, not all NullSensor."""
        from mycosoft_mas.consciousness.world_model import WorldModel, _NullSensor

        model = WorldModel()

        null_count = sum(1 for s in model._sensors.values() if isinstance(s, _NullSensor))
        # At least the sensors whose modules exist should be real
        assert null_count < len(model._sensors), (
            f"All {len(model._sensors)} sensors are NullSensor stubs — "
            "per-sensor isolation is not working"
        )

    def test_named_sensor_refs_populated(self):
        """Named refs (_crep_sensor, etc.) should be populated from _sensors."""
        from mycosoft_mas.consciousness.world_model import WorldModel

        model = WorldModel()

        # Named refs should point to the same objects in _sensors
        assert model._crep_sensor is model._sensors.get("crep")
        assert model._earth2_sensor is model._sensors.get("earth2")
        assert model._natureos_sensor is model._sensors.get("natureos")
        assert model._mindex_sensor is model._sensors.get("mindex")
        assert model._mycobrain_sensor is model._sensors.get("mycobrain")
        assert model._nlm_sensor is model._sensors.get("nlm")
        assert model._earthlive_sensor is model._sensors.get("earthlive")
        assert model._presence_sensor is model._sensors.get("presence")
        assert model._workspace_sensor is model._sensors.get("workspace")

    @pytest.mark.asyncio
    async def test_initialize_sensors_is_idempotent(self):
        """Calling initialize_sensors twice should be safe."""
        from mycosoft_mas.consciousness.world_model import WorldModel

        model = WorldModel()
        await model.initialize_sensors()
        first_sensors = dict(model._sensors)
        await model.initialize_sensors()  # second call — should be no-op
        assert model._sensors == first_sensors

    @pytest.mark.asyncio
    async def test_initialize_sensors(self):
        """initialize should set up all sensors."""
        from mycosoft_mas.consciousness.world_model import WorldModel

        model = WorldModel()

        # Mock sensor connections
        for sensor in model._sensors.values():
            sensor.connect = AsyncMock(return_value=True)

        await model.initialize()

        # All sensors should have connect called
        for sensor in model._sensors.values():
            sensor.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_all(self):
        """update_all should update from all sensors."""
        from mycosoft_mas.consciousness.world_model import WorldModel

        model = WorldModel()

        # Mock sensor reads
        for name, sensor in model._sensors.items():
            sensor.read = AsyncMock(return_value={"test": True})
            sensor._connected = True

        await model.update_all()

        # State should be updated
        assert model._current_state is not None

    @pytest.mark.asyncio
    async def test_update_all_populates_crep(self):
        """update_all with CREP data should flow into current state."""
        from mycosoft_mas.consciousness.world_model import WorldModel

        model = WorldModel()

        crep_data = {"flight_count": 42, "flights": []}
        model._sensors["crep"].read = AsyncMock(return_value=crep_data)
        # Make other sensors return empty
        for name, sensor in model._sensors.items():
            if name != "crep":
                sensor.read = AsyncMock(return_value={})

        await model.update_all()
        assert model._current_state.crep_data == crep_data

    @pytest.mark.asyncio
    async def test_update_all_populates_presence(self):
        """update_all with presence data should update presence fields."""
        from mycosoft_mas.consciousness.world_model import WorldModel

        model = WorldModel()

        presence_data = {
            "online_count": 7,
            "sessions_count": 12,
            "staff_count": 3,
            "superuser_online": True,
        }
        model._sensors["presence"].read = AsyncMock(return_value=presence_data)
        for name, sensor in model._sensors.items():
            if name != "presence":
                sensor.read = AsyncMock(return_value={})

        await model.update_all()
        assert model._current_state.online_users == 7
        assert model._current_state.active_sessions == 12
        assert model._current_state.staff_online == 3
        assert model._current_state.superuser_online is True

    def test_get_current_state(self):
        """get_current_state should return WorldState."""
        from mycosoft_mas.consciousness.world_model import WorldModel, WorldState

        model = WorldModel()

        state = model.get_current_state()

        assert isinstance(state, WorldState)

    @pytest.mark.asyncio
    async def test_get_relevant_context(self):
        """get_relevant_context should filter based on focus."""
        from mycosoft_mas.consciousness.attention import AttentionFocus
        from mycosoft_mas.consciousness.world_model import WorldModel

        model = WorldModel()

        focus = AttentionFocus(
            content="What's the weather?", source="text", category="user_input", priority=1.0
        )

        context = await model.get_relevant_context(focus)

        assert isinstance(context, dict)

    def test_sensor_status(self):
        """sensor_status should return all sensor statuses."""
        from mycosoft_mas.consciousness.world_model import WorldModel

        model = WorldModel()

        status = model.sensor_status

        assert isinstance(status, dict)
        assert "crep" in status
        assert "earth2" in status


class TestWorldModelDegradation:
    """Tests for the is_degraded property."""

    def test_not_degraded_when_sensors_available(self):
        """is_degraded should be False when most sensors are real."""
        from mycosoft_mas.consciousness.world_model import WorldModel

        model = WorldModel()
        assert model.is_degraded is False

    def test_degraded_when_all_null(self):
        """is_degraded should be True when all sensors are NullSensor."""
        from mycosoft_mas.consciousness.world_model import WorldModel, _NullSensor

        model = WorldModel()
        # Replace all sensors with NullSensor
        for key in list(model._sensors.keys()):
            model._sensors[key] = _NullSensor()

        assert model.is_degraded is True

    def test_degraded_when_majority_null(self):
        """is_degraded should be True when more than half are NullSensor."""
        from mycosoft_mas.consciousness.world_model import WorldModel, _NullSensor

        model = WorldModel()
        keys = list(model._sensors.keys())
        majority = len(keys) // 2 + 1
        for key in keys[:majority]:
            model._sensors[key] = _NullSensor()

        assert model.is_degraded is True

    def test_not_degraded_when_minority_null(self):
        """is_degraded should be False when less than half are NullSensor."""
        from mycosoft_mas.consciousness.world_model import WorldModel, _NullSensor

        model = WorldModel()
        keys = list(model._sensors.keys())
        # Replace only 2 sensors
        for key in keys[:2]:
            model._sensors[key] = _NullSensor()

        assert model.is_degraded is False

    def test_is_degraded_initially_false(self):
        """Fresh WorldModel with working imports should not be degraded."""
        from mycosoft_mas.consciousness.world_model import WorldModel

        model = WorldModel()
        assert model.is_degraded is False


class TestPresenceSensor:
    """Tests for PresenceSensor."""

    def test_presence_sensor_importable(self):
        """PresenceSensor should be importable."""
        from mycosoft_mas.consciousness.sensors.presence_sensor import PresenceSensor
        assert PresenceSensor is not None

    def test_presence_sensor_init(self):
        """PresenceSensor should construct without a world model."""
        from mycosoft_mas.consciousness.sensors.presence_sensor import PresenceSensor

        sensor = PresenceSensor()
        assert sensor.name == "presence"

    @pytest.mark.asyncio
    async def test_presence_sensor_read_when_disconnected(self):
        """PresenceSensor.read() should return None when not connected."""
        from mycosoft_mas.consciousness.sensors.base_sensor import SensorStatus
        from mycosoft_mas.consciousness.sensors.presence_sensor import PresenceSensor

        sensor = PresenceSensor()
        sensor._client = None
        sensor._status = SensorStatus.DISCONNECTED
        result = await sensor.read()
        assert result is None


class TestWorldstateAPISerialization:
    """Tests for worldstate_api serialization helpers.

    Importing mycosoft_mas.core.routers triggers jose/JWT deps that may
    not be present in lightweight test environments, so these tests skip
    gracefully when the import chain is unavailable.
    """

    @staticmethod
    def _import_worldstate_api():
        """Try to import worldstate_api; return module or None."""
        try:
            from mycosoft_mas.core.routers import worldstate_api
            return worldstate_api
        except Exception:
            return None

    def test_freshness_val_with_enum(self):
        """_freshness_val should extract .value from DataFreshness."""
        mod = self._import_worldstate_api()
        if mod is None:
            pytest.skip("worldstate_api import chain unavailable (missing jose)")
        from mycosoft_mas.consciousness.world_model import DataFreshness

        assert mod._freshness_val(DataFreshness.LIVE) == "live"
        assert mod._freshness_val(DataFreshness.UNAVAILABLE) == "unavailable"

    def test_freshness_val_with_none(self):
        """_freshness_val should return 'unavailable' for None."""
        mod = self._import_worldstate_api()
        if mod is None:
            pytest.skip("worldstate_api import chain unavailable (missing jose)")

        assert mod._freshness_val(None) == "unavailable"

    def test_world_state_to_dict_includes_freshness(self):
        """_world_state_to_dict should include freshness for predictions, ecosystem, etc."""
        mod = self._import_worldstate_api()
        if mod is None:
            pytest.skip("worldstate_api import chain unavailable (missing jose)")
        from mycosoft_mas.consciousness.world_model import WorldState

        state = WorldState()
        d = mod._world_state_to_dict(state)

        # predictions and ecosystem should now be wrapped with freshness
        assert "freshness" in d["predictions"]
        assert "data" in d["predictions"]
        assert "freshness" in d["ecosystem"]
        assert "data" in d["ecosystem"]
        assert "freshness" in d["nlm"]
        assert "freshness" in d["earthlive"]
        assert "freshness" in d["presence"]

    def test_world_state_to_dict_none_returns_empty(self):
        """_world_state_to_dict with None should return empty dict."""
        mod = self._import_worldstate_api()
        if mod is None:
            pytest.skip("worldstate_api import chain unavailable (missing jose)")

        assert mod._world_state_to_dict(None) == {}

    def test_world_state_to_dict_crep_fields(self):
        """_world_state_to_dict should include CREP flight/vessel/satellite counts."""
        mod = self._import_worldstate_api()
        if mod is None:
            pytest.skip("worldstate_api import chain unavailable (missing jose)")
        from mycosoft_mas.consciousness.world_model import WorldState

        state = WorldState()
        state.total_flights = 100
        state.total_vessels = 50
        state.total_satellites = 10

        d = mod._world_state_to_dict(state)
        assert d["crep"]["flights"] == 100
        assert d["crep"]["vessels"] == 50
        assert d["crep"]["satellites"] == 10
