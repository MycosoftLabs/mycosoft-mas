"""
Mycosoft Multi-Agent System (MAS) - Image Processing Agent

This module implements the ImageProcessingAgent, which manages image processing,
analysis, and storage for mycology research.
"""

import asyncio
import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import numpy as np
import cv2
from PIL import Image
import io

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus

class ImageType(Enum):
    """Enumeration of image types."""
    MICROSCOPY = "microscopy"
    MACRO = "macro"
    TIMELAPSE = "timelapse"
    SPECTRAL = "spectral"
    THERMAL = "thermal"

class ProcessingType(Enum):
    """Enumeration of processing types."""
    ENHANCEMENT = "enhancement"
    SEGMENTATION = "segmentation"
    FEATURE_EXTRACTION = "feature_extraction"
    CLASSIFICATION = "classification"
    MEASUREMENT = "measurement"

@dataclass
class ImageMetadata:
    """Data class for storing image metadata."""
    image_id: str
    timestamp: datetime
    image_type: ImageType
    source: str
    resolution: Tuple[int, int]
    format: str
    size_bytes: int
    metadata: Dict[str, Any]

@dataclass
class ProcessedImage:
    """Data class for storing processed image data."""
    processed_id: str
    image_id: str
    timestamp: datetime
    processing_type: ProcessingType
    parameters: Dict[str, Any]
    result_data: Dict[str, Any]
    metadata: Dict[str, Any]

@dataclass
class ImageAnalysis:
    """Data class for storing image analysis results."""
    analysis_id: str
    image_id: str
    timestamp: datetime
    analysis_type: str
    features: Dict[str, Any]
    measurements: Dict[str, Any]
    classifications: Dict[str, Any]
    metadata: Dict[str, Any]

