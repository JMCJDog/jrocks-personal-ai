"""Vision Module - Image and Video Analysis.

Handles interaction with vision-capable models (like Llama 3.2 Vision)
to describe and analyze visual data.
"""

import logging
import base64
import ollama
from pathlib import Path
from typing import Optional, List

# Configure logging
logger = logging.getLogger(__name__)

class VisionEngine:
    """Engine for analyzing images and video frames using multimodal SLMs."""
    
    def __init__(self, model_name: str = "llama3.2") -> None:
        """Initialize the vision engine.
        
        Args:
            model_name: The vision-capable model to use in Ollama.
        """
        self.model_name = model_name
        self._client = ollama.Client()
        logger.info(f"Vision Engine initialized with model '{model_name}'")

    def analyze_image(self, image_data: str, prompt: str = "Describe this image in detail.") -> str:
        """Analyze a base64 encoded image or path to image.
        
        Args:
            image_data: Base64 string of the image or path to image file.
            prompt: Question or instruction for the model.
            
        Returns:
            Text description/analysis from the model.
        """
        try:
            # Check if image_data is a path or base64
            if len(image_data) < 1024 and Path(image_data).exists():
                with open(image_data, "rb") as f:
                    image_bytes = f.read()
            else:
                # Expecting base64 (might have data:image/xxx;base64, prefix)
                if "," in image_data:
                    image_data = image_data.split(",")[1]
                image_bytes = base64.b64decode(image_data)

            logger.info(f"Analyzing image with prompt: {prompt}")
            
            response = self._client.generate(
                model=self.model_name,
                prompt=prompt,
                images=[image_bytes]
            )
            
            return response.get("response", "No visual analysis returned.")
            
        except Exception as e:
            logger.error(f"Vision analysis error: {e}")
            return f"Error analyzing image: {str(e)}"

    def analyze_video_frames(self, frames: List[str], prompt: str = "Summarize the action in these video frames.") -> str:
        """Analyze a sequence of frames (video summarization).
        
        Args:
            frames: List of base64 encoded images.
            prompt: Instruction for the model.
            
        Returns:
            Text summary of the sequence.
        """
        # Multimodal models usually take a few images at a time
        # We'll concatenate the analysis or use a model that supports multi-image
        try:
            image_list = []
            for frame in frames:
                if "," in frame:
                    frame = frame.split(",")[1]
                image_list.append(base64.b64decode(frame))

            # Current Ollama llama3.2 might only handle one or few images well
            # Best to sample or send them all if the model supports it
            response = self._client.generate(
                model=self.model_name,
                prompt=prompt,
                images=image_list
            )
            
            return response.get("response", "No video summary returned.")
            
        except Exception as e:
            logger.error(f"Video analysis error: {e}")
            return f"Error analyzing video: {str(e)}"

if __name__ == "__main__":
    # Test script
    import sys
    engine = VisionEngine()
    if len(sys.argv) > 1:
        print(f"Analysis: {engine.analyze_image(sys.argv[1])}")
    else:
        print("Usage: python vision.py <image_path_or_base64>")
