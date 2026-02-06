"""
TrOCR engine for handwritten text recognition.
"""
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
import torch
from typing import Optional
import os


class TrOCREngine:
    """TrOCR-based handwritten text recognition engine."""
    
    def __init__(self, model_name: str = "microsoft/trocr-large-handwritten", use_gpu: bool = True):
        """
        Initialize TrOCR model.
        
        Args:
            model_name: HuggingFace model name
            use_gpu: Whether to use GPU acceleration
        """
        self.device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        print(f"Loading TrOCR model on {self.device}...")
        
        self.processor = TrOCRProcessor.from_pretrained(model_name)
        self.model = VisionEncoderDecoderModel.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()
        
        print(f"TrOCR model loaded successfully")
    
    def recognize(self, image: Image.Image) -> dict:
        """
        Recognize handwritten text in image.
        
        Args:
            image: PIL Image of text region
            
        Returns:
            dict: {
                'text': str,
                'confidence': float
            }
        """
        # Preprocess image
        pixel_values = self.processor(image, return_tensors="pt").pixel_values
        pixel_values = pixel_values.to(self.device)
        
        # Generate text
        with torch.no_grad():
            generated_ids = self.model.generate(pixel_values)
        
        # Decode text
        generated_text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        # Calculate confidence (simplified - use logits for actual confidence)
        # For MVP, use a heuristic based on text length and model certainty
        confidence = 0.75 if len(generated_text) > 0 else 0.0
        
        return {
            'text': generated_text,
            'confidence': confidence
        }
    
    def recognize_batch(self, images: list[Image.Image], batch_size: int = 8) -> list[dict]:
        """
        Recognize text in multiple images (batch processing).
        
        Args:
            images: List of PIL Images
            batch_size: Batch size for processing
            
        Returns:
            list: List of recognition results
        """
        results = []
        
        for i in range(0, len(images), batch_size):
            batch = images[i:i + batch_size]
            
            # Process batch
            pixel_values = self.processor(batch, return_tensors="pt", padding=True).pixel_values
            pixel_values = pixel_values.to(self.device)
            
            # Generate text
            with torch.no_grad():
                generated_ids = self.model.generate(pixel_values)
            
            # Decode texts
            generated_texts = self.processor.batch_decode(generated_ids, skip_special_tokens=True)
            
            # Add results
            for text in generated_texts:
                confidence = 0.75 if len(text) > 0 else 0.0
                results.append({
                    'text': text,
                    'confidence': confidence
                })
        
        return results


# Global instance (lazy loaded)
_trocr_engine: Optional[TrOCREngine] = None


def get_trocr_engine(model_name: str = "microsoft/trocr-large-handwritten", use_gpu: bool = True) -> TrOCREngine:
    """
    Get or create TrOCR engine instance (singleton pattern).
    
    Args:
        model_name: HuggingFace model name
        use_gpu: Whether to use GPU
        
    Returns:
        TrOCREngine instance
    """
    global _trocr_engine
    
    if _trocr_engine is None:
        _trocr_engine = TrOCREngine(model_name=model_name, use_gpu=use_gpu)
    
    return _trocr_engine
