"""Video Processing Utility - Keyframe Extraction.

Uses OpenCV to extract frames from video files for analysis by
vision-capable SLMs.
"""

import cv2
import base64
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

class VideoProcessor:
    """Handles video file manipulation and frame extraction."""
    
    @staticmethod
    def extract_keyframes(video_path: str | Path, num_frames: int = 5) -> List[str]:
        """Extract a set number of representative frames from a video.
        
        Args:
            video_path: Path to the video file.
            num_frames: Number of frames to extract (evenly spaced).
            
        Returns:
            List[str]: Base64 encoded JPEG frames.
        """
        path = Path(video_path)
        if not path.exists():
            logger.error(f"Video file not found: {video_path}")
            return []

        frames_b64 = []
        try:
            cap = cv2.VideoCapture(str(path))
            if not cap.isOpened():
                logger.error(f"Could not open video: {video_path}")
                return []

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames <= 0:
                logger.error("Video has no frames.")
                return []

            # Calculate intervals
            interval = max(1, total_frames // (num_frames + 1))
            
            for i in range(num_frames):
                frame_idx = (i + 1) * interval
                if frame_idx >= total_frames:
                    break
                
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if ret:
                    # Resize to a reasonable size for the SLM (max 640px)
                    h, w = frame.shape[:2]
                    if w > 640:
                        new_w = 640
                        new_h = int(h * (640 / w))
                        frame = cv2.resize(frame, (new_w, new_h))
                    
                    # Encode to JPEG
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    b64_str = base64.b64encode(buffer).decode('utf-8')
                    frames_b64.append(f"data:image/jpeg;base64,{b64_str}")

            cap.release()
            logger.info(f"Extracted {len(frames_b64)} frames from {path.name}")
            
        except Exception as e:
            logger.error(f"Error extracting frames: {e}")
        
        return frames_b64

    @staticmethod
    def get_video_info(video_path: str | Path) -> dict:
        """Get basic metadata about a video file."""
        path = Path(video_path)
        info = {"filename": path.name, "exists": path.exists()}
        
        if path.exists():
            try:
                cap = cv2.VideoCapture(str(path))
                info["duration_sec"] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS))
                info["resolution"] = f"{int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}"
                cap.release()
            except Exception:
                pass
        return info
