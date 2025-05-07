import pytest
import asyncio
from unittest.mock import Mock, patch
from mycosoft_mas.agents.desktop_automation_agent import DesktopAutomationAgent
from mycosoft_mas.agents.messaging.message import Message, MessageType

@pytest.fixture
def agent():
    config = {
        "mouse_speed": 0.5,
        "keyboard_delay": 0.1,
        "browser_profiles": {
            "default": {
                "browser_type": "chrome",
                "user_data_dir": "browser_profiles/default"
            }
        },
        "applications": {
            "test_app": {
                "path": "C:\\test\\app.exe",
                "args": []
            }
        }
    }
    return DesktopAutomationAgent("test_agent", "Test Agent", config)

@pytest.mark.asyncio
async def test_handle_message_browser(agent):
    message = Message(
        message_type=MessageType.BROWSER,
        content={
            "action": "start_browser",
            "profile": "default"
        }
    )
    
    with patch.object(agent, 'start_browser') as mock_start:
        await agent.handle_message(message)
        mock_start.assert_called_once_with("default")

@pytest.mark.asyncio
async def test_handle_message_desktop(agent):
    message = Message(
        message_type=MessageType.DESKTOP,
        content={
            "action": "start_application",
            "app_name": "test_app"
        }
    )
    
    with patch.object(agent, 'start_application') as mock_start:
        await agent.handle_message(message)
        mock_start.assert_called_once_with("test_app")

@pytest.mark.asyncio
async def test_handle_message_invalid_type(agent):
    message = Message(
        message_type=MessageType.TASK,
        content={"action": "test"}
    )
    
    with pytest.raises(ValueError):
        await agent.handle_message(message)

@pytest.mark.asyncio
async def test_handle_message_missing_action(agent):
    message = Message(
        message_type=MessageType.BROWSER,
        content={"profile": "default"}
    )
    
    with pytest.raises(ValueError):
        await agent.handle_message(message)

@pytest.mark.asyncio
async def test_metrics_tracking(agent):
    # Test browser metrics
    await agent.start_browser("default")
    assert agent.metrics["browser_sessions"] == 1
    
    # Test page navigation metrics
    await agent.navigate_to("https://example.com")
    assert agent.metrics["pages_visited"] == 1
    
    # Test form submission metrics
    await agent.fill_form({"username": "test", "password": "test"})
    assert agent.metrics["forms_submitted"] == 1
    
    # Test error metrics
    with pytest.raises(Exception):
        await agent.start_browser("invalid_profile")
    assert agent.metrics["errors"] == 1 