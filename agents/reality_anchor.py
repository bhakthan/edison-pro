"""
Reality Anchor Agent
Processes current engineering diagram as raw sensory input without historical bias.
"""

import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import base64
from PIL import Image
import io


@dataclass
class FeatureVector:
    """Represents extracted features from a diagram"""
    visual_elements: List[Dict[str, Any]] = field(default_factory=list)
    text_annotations: List[Dict[str, str]] = field(default_factory=list)
    symbols: List[Dict[str, Any]] = field(default_factory=list)
    spatial_layout: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    embedding: Optional[np.ndarray] = None
    raw_image: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'visual_elements': self.visual_elements,
            'text_annotations': self.text_annotations,
            'symbols': self.symbols,
            'spatial_layout': self.spatial_layout,
            'timestamp': self.timestamp,
            'embedding': self.embedding.tolist() if self.embedding is not None else None
        }
    
    def __sub__(self, other: 'FeatureVector') -> 'FeatureVector':
        """Compute difference between feature vectors (for novelty detection)"""
        if self.embedding is not None and other.embedding is not None:
            diff_embedding = self.embedding - other.embedding
        else:
            diff_embedding = None
            
        return FeatureVector(
            visual_elements=[v for v in self.visual_elements if v not in other.visual_elements],
            text_annotations=[t for t in self.text_annotations if t not in other.text_annotations],
            symbols=[s for s in self.symbols if s not in other.symbols],
            spatial_layout={},
            embedding=diff_embedding
        )


class RealityAnchorAgent:
    """
    Extract pure features from current diagram without memory bias.
    Represents objective reality - what's actually in the diagram.
    """
    
    def __init__(self, vision_model=None, ocr_engine=None, symbol_detector=None):
        """
        Initialize Reality Anchor with perception tools
        
        Args:
            vision_model: Azure OpenAI o3-pro vision model
            ocr_engine: OCR engine for text extraction
            symbol_detector: Symbol/component detection model
        """
        self.vision = vision_model
        self.ocr = ocr_engine
        self.symbols = symbol_detector
        
    def analyze(self, diagram_image: Any, use_vision: bool = True) -> FeatureVector:
        """
        Extract features from current diagram
        
        Args:
            diagram_image: Image file path, PIL Image, or base64 string
            use_vision: Whether to use vision model (if False, use basic extraction)
            
        Returns:
            FeatureVector with extracted features
        """
        # Convert input to PIL Image
        pil_image = self._load_image(diagram_image)
        
        # Extract visual features
        visual_elements = self._detect_components(pil_image) if use_vision else []
        
        # Extract text annotations
        text_annotations = self._extract_text(pil_image)
        
        # Identify symbols
        symbols = self._identify_symbols(pil_image)
        
        # Compute spatial relationships
        spatial_layout = self._compute_spatial_relationships(visual_elements, symbols)
        
        # Generate embedding
        embedding = self._generate_embedding(visual_elements, text_annotations, symbols)
        
        return FeatureVector(
            visual_elements=visual_elements,
            text_annotations=text_annotations,
            symbols=symbols,
            spatial_layout=spatial_layout,
            timestamp=datetime.now().isoformat(),
            embedding=embedding,
            raw_image=pil_image
        )
    
    def _load_image(self, diagram_image: Any) -> Image.Image:
        """Load image from various input formats"""
        if isinstance(diagram_image, str):
            if diagram_image.startswith('data:image') or diagram_image.startswith('iVBOR'):
                # Base64 encoded
                if 'base64,' in diagram_image:
                    diagram_image = diagram_image.split('base64,')[1]
                image_data = base64.b64decode(diagram_image)
                return Image.open(io.BytesIO(image_data))
            else:
                # File path
                return Image.open(diagram_image)
        elif isinstance(diagram_image, Image.Image):
            return diagram_image
        else:
            raise ValueError(f"Unsupported image type: {type(diagram_image)}")
    
    def _detect_components(self, image: Image.Image) -> List[Dict[str, Any]]:
        """
        Detect visual components using vision model
        
        For now, placeholder - will integrate with o3-pro vision
        """
        # TODO: Integrate with Azure OpenAI o3-pro vision API
        # This would call the vision model to detect components
        
        # Placeholder: Basic image analysis
        width, height = image.size
        
        return [
            {
                'type': 'diagram_placeholder',
                'bbox': [0, 0, width, height],
                'confidence': 1.0,
                'properties': {
                    'width': width,
                    'height': height,
                    'mode': image.mode
                }
            }
        ]
    
    def _extract_text(self, image: Image.Image) -> List[Dict[str, str]]:
        """
        Extract text using OCR
        
        For now, placeholder - will integrate with OCR engine
        """
        # TODO: Integrate with Azure Computer Vision OCR or Tesseract
        
        return [
            {
                'text': 'placeholder_text',
                'position': [0, 0],
                'confidence': 0.9
            }
        ]
    
    def _identify_symbols(self, image: Image.Image) -> List[Dict[str, Any]]:
        """
        Identify engineering symbols
        
        For now, placeholder - will integrate with symbol detection
        """
        # TODO: Integrate with custom symbol detection model
        
        return [
            {
                'symbol_type': 'unknown',
                'bbox': [0, 0, 50, 50],
                'confidence': 0.5
            }
        ]
    
    def _compute_spatial_relationships(
        self, 
        visual_elements: List[Dict[str, Any]], 
        symbols: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compute spatial relationships between components
        """
        # Build simple spatial graph
        num_elements = len(visual_elements)
        num_symbols = len(symbols)
        
        return {
            'num_visual_elements': num_elements,
            'num_symbols': num_symbols,
            'total_components': num_elements + num_symbols,
            'spatial_density': (num_elements + num_symbols) / 1000.0  # per 1000 pixels
        }
    
    def _generate_embedding(
        self,
        visual_elements: List[Dict[str, Any]],
        text_annotations: List[Dict[str, str]],
        symbols: List[Dict[str, Any]]
    ) -> np.ndarray:
        """
        Generate feature embedding from extracted elements
        
        For now, simple feature vector. Will be enhanced with learned embeddings.
        """
        # Create simple feature vector (512 dimensions)
        features = np.zeros(512)
        
        # Encode counts
        features[0] = len(visual_elements)
        features[1] = len(text_annotations)
        features[2] = len(symbols)
        
        # Add some randomness for now (will be replaced with learned features)
        features[3:] = np.random.randn(509) * 0.1
        
        # Normalize
        norm = np.linalg.norm(features)
        if norm > 0:
            features = features / norm
            
        return features


# Convenience function for quick usage
def extract_features(diagram_image: Any, use_vision: bool = False) -> FeatureVector:
    """
    Quick function to extract features from a diagram
    
    Args:
        diagram_image: Image file path, PIL Image, or base64 string
        use_vision: Whether to use vision model
        
    Returns:
        FeatureVector with extracted features
    """
    agent = RealityAnchorAgent()
    return agent.analyze(diagram_image, use_vision=use_vision)
