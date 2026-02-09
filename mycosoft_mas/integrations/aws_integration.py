"""
AWS Integration Client for MYCA Voice System
Created: February 4, 2026

Client for AWS services including S3, EC2, Lambda, and Bedrock.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
import os as os_module

logger = logging.getLogger(__name__)


@dataclass
class AWSConfig:
    """AWS configuration."""
    region: str = "us-east-1"
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    profile: Optional[str] = None


class AWSClient:
    """
    AWS services client for MYCA integration.
    
    Features:
    - S3 operations (upload, download, list)
    - EC2 management (start, stop, describe)
    - Lambda invocation
    - Bedrock LLM integration
    """
    
    def __init__(self, config: Optional[AWSConfig] = None):
        self.config = config or AWSConfig()
        self._clients: Dict[str, Any] = {}
        self._initialized = False
        
        # Try to initialize boto3 clients
        self._init_clients()
        
        logger.info(f"AWSClient initialized for region: {self.config.region}")
    
    def _init_clients(self):
        """Initialize boto3 clients."""
        try:
            import boto3
            
            session_kwargs = {"region_name": self.config.region}
            
            if self.config.access_key_id and self.config.secret_access_key:
                session_kwargs["aws_access_key_id"] = self.config.access_key_id
                session_kwargs["aws_secret_access_key"] = self.config.secret_access_key
            elif self.config.profile:
                session_kwargs["profile_name"] = self.config.profile
            
            session = boto3.Session(**session_kwargs)
            
            self._clients["s3"] = session.client("s3")
            self._clients["ec2"] = session.client("ec2")
            self._clients["lambda"] = session.client("lambda")
            self._clients["bedrock"] = session.client("bedrock-runtime")
            
            self._initialized = True
            logger.info("AWS clients initialized successfully")
            
        except ImportError:
            logger.warning("boto3 not installed - AWS features disabled")
        except Exception as e:
            logger.warning(f"Failed to initialize AWS clients: {e}")
    
    # S3 Operations
    async def s3_upload(self, bucket: str, key: str, data: bytes) -> Dict[str, Any]:
        """Upload data to S3."""
        if not self._initialized:
            return {"error": "AWS not initialized"}
        
        try:
            self._clients["s3"].put_object(Bucket=bucket, Key=key, Body=data)
            return {"success": True, "bucket": bucket, "key": key}
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return {"error": str(e)}
    
    async def s3_download(self, bucket: str, key: str) -> Dict[str, Any]:
        """Download data from S3."""
        if not self._initialized:
            return {"error": "AWS not initialized"}
        
        try:
            response = self._clients["s3"].get_object(Bucket=bucket, Key=key)
            data = response["Body"].read()
            return {"success": True, "data": data, "size": len(data)}
        except Exception as e:
            logger.error(f"S3 download failed: {e}")
            return {"error": str(e)}
    
    async def s3_list(self, bucket: str, prefix: str = "") -> Dict[str, Any]:
        """List objects in S3 bucket."""
        if not self._initialized:
            return {"error": "AWS not initialized"}
        
        try:
            response = self._clients["s3"].list_objects_v2(Bucket=bucket, Prefix=prefix)
            objects = [{"key": obj["Key"], "size": obj["Size"]} for obj in response.get("Contents", [])]
            return {"success": True, "objects": objects, "count": len(objects)}
        except Exception as e:
            logger.error(f"S3 list failed: {e}")
            return {"error": str(e)}
    
    # EC2 Operations
    async def ec2_start(self, instance_ids: List[str]) -> Dict[str, Any]:
        """Start EC2 instances."""
        if not self._initialized:
            return {"error": "AWS not initialized"}
        
        try:
            response = self._clients["ec2"].start_instances(InstanceIds=instance_ids)
            return {"success": True, "starting": [i["InstanceId"] for i in response["StartingInstances"]]}
        except Exception as e:
            logger.error(f"EC2 start failed: {e}")
            return {"error": str(e)}
    
    async def ec2_stop(self, instance_ids: List[str]) -> Dict[str, Any]:
        """Stop EC2 instances."""
        if not self._initialized:
            return {"error": "AWS not initialized"}
        
        try:
            response = self._clients["ec2"].stop_instances(InstanceIds=instance_ids)
            return {"success": True, "stopping": [i["InstanceId"] for i in response["StoppingInstances"]]}
        except Exception as e:
            logger.error(f"EC2 stop failed: {e}")
            return {"error": str(e)}
    
    async def ec2_describe(self, instance_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Describe EC2 instances."""
        if not self._initialized:
            return {"error": "AWS not initialized"}
        
        try:
            kwargs = {}
            if instance_ids:
                kwargs["InstanceIds"] = instance_ids
            
            response = self._clients["ec2"].describe_instances(**kwargs)
            
            instances = []
            for reservation in response["Reservations"]:
                for instance in reservation["Instances"]:
                    instances.append({
                        "id": instance["InstanceId"],
                        "type": instance["InstanceType"],
                        "state": instance["State"]["Name"],
                        "public_ip": instance.get("PublicIpAddress"),
                    })
            
            return {"success": True, "instances": instances}
        except Exception as e:
            logger.error(f"EC2 describe failed: {e}")
            return {"error": str(e)}
    
    # Lambda Operations
    async def lambda_invoke(
        self,
        function_name: str,
        payload: Dict[str, Any],
        async_invoke: bool = False,
    ) -> Dict[str, Any]:
        """Invoke a Lambda function."""
        if not self._initialized:
            return {"error": "AWS not initialized"}
        
        try:
            response = self._clients["lambda"].invoke(
                FunctionName=function_name,
                InvocationType="Event" if async_invoke else "RequestResponse",
                Payload=json.dumps(payload),
            )
            
            if async_invoke:
                return {"success": True, "status": "invoked_async"}
            
            result = json.loads(response["Payload"].read())
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Lambda invoke failed: {e}")
            return {"error": str(e)}
    
    async def lambda_list(self) -> Dict[str, Any]:
        """List Lambda functions."""
        if not self._initialized:
            return {"error": "AWS not initialized"}
        
        try:
            response = self._clients["lambda"].list_functions()
            functions = [
                {"name": f["FunctionName"], "runtime": f["Runtime"], "memory": f["MemorySize"]}
                for f in response["Functions"]
            ]
            return {"success": True, "functions": functions}
        except Exception as e:
            logger.error(f"Lambda list failed: {e}")
            return {"error": str(e)}
    
    # Bedrock Operations
    async def bedrock_generate(
        self,
        prompt: str,
        model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0",
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        """Generate text using Bedrock."""
        if not self._initialized:
            return {"error": "AWS not initialized"}
        
        try:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            })
            
            response = self._clients["bedrock"].invoke_model(
                modelId=model_id,
                body=body,
            )
            
            result = json.loads(response["body"].read())
            content = result.get("content", [{}])[0].get("text", "")
            
            return {"success": True, "response": content, "model": model_id}
        except Exception as e:
            logger.error(f"Bedrock generate failed: {e}")
            return {"error": str(e)}
    
    async def bedrock_list_models(self) -> Dict[str, Any]:
        """List available Bedrock models."""
        if not self._initialized:
            return {"error": "AWS not initialized"}
        
        try:
            bedrock = self._clients.get("bedrock")
            if not bedrock:
                # Create bedrock client (not bedrock-runtime)
                import boto3
                bedrock = boto3.client("bedrock", region_name=self.config.region)
            
            response = bedrock.list_foundation_models()
            models = [
                {"id": m["modelId"], "name": m.get("modelName", ""), "provider": m.get("providerName", "")}
                for m in response.get("modelSummaries", [])
            ]
            return {"success": True, "models": models}
        except Exception as e:
            logger.error(f"Bedrock list models failed: {e}")
            return {"error": str(e)}
    
    def is_available(self) -> bool:
        """Check if AWS is available."""
        return self._initialized


# Singleton
_aws_client: Optional[AWSClient] = None


def get_aws_client() -> AWSClient:
    global _aws_client
    if _aws_client is None:
        config = AWSConfig(
            region=os_module.environ.get("AWS_REGION", "us-east-1"),
            access_key_id=os_module.environ.get("AWS_ACCESS_KEY_ID"),
            secret_access_key=os_module.environ.get("AWS_SECRET_ACCESS_KEY"),
        )
        _aws_client = AWSClient(config)
    return _aws_client


__all__ = [
    "AWSClient",
    "AWSConfig",
    "get_aws_client",
]
