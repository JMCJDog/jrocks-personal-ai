
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from .slm_engine import quick_generate
from .consciousness import ConsciousnessState, default_consciousness

logger = logging.getLogger(__name__)

class SurveillanceSystem:
    """
    Bio-Digital Surveillance & Pattern Recognition System.
    
    Layer 1 (The Screener): Uses fast/cheap models (Gemini Flash) to scan streams.
    Layer 2 (The Analyst): Uses high-intelligence models (Claude Sonnet/Opus) for deep dive.
    """
    
    def __init__(self, consciousness: Optional[ConsciousnessState] = None):
        self.consciousness = consciousness or default_consciousness
    
    def scan(self, signal_data: str, source: str = "network_log") -> Dict[str, Any]:
        """
        Layer 1: Rapidly scan data for anomalies using a fast model.
        """
        prompt = (
            f"Analyze the following {source} signal for security anomalies, relevant patterns, or noise.\n"
            "Classify as: 'NOISE' (ignore), 'RELEVANT' (worth tracking), or 'CRITICAL' (immediate threat/insight).\n"
            "Return JSON: {{\"classification\": \"...\", \"confidence\": 0.0-1.0, \"summary\": \"...\"}}\n\n"
            f"Signal Data:\n{signal_data}"
        )
        
        # Use Gemini Flash for speed/cost if available, otherwise local Llama
        # "gemini-1.5-flash" is usually the content-window king for this
        try:
            # We use quick_generate which uses SLMEngine -> ModelRouter
            response = quick_generate(prompt, model="gemini-1.5-flash")
            
            # Simple parsing (in production use structured output/json mode)
            import json
            import re
            
            # Extract JSON block
            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                result = json.loads(match.group(0))
            else:
                layout = response.lower()
                if "critical" in layout:
                    result = {"classification": "CRITICAL", "confidence": 0.8, "summary": response}
                elif "relevant" in layout:
                     result = {"classification": "RELEVANT", "confidence": 0.6, "summary": response}
                else:
                    result = {"classification": "NOISE", "confidence": 0.9, "summary": "No interesting patterns found."}

            # Trigger Layer 2 if needed
            if result["classification"] in ["RELEVANT", "CRITICAL"]:
                return self.analyze(signal_data, result)
            
            return result

        except Exception as e:
            logger.error(f"Surveillance scan failed: {e}")
            return {"classification": "ERROR", "error": str(e)}

    def analyze(self, signal_data: str, scan_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Layer 2: Deep analysis of flagged signals using a smarter model.
        """
        logger.info(f"Escalating signal to Layer 2 Analysis: {scan_result['summary']}")
        
        prompt = (
            "Deep Dive Analysis Required.\n"
            f"Initial Scan: {scan_result['classification']} - {scan_result['summary']}\n\n"
            "Analyze the intent, origin, and potential impact of this signal.\n"
            "Connect this to broader patterns if possible.\n\n"
            f"Signal Data:\n{signal_data}"
        )
        
        # Use a high-intelligence model
        # Try Claude first, then GPT-4
        model = "claude-3-5-sonnet-20240620" 
        
        try:
            analysis = quick_generate(prompt, model=model)
            
            # Update Consciousness
            self.consciousness.add_memory(
                content=f"Surveillance Alert ({scan_result['classification']}): {analysis}",
                importance=0.9 if scan_result["classification"] == "CRITICAL" else 0.6,
                category="security_alert",
                source="surveillance_system"
            )
            
            if scan_result["classification"] == "CRITICAL":
                self.consciousness.update_emotional_state("security alert detection")
            
            return {
                "scan": scan_result,
                "deep_analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
             logger.error(f"Surveillance analysis failed: {e}")
             return scan_result

# Singleton instance
default_surveillance = SurveillanceSystem()
