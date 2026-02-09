from datetime import datetime, timedelta
import asyncio
import logging
from typing import Dict, List, Optional, Union
from .base_agent import BaseAgent
from dataclasses import dataclass
from enum import Enum
import json
import aiohttp
from collections import defaultdict

class CampaignStatus(Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class CampaignType(Enum):
    EMAIL = "email"
    SOCIAL_MEDIA = "social_media"
    CONTENT = "content"
    EVENT = "event"
    PR = "pr"
    PRODUCT_LAUNCH = "product_launch"
    WEBINAR = "webinar"
    PARTNERSHIP = "partnership"

@dataclass
class MarketingCampaign:
    id: str
    name: str
    description: str
    campaign_type: CampaignType
    status: CampaignStatus
    start_date: datetime
    end_date: datetime
    budget: float
    target_audience: List[str]
    channels: List[str]
    kpis: Dict[str, float]
    content: Dict[str, str]
    metrics: Dict[str, float]
    created_at: datetime
    updated_at: datetime

class MarketingAgent(BaseAgent):
    def __init__(self, agent_id: str, name: str, config: dict):
        """Initialize the Marketing Agent.
        
        Args:
            agent_id: Unique identifier for the agent
            name: Human-readable name for the agent
            config: Configuration dictionary for the agent
        """
        super().__init__(agent_id=agent_id, name=name, config=config)
        self.campaigns = {}
        self.content_library = {}
        self.audience_segments = {}
        self.analytics_data = defaultdict(dict)
        self.social_media_accounts = {}
        self.email_templates = {}
        self.notification_queue = asyncio.Queue()
        self.api_clients = {}
        
    async def initialize(self, integration_service):
        """Initialize the marketing agent with configurations and connections."""
        await super().initialize(integration_service)
        await self._init_api_connections()
        await self._load_marketing_data()
        await self._start_background_tasks()
        self.logger.info(f"Marketing Agent {self.name} initialized successfully")

    async def create_campaign(self, campaign_data: Dict) -> Dict:
        """Create a new marketing campaign."""
        try:
            campaign_id = campaign_data.get('id', f"camp_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            if campaign_id in self.campaigns:
                return {"success": False, "message": "Campaign ID already exists"}
                
            campaign = MarketingCampaign(
                id=campaign_id,
                name=campaign_data['name'],
                description=campaign_data['description'],
                campaign_type=CampaignType[campaign_data['type'].upper()],
                status=CampaignStatus.DRAFT,
                start_date=datetime.fromisoformat(campaign_data['start_date']),
                end_date=datetime.fromisoformat(campaign_data['end_date']),
                budget=float(campaign_data['budget']),
                target_audience=campaign_data['target_audience'],
                channels=campaign_data['channels'],
                kpis=campaign_data.get('kpis', {}),
                content=campaign_data.get('content', {}),
                metrics={},
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Validate campaign parameters
            validation_result = await self._validate_campaign(campaign)
            if not validation_result['success']:
                return validation_result
            
            self.campaigns[campaign_id] = campaign
            await self._schedule_campaign_tasks(campaign)
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "message": "Campaign created successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create campaign: {str(e)}")
            return {"success": False, "message": str(e)}

    async def create_content(self, content_data: Dict) -> Dict:
        """Create and manage marketing content."""
        try:
            content_id = content_data.get('id', f"cont_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            content = {
                'id': content_id,
                'title': content_data['title'],
                'type': content_data['type'],
                'description': content_data['description'],
                'body': content_data['body'],
                'target_audience': content_data.get('target_audience', []),
                'channels': content_data.get('channels', []),
                'keywords': content_data.get('keywords', []),
                'status': 'draft',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            # Analyze content for SEO and engagement potential
            analysis = await self._analyze_content(content)
            content['analysis'] = analysis
            
            self.content_library[content_id] = content
            
            return {
                "success": True,
                "content_id": content_id,
                "analysis": analysis,
                "message": "Content created successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create content: {str(e)}")
            return {"success": False, "message": str(e)}

    async def schedule_social_media(self, post_data: Dict) -> Dict:
        """Schedule social media posts across platforms."""
        try:
            post_id = post_data.get('id', f"post_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            post = {
                'id': post_id,
                'content': post_data['content'],
                'platforms': post_data['platforms'],
                'schedule_time': datetime.fromisoformat(post_data['schedule_time']),
                'media_urls': post_data.get('media_urls', []),
                'campaign_id': post_data.get('campaign_id'),
                'status': 'scheduled'
            }
            
            # Validate and optimize post for each platform
            for platform in post['platforms']:
                optimization = await self._optimize_social_post(post['content'], platform)
                post[f'{platform}_optimized'] = optimization
            
            # Schedule posts
            scheduling_results = await self._schedule_social_posts(post)
            
            return {
                "success": True,
                "post_id": post_id,
                "scheduling_results": scheduling_results,
                "message": "Social media posts scheduled successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to schedule social media posts: {str(e)}")
            return {"success": False, "message": str(e)}

    async def analyze_campaign_performance(self, campaign_id: str) -> Dict:
        """Analyze campaign performance and generate insights."""
        try:
            if campaign_id not in self.campaigns:
                return {"success": False, "message": "Campaign not found"}
                
            campaign = self.campaigns[campaign_id]
            
            # Gather metrics from various channels
            metrics = {
                'social_media': await self._get_social_metrics(campaign_id),
                'email': await self._get_email_metrics(campaign_id),
                'website': await self._get_website_metrics(campaign_id),
                'conversion': await self._get_conversion_metrics(campaign_id)
            }
            
            # Calculate KPIs
            kpi_performance = await self._calculate_kpi_performance(campaign, metrics)
            
            # Generate insights
            insights = await self._generate_campaign_insights(campaign, metrics, kpi_performance)
            
            # Update campaign metrics
            campaign.metrics = metrics
            campaign.updated_at = datetime.now()
            
            return {
                "success": True,
                "campaign_id": campaign_id,
                "metrics": metrics,
                "kpi_performance": kpi_performance,
                "insights": insights,
                "recommendations": await self._generate_recommendations(campaign, metrics)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze campaign performance: {str(e)}")
            return {"success": False, "message": str(e)}

    async def generate_marketing_report(self, parameters: Dict) -> Dict:
        """Generate comprehensive marketing reports."""
        try:
            report_type = parameters.get('type', 'campaign')
            time_period = parameters.get('time_period', 'last_30_days')
            
            if report_type == 'campaign':
                report_data = await self._generate_campaign_report(parameters)
            elif report_type == 'content':
                report_data = await self._generate_content_report(parameters)
            elif report_type == 'social_media':
                report_data = await self._generate_social_media_report(parameters)
            else:
                return {"success": False, "message": "Invalid report type"}
            
            return {
                "success": True,
                "report_type": report_type,
                "time_period": time_period,
                "data": report_data,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate marketing report: {str(e)}")
            return {"success": False, "message": str(e)}

    async def _init_api_connections(self):
        """Initialize connections to various marketing platforms and APIs."""
        try:
            # Initialize social media API clients
            self.api_clients['twitter'] = await self._init_twitter_client()
            self.api_clients['facebook'] = await self._init_facebook_client()
            self.api_clients['linkedin'] = await self._init_linkedin_client()
            self.api_clients['instagram'] = await self._init_instagram_client()
            
            # Initialize email marketing platform
            self.api_clients['email'] = await self._init_email_platform()
            
            # Initialize analytics platforms
            self.api_clients['analytics'] = await self._init_analytics_platform()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize API connections: {str(e)}")
            raise

    async def _start_background_tasks(self):
        """Start background tasks for monitoring and maintenance."""
        asyncio.create_task(self._monitor_campaign_performance())
        asyncio.create_task(self._process_scheduled_posts())
        asyncio.create_task(self._update_analytics())
        asyncio.create_task(self._process_notifications())

    async def _monitor_campaign_performance(self):
        """Monitor campaign performance and trigger alerts if needed."""
        while True:
            for campaign_id, campaign in self.campaigns.items():
                if campaign.status == CampaignStatus.ACTIVE:
                    performance = await self._check_campaign_performance(campaign_id)
                    if performance['needs_attention']:
                        await self.notification_queue.put({
                            'type': 'campaign_alert',
                            'campaign_id': campaign_id,
                            'issues': performance['issues'],
                            'timestamp': datetime.now()
                        })
            await asyncio.sleep(3600)  # Check every hour

    async def _process_scheduled_posts(self):
        """Process and publish scheduled social media posts."""
        while True:
            now = datetime.now()
            for campaign in self.campaigns.values():
                if campaign.status == CampaignStatus.ACTIVE:
                    await self._publish_scheduled_content(campaign, now)
            await asyncio.sleep(300)  # Check every 5 minutes

    async def _update_analytics(self):
        """Background task to update marketing analytics."""
        while True:
            try:
                # Update analytics logic here
                await asyncio.sleep(300)  # Update every 5 minutes
            except Exception as e:
                self.logger.error(f"Error updating analytics: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _handle_error_type(self, error_type: str, error: Dict) -> Dict:
        """
        Handle marketing-specific error types.
        
        Args:
            error_type: Type of error to handle
            error: Error data dictionary
            
        Returns:
            Dict: Result of error handling
        """
        try:
            error_msg = error.get('error', 'Unknown error')
            error_data = error.get('data', {})
            
            if error_type == 'campaign_error':
                campaign_id = error_data.get('campaign_id')
                if campaign_id in self.campaigns:
                    campaign = self.campaigns[campaign_id]
                    campaign.status = CampaignStatus.PAUSED
                    self.logger.warning(f"Paused campaign {campaign_id} due to error: {error_msg}")
                    return {"success": True, "message": f"Campaign {campaign_id} paused", "action_taken": "pause_campaign"}
            
            elif error_type == 'content_error':
                content_id = error_data.get('content_id')
                if content_id in self.content_library:
                    content = self.content_library[content_id]
                    content['status'] = 'draft'
                    self.logger.warning(f"Reverted content {content_id} to draft due to error: {error_msg}")
                    return {"success": True, "message": f"Content {content_id} reverted to draft", "action_taken": "revert_content"}
            
            elif error_type == 'social_media_error':
                post_id = error_data.get('post_id')
                platform = error_data.get('platform')
                self.logger.warning(f"Social media error for post {post_id} on {platform}: {error_msg}")
                # Attempt to reschedule the post
                if 'retry_time' in error_data:
                    return {"success": True, "message": f"Post {post_id} rescheduled", "action_taken": "reschedule_post"}
            
            elif error_type == 'analytics_error':
                metric_type = error_data.get('metric_type')
                self.logger.warning(f"Analytics error for {metric_type}: {error_msg}")
                # Use cached data if available
                if metric_type in self.analytics_data:
                    return {"success": True, "message": "Using cached analytics data", "action_taken": "use_cache"}
            
            # Handle health check errors
            elif error_type == 'health_check_error':
                service = error_data.get('service', 'unknown')
                self.logger.error(f"Health check failed for {service}: {error_msg}")
                # Attempt to reconnect to the service
                if await self._reconnect_service(service):
                    return {"success": True, "message": f"Reconnected to {service}", "action_taken": "service_reconnect"}
                return {"success": False, "message": f"Failed to reconnect to {service}", "action_taken": "none"}
            
            # Default error handling
            self.logger.error(f"Unhandled error type {error_type}: {error_msg}")
            return {"success": False, "message": f"Unhandled error type: {error_type}", "action_taken": "none"}
            
        except Exception as e:
            self.logger.error(f"Error in error handler: {str(e)}")
            return {"success": False, "message": f"Error handler failed: {str(e)}", "action_taken": "none"}

    async def _reconnect_service(self, service: str) -> bool:
        """Attempt to reconnect to a failed service."""
        try:
            if service in self.api_clients:
                await self._init_api_connections()
                return True
            return False
        except Exception:
            return False

    async def _reschedule_post(self, post_id: str) -> Dict:
        """Reschedule a social media post."""
        try:
            if post_id in self.campaigns:
                campaign = self.campaigns[post_id]
                await self._schedule_social_posts(campaign)
                return {"success": True, "message": "Post rescheduled successfully"}
            return {"success": False, "message": "Post not found"}
        except Exception as e:
            self.logger.error(f"Failed to reschedule post: {str(e)}")
            return {"success": False, "message": str(e)}