class ImageProcessingAgent(BaseAgent):
    """
    Agent responsible for managing image processing, analysis, and storage
    for mycology research.
    """
    
    def __init__(self, agent_id: str, name: str, config: dict):
        """Initialize the ImageProcessingAgent."""
        super().__init__(agent_id, name, config)
        
        # Initialize storage
        self.images: Dict[str, ImageMetadata] = {}
        self.processed_images: Dict[str, List[ProcessedImage]] = {}
        self.analyses: Dict[str, List[ImageAnalysis]] = {}
        self.active_processes: Set[str] = set()
        
        # Initialize directories
        self.image_dir = Path(config.get('image_dir', 'data/images'))
        self.processed_dir = Path(config.get('processed_dir', 'data/processed'))
        self.analysis_dir = Path(config.get('analysis_dir', 'data/analysis'))
        
        # Create directories if they don't exist
        self.image_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize queues
        self.processing_queue = asyncio.Queue()
        self.analysis_queue = asyncio.Queue()
        
        # Initialize metrics
        self.metrics.update({
            "images_processed": 0,
            "processing_operations": 0,
            "analyses_performed": 0,
            "processing_errors": 0
        })

    async def initialize(self) -> bool:
        """Initialize the agent and its services."""
        try:
            self.status = AgentStatus.INITIALIZING
            self.logger.info(f"Initializing ImageProcessingAgent {self.name}")
            
            # Load existing images
            await self._load_images()
            
            # Start background tasks
            self.background_tasks.extend([
                asyncio.create_task(self._process_processing_queue()),
                asyncio.create_task(self._process_analysis_queue())
            ])
            
            self.status = AgentStatus.ACTIVE
            self.is_running = True
            self.metrics["start_time"] = datetime.now()
            
            self.logger.info(f"ImageProcessingAgent {self.name} initialized successfully")
            return True
        except Exception as e:
            self.status = AgentStatus.ERROR
            self.logger.error(f"Failed to initialize ImageProcessingAgent {self.name}: {str(e)}")
            return False

    async def stop(self) -> bool:
        """Stop the agent and cleanup resources."""
        try:
            self.logger.info(f"Stopping ImageProcessingAgent {self.name}")
            self.is_running = False
            
            # Stop all active processes
            for image_id in self.active_processes:
                await self.stop_processing(image_id)
            
            # Save images
            await self._save_images()
            
            # Cancel background tasks
            for task in self.background_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            self.background_tasks = []
            self.status = AgentStatus.STOPPED
            
            self.logger.info(f"ImageProcessingAgent {self.name} stopped successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error stopping ImageProcessingAgent {self.name}: {str(e)}")
            return False

    async def add_image(self, image_data: bytes, image_type: ImageType, source: str, metadata: Dict[str, Any]) -> str:
        """
        Add a new image to the system.
        
        Args:
            image_data: Raw image data
            image_type: Type of image
            source: Source of the image
            metadata: Additional metadata
            
        Returns:
            str: ID of the added image
        """
        try:
            # Generate image ID
            image_id = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Save image data
            image_path = self.image_dir / f"{image_id}.jpg"
            with open(image_path, 'wb') as f:
                f.write(image_data)
            
            # Get image properties
            img = Image.open(io.BytesIO(image_data))
            resolution = img.size
            format = img.format
            size_bytes = len(image_data)
            
            # Create metadata
            image_metadata = ImageMetadata(
                image_id=image_id,
                timestamp=datetime.now(),
                image_type=image_type,
                source=source,
                resolution=resolution,
                format=format,
                size_bytes=size_bytes,
                metadata=metadata
            )
            
            # Store metadata
            self.images[image_id] = image_metadata
            self.processed_images[image_id] = []
            self.analyses[image_id] = []
            
            # Save metadata
            await self._save_image_metadata(image_id)
            
            self.metrics["images_processed"] += 1
            self.logger.info(f"Added image: {image_id}")
            return image_id
            
        except Exception as e:
            self.logger.error(f"Error adding image: {str(e)}")
            return ""

    async def start_processing(self, image_id: str, processing_type: ProcessingType, parameters: Dict[str, Any]) -> bool:
        """
        Start processing an image.
        
        Args:
            image_id: ID of the image to process
            processing_type: Type of processing to perform
            parameters: Processing parameters
            
        Returns:
            bool: True if processing was started successfully, False otherwise
        """
        try:
            # Check if image exists
            if image_id not in self.images:
                raise ValueError(f"Image not found: {image_id}")
            
            # Check if processing is already active
            if image_id in self.active_processes:
                raise ValueError(f"Processing already active for image: {image_id}")
            
            # Add to processing queue
            await self.processing_queue.put({
                "image_id": image_id,
                "processing_type": processing_type,
                "parameters": parameters,
                "action": "start"
            })
            
            self.logger.info(f"Queued processing start for image: {image_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting processing for image {image_id}: {str(e)}")
            return False

    async def stop_processing(self, image_id: str) -> bool:
        """
        Stop processing an image.
        
        Args:
            image_id: ID of the image to stop processing
            
        Returns:
            bool: True if processing was stopped successfully, False otherwise
        """
        try:
            # Check if image exists
            if image_id not in self.images:
                raise ValueError(f"Image not found: {image_id}")
            
            # Check if processing is active
            if image_id not in self.active_processes:
                raise ValueError(f"Processing not active for image: {image_id}")
            
            # Add to processing queue
            await self.processing_queue.put({
                "image_id": image_id,
                "action": "stop"
            })
            
            self.logger.info(f"Queued processing stop for image: {image_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping processing for image {image_id}: {str(e)}")
            return False

    async def analyze_image(self, image_id: str, analysis_type: str, parameters: Dict[str, Any]) -> bool:
        """
        Analyze an image.
        
        Args:
            image_id: ID of the image to analyze
            analysis_type: Type of analysis to perform
            parameters: Analysis parameters
            
        Returns:
            bool: True if analysis was started successfully, False otherwise
        """
        try:
            # Check if image exists
            if image_id not in self.images:
                raise ValueError(f"Image not found: {image_id}")
            
            # Add to analysis queue
            await self.analysis_queue.put({
                "image_id": image_id,
                "analysis_type": analysis_type,
                "parameters": parameters
            })
            
            self.logger.info(f"Queued analysis for image: {image_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error analyzing image {image_id}: {str(e)}")
            return False

    async def get_image(self, image_id: str) -> Optional[Tuple[bytes, ImageMetadata]]:
        """
        Get an image and its metadata.
        
        Args:
            image_id: ID of the image to get
            
        Returns:
            Optional[Tuple[bytes, ImageMetadata]]: The image data and metadata, or None if not found
        """
        try:
            # Check if image exists
            if image_id not in self.images:
                raise ValueError(f"Image not found: {image_id}")
            
            # Get image data
            image_path = self.image_dir / f"{image_id}.jpg"
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            return image_data, self.images[image_id]
            
        except Exception as e:
            self.logger.error(f"Error getting image {image_id}: {str(e)}")
            return None

    async def get_processed_image(self, image_id: str, processed_id: str) -> Optional[Tuple[bytes, ProcessedImage]]:
        """
        Get a processed image and its metadata.
        
        Args:
            image_id: ID of the original image
            processed_id: ID of the processed image
            
        Returns:
            Optional[Tuple[bytes, ProcessedImage]]: The processed image data and metadata, or None if not found
        """
        try:
            # Check if image exists
            if image_id not in self.images:
                raise ValueError(f"Image not found: {image_id}")
            
            # Check if processed image exists
            processed_images = self.processed_images.get(image_id, [])
            processed_image = next((p for p in processed_images if p.processed_id == processed_id), None)
            
            if processed_image is None:
                raise ValueError(f"Processed image not found: {processed_id}")
            
            # Get processed image data
            processed_path = self.processed_dir / f"{processed_id}.jpg"
            with open(processed_path, 'rb') as f:
                processed_data = f.read()
            
            return processed_data, processed_image
            
        except Exception as e:
            self.logger.error(f"Error getting processed image {processed_id}: {str(e)}")
            return None

    async def get_analysis(self, image_id: str, analysis_id: str) -> Optional[ImageAnalysis]:
        """
        Get analysis results for an image.
        
        Args:
            image_id: ID of the image
            analysis_id: ID of the analysis
            
        Returns:
            Optional[ImageAnalysis]: The analysis results, or None if not found
        """
        try:
            # Check if image exists
            if image_id not in self.images:
                raise ValueError(f"Image not found: {image_id}")
            
            # Check if analysis exists
            analyses = self.analyses.get(image_id, [])
            analysis = next((a for a in analyses if a.analysis_id == analysis_id), None)
            
            if analysis is None:
                raise ValueError(f"Analysis not found: {analysis_id}")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error getting analysis {analysis_id}: {str(e)}")
            return None

    async def _load_images(self):
        """Load images from storage."""
        try:
            # Load image metadata files
            for file_path in self.image_dir.glob("*.json"):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        
                        # Convert to ImageMetadata
                        image_metadata = self._dict_to_image_metadata(data)
                        
                        # Store metadata
                        self.images[image_metadata.image_id] = image_metadata
                        self.processed_images[image_metadata.image_id] = []
                        self.analyses[image_metadata.image_id] = []
                        
                        self.logger.info(f"Loaded image: {image_metadata.image_id}")
                except Exception as e:
                    self.logger.error(f"Error loading image from {file_path}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error loading images: {str(e)}")

    async def _save_images(self):
        """Save images to storage."""
        try:
            # Save each image metadata
            for image_id, image_metadata in self.images.items():
                try:
                    await self._save_image_metadata(image_id)
                except Exception as e:
                    self.logger.error(f"Error saving image {image_id}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error saving images: {str(e)}")

    async def _save_image_metadata(self, image_id: str):
        """Save image metadata to storage."""
        try:
            if image_id in self.images:
                # Convert to dictionary
                data = self._image_metadata_to_dict(self.images[image_id])
                
                # Save to file
                file_path = self.image_dir / f"{image_id}.json"
                with open(file_path, 'w') as f:
                    json.dump(data, f, default=str)
        except Exception as e:
            self.logger.error(f"Error saving image metadata {image_id}: {str(e)}")

    async def _process_processing_queue(self):
        """Process the processing queue."""
        while self.is_running:
            try:
                task = await self.processing_queue.get()
                image_id = task.get('image_id')
                action = task.get('action')
                
                if image_id in self.images:
                    if action == 'start':
                        # Start processing
                        processing_type = task.get('processing_type')
                        parameters = task.get('parameters')
                        
                        # Get image data
                        image_path = self.image_dir / f"{image_id}.jpg"
                        with open(image_path, 'rb') as f:
                            image_data = f.read()
                        
                        # Process image
                        processed_data = await self._process_image(image_data, processing_type, parameters)
                        
                        if processed_data:
                            # Generate processed image ID
                            processed_id = f"proc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            
                            # Save processed image
                            processed_path = self.processed_dir / f"{processed_id}.jpg"
                            with open(processed_path, 'wb') as f:
                                f.write(processed_data)
                            
                            # Create processed image metadata
                            processed_image = ProcessedImage(
                                processed_id=processed_id,
                                image_id=image_id,
                                timestamp=datetime.now(),
                                processing_type=processing_type,
                                parameters=parameters,
                                result_data={},
                                metadata={}
                            )
                            
                            # Store processed image
                            if image_id not in self.processed_images:
                                self.processed_images[image_id] = []
                            self.processed_images[image_id].append(processed_image)
                            
                            self.metrics["processing_operations"] += 1
                            self.logger.info(f"Processed image: {image_id}")
                    elif action == 'stop':
                        # Stop processing
                        self.active_processes.remove(image_id)
                        self.logger.info(f"Stopped processing for image: {image_id}")
                
                self.processing_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing processing queue: {str(e)}")
                self.metrics["processing_errors"] += 1
                await asyncio.sleep(1)

    async def _process_analysis_queue(self):
        """Process the analysis queue."""
        while self.is_running:
            try:
                task = await self.analysis_queue.get()
                image_id = task.get('image_id')
                analysis_type = task.get('analysis_type')
                parameters = task.get('parameters')
                
                if image_id in self.images:
                    # Get image data
                    image_path = self.image_dir / f"{image_id}.jpg"
                    with open(image_path, 'rb') as f:
                        image_data = f.read()
                    
                    # Analyze image
                    analysis_results = await self._analyze_image(image_data, analysis_type, parameters)
                    
                    if analysis_results:
                        # Generate analysis ID
                        analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        
                        # Create analysis
                        analysis = ImageAnalysis(
                            analysis_id=analysis_id,
                            image_id=image_id,
                            timestamp=datetime.now(),
                            analysis_type=analysis_type,
                            features=analysis_results.get('features', {}),
                            measurements=analysis_results.get('measurements', {}),
                            classifications=analysis_results.get('classifications', {}),
                            metadata=analysis_results.get('metadata', {})
                        )
                        
                        # Store analysis
                        if image_id not in self.analyses:
                            self.analyses[image_id] = []
                        self.analyses[image_id].append(analysis)
                        
                        # Save analysis
                        file_path = self.analysis_dir / f"{analysis_id}.json"
                        with open(file_path, 'w') as f:
                            json.dump(self._analysis_to_dict(analysis), f, default=str)
                        
                        self.metrics["analyses_performed"] += 1
                        self.logger.info(f"Analyzed image: {image_id}")
                
                self.analysis_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing analysis queue: {str(e)}")
                await asyncio.sleep(1)

    async def _process_image(self, image_data: bytes, processing_type: ProcessingType, parameters: Dict[str, Any]) -> Optional[bytes]:
        """
        Process an image.
        
        Args:
            image_data: Raw image data
            processing_type: Type of processing to perform
            parameters: Processing parameters
            
        Returns:
            Optional[bytes]: Processed image data, or None if processing failed
        """
        try:
            # Convert to numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Process image based on type
            if processing_type == ProcessingType.ENHANCEMENT:
                # Apply enhancement
                processed = self._enhance_image(img, parameters)
            elif processing_type == ProcessingType.SEGMENTATION:
                # Apply segmentation
                processed = self._segment_image(img, parameters)
            elif processing_type == ProcessingType.FEATURE_EXTRACTION:
                # Extract features
                processed = self._extract_features(img, parameters)
            else:
                raise ValueError(f"Unsupported processing type: {processing_type}")
            
            # Convert back to bytes
            _, buffer = cv2.imencode('.jpg', processed)
            return buffer.tobytes()
            
        except Exception as e:
            self.logger.error(f"Error processing image: {str(e)}")
            return None

    async def _analyze_image(self, image_data: bytes, analysis_type: str, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze an image.
        
        Args:
            image_data: Raw image data
            analysis_type: Type of analysis to perform
            parameters: Analysis parameters
            
        Returns:
            Optional[Dict[str, Any]]: Analysis results, or None if analysis failed
        """
        try:
            # Convert to numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Analyze image based on type
            if analysis_type == "morphology":
                # Analyze morphology
                results = self._analyze_morphology(img, parameters)
            elif analysis_type == "color":
                # Analyze color
                results = self._analyze_color(img, parameters)
            elif analysis_type == "texture":
                # Analyze texture
                results = self._analyze_texture(img, parameters)
            else:
                raise ValueError(f"Unsupported analysis type: {analysis_type}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error analyzing image: {str(e)}")
            return None

    def _enhance_image(self, img: np.ndarray, parameters: Dict[str, Any]) -> np.ndarray:
        """Enhance an image."""
        try:
            # Apply contrast enhancement
            if parameters.get('enhance_contrast', False):
                lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
                l = clahe.apply(l)
                lab = cv2.merge((l,a,b))
                img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            
            # Apply denoising
            if parameters.get('denoise', False):
                img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
            
            return img
        except Exception:
            return img

    def _segment_image(self, img: np.ndarray, parameters: Dict[str, Any]) -> np.ndarray:
        """Segment an image."""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply thresholding
            _, binary = cv2.threshold(gray, parameters.get('threshold', 127), 255, cv2.THRESH_BINARY)
            
            # Apply morphological operations
            kernel = np.ones((5,5), np.uint8)
            binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            
            # Convert back to BGR
            return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
        except Exception:
            return img

    def _extract_features(self, img: np.ndarray, parameters: Dict[str, Any]) -> np.ndarray:
        """Extract features from an image."""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Detect edges
            edges = cv2.Canny(gray, parameters.get('threshold1', 100), parameters.get('threshold2', 200))
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Draw contours
            result = img.copy()
            cv2.drawContours(result, contours, -1, (0,255,0), 2)
            
            return result
        except Exception:
            return img

    def _analyze_morphology(self, img: np.ndarray, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze image morphology."""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply thresholding
            _, binary = cv2.threshold(gray, parameters.get('threshold', 127), 255, cv2.THRESH_BINARY)
            
            # Find contours
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Calculate measurements
            areas = [cv2.contourArea(c) for c in contours]
            perimeters = [cv2.arcLength(c, True) for c in contours]
            
            return {
                'features': {
                    'num_objects': len(contours),
                    'areas': areas,
                    'perimeters': perimeters
                },
                'measurements': {
                    'total_area': sum(areas),
                    'avg_area': np.mean(areas) if areas else 0,
                    'avg_perimeter': np.mean(perimeters) if perimeters else 0
                },
                'classifications': {},
                'metadata': {}
            }
        except Exception:
            return {
                'features': {},
                'measurements': {},
                'classifications': {},
                'metadata': {}
            }

    def _analyze_color(self, img: np.ndarray, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze image color."""
        try:
            # Convert to HSV
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            
            # Calculate color histograms
            h_hist = cv2.calcHist([hsv], [0], None, [180], [0, 180])
            s_hist = cv2.calcHist([hsv], [1], None, [256], [0, 256])
            v_hist = cv2.calcHist([hsv], [2], None, [256], [0, 256])
            
            # Calculate statistics
            h_mean = np.mean(h_hist)
            s_mean = np.mean(s_hist)
            v_mean = np.mean(v_hist)
            
            return {
                'features': {
                    'h_histogram': h_hist.tolist(),
                    's_histogram': s_hist.tolist(),
                    'v_histogram': v_hist.tolist()
                },
                'measurements': {
                    'h_mean': h_mean,
                    's_mean': s_mean,
                    'v_mean': v_mean
                },
                'classifications': {},
                'metadata': {}
            }
        except Exception:
            return {
                'features': {},
                'measurements': {},
                'classifications': {},
                'metadata': {}
            }

    def _analyze_texture(self, img: np.ndarray, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze image texture."""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Calculate GLCM
            glcm = cv2.cornerHarris(gray, 2, 3, 0.04)
            
            # Calculate statistics
            glcm_mean = np.mean(glcm)
            glcm_std = np.std(glcm)
            
            return {
                'features': {
                    'glcm': glcm.tolist()
                },
                'measurements': {
                    'glcm_mean': glcm_mean,
                    'glcm_std': glcm_std
                },
                'classifications': {},
                'metadata': {}
            }
        except Exception:
            return {
                'features': {},
                'measurements': {},
                'classifications': {},
                'metadata': {}
            }

    def _image_metadata_to_dict(self, metadata: ImageMetadata) -> Dict[str, Any]:
        """Convert ImageMetadata to dictionary."""
        return {
            "image_id": metadata.image_id,
            "timestamp": metadata.timestamp,
            "image_type": metadata.image_type.value,
            "source": metadata.source,
            "resolution": metadata.resolution,
            "format": metadata.format,
            "size_bytes": metadata.size_bytes,
            "metadata": metadata.metadata
        }

    def _dict_to_image_metadata(self, data: Dict[str, Any]) -> ImageMetadata:
        """Convert dictionary to ImageMetadata."""
        return ImageMetadata(
            image_id=data.get("image_id", ""),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            image_type=ImageType(data.get("image_type", "microscopy")),
            source=data.get("source", ""),
            resolution=tuple(data.get("resolution", (0, 0))),
            format=data.get("format", ""),
            size_bytes=data.get("size_bytes", 0),
            metadata=data.get("metadata", {})
        )

    def _analysis_to_dict(self, analysis: ImageAnalysis) -> Dict[str, Any]:
        """Convert ImageAnalysis to dictionary."""
        return {
            "analysis_id": analysis.analysis_id,
            "image_id": analysis.image_id,
            "timestamp": analysis.timestamp,
            "analysis_type": analysis.analysis_type,
            "features": analysis.features,
            "measurements": analysis.measurements,
            "classifications": analysis.classifications,
            "metadata": analysis.metadata
        } 