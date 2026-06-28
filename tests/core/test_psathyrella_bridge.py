from mycosoft_mas.devices.psathyrella.comms_bridge import PsathyrellaCommsBridge


def test_radio_acoustic_round_trip() -> None:
    bridge = PsathyrellaCommsBridge()
    frame = {"channel": "lora", "payload": {"signal": "ping", "strength": 0.82}}

    acoustic = bridge.translate_radio_to_acoustic("psathyrella-buoy-com4", frame)
    translated = bridge.translate_acoustic_to_radio(acoustic)

    assert translated["status"] == "ok"
    assert translated["radio_frame"] == frame


def test_set_bearer_updates_state() -> None:
    bridge = PsathyrellaCommsBridge()
    state = bridge.set_bearer("psathyrella-buoy-com4", "starlink")
    assert state["preferred_bearer"] == "starlink"
    assert state["satellite"]["bearer"] == "starlink"


def test_store_forward_enqueue_and_flush() -> None:
    bridge = PsathyrellaCommsBridge()

    one = bridge.enqueue_for_backhaul("psathyrella-buoy-com4", "radio_to_acoustic", {"payload": 1})
    two = bridge.enqueue_for_backhaul("psathyrella-buoy-com4", "acoustic_to_radio", {"payload": 2})
    flushed = bridge.flush_store_forward("psathyrella-buoy-com4", limit=10)

    assert len(flushed) == 2
    assert flushed[0]["frame_id"] == one.frame_id
    assert flushed[1]["frame_id"] == two.frame_id
    assert bridge.get_state("psathyrella-buoy-com4")["store_forward_depth"] == 0
