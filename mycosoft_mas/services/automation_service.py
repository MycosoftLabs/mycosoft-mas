import os
import requests

class AutomationService:
    def __init__(self):
        self.zapier_webhook = os.getenv("ZAPIER_WEBHOOK_URL")
        self.ifttt_webhook = os.getenv("IFTTT_WEBHOOK_URL")

    def trigger_zapier(self, event: str, data: dict):
        if self.zapier_webhook:
            try:
                payload = {"event": event, **data}
                requests.post(self.zapier_webhook, json=payload)
            except Exception as e:
                pass

    def trigger_ifttt(self, event: str, data: dict):
        if self.ifttt_webhook:
            try:
                payload = {"value1": event, "value2": str(data)}
                requests.post(self.ifttt_webhook, json=payload)
            except Exception as e:
                pass 