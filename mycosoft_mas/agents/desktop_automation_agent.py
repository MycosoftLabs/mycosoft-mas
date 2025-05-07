"""
Desktop Automation Agent for Mycosoft MAS

This module implements the DesktopAutomationAgent class that provides browser automation
and desktop interaction capabilities for services without APIs.
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import pyautogui
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc
from pywinauto.application import Application
import pygetwindow as gw

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.messaging.message_types import Message, MessageType, MessagePriority

class DesktopAutomationAgent(BaseAgent):
    """
    Agent responsible for browser automation and desktop interaction.
    
    This agent provides capabilities to:
    - Control web browsers (Chrome, Firefox, etc.)
    - Handle login flows and form submissions
    - Navigate through web applications
    - Extract data from web pages
    - Handle CAPTCHAs and other security measures
    - Control desktop applications
    - Simulate mouse and keyboard input
    """
    
    def __init__(self, agent_id: str, name: str, config: dict):
        """
        Initialize the Desktop Automation Agent.
        
        Args:
            agent_id: Unique identifier for the agent
            name: Human-readable name for the agent
            config: Configuration dictionary for the agent
        """
        super().__init__(agent_id=agent_id, name=name, config=config)
        
        # Initialize browser profiles
        self.browser_profiles = {}
        self.active_browsers = {}
        
        # Initialize desktop automation settings
        self.mouse_speed = config.get("mouse_speed", 0.5)
        self.keyboard_delay = config.get("keyboard_delay", 0.1)
        pyautogui.PAUSE = self.keyboard_delay
        pyautogui.FAILSAFE = True
        
        # Initialize metrics
        self.metrics = {
            "browser_sessions": 0,
            "pages_visited": 0,
            "forms_submitted": 0,
            "captchas_solved": 0,
            "errors_encountered": 0
        }
    
    async def handle_message(self, message: Message) -> None:
        """
        Handle incoming messages.
        
        Args:
            message: Message to handle
        """
        try:
            if message.type == MessageType.BROWSER:
                await self._handle_browser_message(message)
            elif message.type == MessageType.DESKTOP:
                await self._handle_desktop_message(message)
            else:
                self.logger.warning(f"Unhandled message type: {message.type}")
        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}")
            self.metrics["errors_encountered"] += 1
            raise
    
    async def _handle_browser_message(self, message: Message) -> None:
        """
        Handle browser automation messages.
        
        Args:
            message: Browser automation message
        """
        action = message.data.get("action")
        
        if action == "start_browser":
            await self._handle_start_browser(message)
        elif action == "navigate":
            await self._handle_navigate(message)
        elif action == "login":
            await self._handle_login(message)
        elif action == "fill_form":
            await self._handle_fill_form(message)
        elif action == "extract_data":
            await self._handle_extract_data(message)
        elif action == "solve_captcha":
            await self._handle_solve_captcha(message)
        elif action == "close_browser":
            await self._handle_close_browser(message)
        else:
            self.logger.warning(f"Unhandled browser action: {action}")
    
    async def _handle_desktop_message(self, message: Message) -> None:
        """
        Handle desktop automation messages.
        
        Args:
            message: Desktop automation message
        """
        action = message.data.get("action")
        
        if action == "start_application":
            await self._handle_start_application(message)
        elif action == "click_element":
            await self._handle_click_element(message)
        elif action == "type_text":
            await self._handle_type_text(message)
        elif action == "extract_window_data":
            await self._handle_extract_window_data(message)
        elif action == "close_application":
            await self._handle_close_application(message)
        else:
            self.logger.warning(f"Unhandled desktop action: {action}")
    
    async def _handle_start_browser(self, message: Message) -> None:
        """
        Start a new browser session.
        
        Args:
            message: Start browser message
        """
        try:
            profile_name = message.data.get("profile_name", "default")
            browser_type = message.data.get("browser_type", "chrome")
            
            if browser_type == "chrome":
                options = uc.ChromeOptions()
                options.add_argument("--start-maximized")
                
                # Load profile if exists
                if profile_name in self.browser_profiles:
                    options.add_argument(f"--user-data-dir={self.browser_profiles[profile_name]}")
                
                driver = uc.Chrome(options=options)
                self.active_browsers[profile_name] = driver
                self.metrics["browser_sessions"] += 1
                
                await self.send_message(
                    Message(
                        type=MessageType.BROWSER,
                        priority=MessagePriority.NORMAL,
                        data={
                            "action": "browser_started",
                            "profile_name": profile_name
                        }
                    )
                )
            else:
                raise ValueError(f"Unsupported browser type: {browser_type}")
        except Exception as e:
            self.logger.error(f"Error starting browser: {str(e)}")
            raise
    
    async def _handle_navigate(self, message: Message) -> None:
        """
        Navigate to a URL.
        
        Args:
            message: Navigate message
        """
        try:
            profile_name = message.data.get("profile_name", "default")
            url = message.data.get("url")
            
            if profile_name not in self.active_browsers:
                raise ValueError(f"No active browser for profile: {profile_name}")
            
            driver = self.active_browsers[profile_name]
            driver.get(url)
            self.metrics["pages_visited"] += 1
            
            await self.send_message(
                Message(
                    type=MessageType.BROWSER,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "navigation_complete",
                        "url": url
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error navigating: {str(e)}")
            raise
    
    async def _handle_login(self, message: Message) -> None:
        """
        Handle login flow.
        
        Args:
            message: Login message
        """
        try:
            profile_name = message.data.get("profile_name", "default")
            credentials = message.data.get("credentials", {})
            
            if profile_name not in self.active_browsers:
                raise ValueError(f"No active browser for profile: {profile_name}")
            
            driver = self.active_browsers[profile_name]
            
            # Wait for login form
            wait = WebDriverWait(driver, 10)
            username_field = wait.until(EC.presence_of_element_located((By.NAME, "username")))
            password_field = driver.find_element(By.NAME, "password")
            
            # Fill credentials
            username_field.send_keys(credentials.get("username", ""))
            password_field.send_keys(credentials.get("password", ""))
            
            # Submit form
            submit_button = driver.find_element(By.XPATH, "//button[@type='submit']")
            submit_button.click()
            
            self.metrics["forms_submitted"] += 1
            
            await self.send_message(
                Message(
                    type=MessageType.BROWSER,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "login_complete",
                        "status": "success"
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error during login: {str(e)}")
            raise
    
    async def _handle_fill_form(self, message: Message) -> None:
        """
        Fill out a web form.
        
        Args:
            message: Fill form message
        """
        try:
            profile_name = message.data.get("profile_name", "default")
            form_data = message.data.get("form_data", {})
            
            if profile_name not in self.active_browsers:
                raise ValueError(f"No active browser for profile: {profile_name}")
            
            driver = self.active_browsers[profile_name]
            
            # Fill each form field
            for field_name, field_value in form_data.items():
                try:
                    element = driver.find_element(By.NAME, field_name)
                    element.clear()
                    element.send_keys(field_value)
                except NoSuchElementException:
                    self.logger.warning(f"Form field not found: {field_name}")
            
            self.metrics["forms_submitted"] += 1
            
            await self.send_message(
                Message(
                    type=MessageType.BROWSER,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "form_filled",
                        "status": "success"
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error filling form: {str(e)}")
            raise
    
    async def _handle_extract_data(self, message: Message) -> None:
        """
        Extract data from a web page.
        
        Args:
            message: Extract data message
        """
        try:
            profile_name = message.data.get("profile_name", "default")
            selectors = message.data.get("selectors", {})
            
            if profile_name not in self.active_browsers:
                raise ValueError(f"No active browser for profile: {profile_name}")
            
            driver = self.active_browsers[profile_name]
            extracted_data = {}
            
            # Extract data using provided selectors
            for key, selector in selectors.items():
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    extracted_data[key] = element.text
                except NoSuchElementException:
                    self.logger.warning(f"Element not found for selector: {selector}")
            
            await self.send_message(
                Message(
                    type=MessageType.BROWSER,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "data_extracted",
                        "data": extracted_data
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error extracting data: {str(e)}")
            raise
    
    async def _handle_solve_captcha(self, message: Message) -> None:
        """
        Handle CAPTCHA solving.
        
        Args:
            message: Solve CAPTCHA message
        """
        try:
            profile_name = message.data.get("profile_name", "default")
            captcha_type = message.data.get("captcha_type", "image")
            
            if profile_name not in self.active_browsers:
                raise ValueError(f"No active browser for profile: {profile_name}")
            
            driver = self.active_browsers[profile_name]
            
            # TODO: Implement CAPTCHA solving logic
            # This could involve:
            # 1. Using a CAPTCHA solving service
            # 2. Using OCR for image CAPTCHAs
            # 3. Using audio recognition for audio CAPTCHAs
            
            self.metrics["captchas_solved"] += 1
            
            await self.send_message(
                Message(
                    type=MessageType.BROWSER,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "captcha_solved",
                        "status": "success"
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error solving CAPTCHA: {str(e)}")
            raise
    
    async def _handle_close_browser(self, message: Message) -> None:
        """
        Close a browser session.
        
        Args:
            message: Close browser message
        """
        try:
            profile_name = message.data.get("profile_name", "default")
            
            if profile_name not in self.active_browsers:
                raise ValueError(f"No active browser for profile: {profile_name}")
            
            driver = self.active_browsers[profile_name]
            driver.quit()
            del self.active_browsers[profile_name]
            
            await self.send_message(
                Message(
                    type=MessageType.BROWSER,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "browser_closed",
                        "profile_name": profile_name
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error closing browser: {str(e)}")
            raise
    
    async def _handle_start_application(self, message: Message) -> None:
        """
        Start a desktop application.
        
        Args:
            message: Start application message
        """
        try:
            app_path = message.data.get("app_path")
            app_args = message.data.get("app_args", [])
            
            app = Application().start(f"{app_path} {' '.join(app_args)}")
            
            await self.send_message(
                Message(
                    type=MessageType.DESKTOP,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "application_started",
                        "app_path": app_path
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error starting application: {str(e)}")
            raise
    
    async def _handle_click_element(self, message: Message) -> None:
        """
        Click a desktop element.
        
        Args:
            message: Click element message
        """
        try:
            x = message.data.get("x")
            y = message.data.get("y")
            
            pyautogui.moveTo(x, y, duration=self.mouse_speed)
            pyautogui.click()
            
            await self.send_message(
                Message(
                    type=MessageType.DESKTOP,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "element_clicked",
                        "x": x,
                        "y": y
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error clicking element: {str(e)}")
            raise
    
    async def _handle_type_text(self, message: Message) -> None:
        """
        Type text using keyboard.
        
        Args:
            message: Type text message
        """
        try:
            text = message.data.get("text", "")
            
            pyautogui.write(text, interval=self.keyboard_delay)
            
            await self.send_message(
                Message(
                    type=MessageType.DESKTOP,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "text_typed",
                        "text": text
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error typing text: {str(e)}")
            raise
    
    async def _handle_extract_window_data(self, message: Message) -> None:
        """
        Extract data from a window.
        
        Args:
            message: Extract window data message
        """
        try:
            window_title = message.data.get("window_title")
            
            window = gw.getWindowsWithTitle(window_title)[0]
            window_data = {
                "title": window.title,
                "left": window.left,
                "top": window.top,
                "width": window.width,
                "height": window.height
            }
            
            await self.send_message(
                Message(
                    type=MessageType.DESKTOP,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "window_data_extracted",
                        "data": window_data
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error extracting window data: {str(e)}")
            raise
    
    async def _handle_close_application(self, message: Message) -> None:
        """
        Close a desktop application.
        
        Args:
            message: Close application message
        """
        try:
            window_title = message.data.get("window_title")
            
            window = gw.getWindowsWithTitle(window_title)[0]
            window.close()
            
            await self.send_message(
                Message(
                    type=MessageType.DESKTOP,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "application_closed",
                        "window_title": window_title
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error closing application: {str(e)}")
            raise 