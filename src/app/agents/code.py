"""Code Agent - Specialized for code generation and analysis.

Handles code writing, debugging, refactoring, and technical analysis.
"""

from typing import Optional
from .base import BaseAgent, AgentConfig, AgentResponse, AgentCapability, AgentMessage


class CodeAgent(BaseAgent):
    """Agent specialized for code generation and analysis.
    
    Capabilities:
    - Code generation in multiple languages
    - Code review and analysis
    - Bug detection and debugging
    - Refactoring suggestions
    
    Example:
        >>> agent = CodeAgent()
        >>> response = agent.process("Write a Python function to parse JSON")
    """
    
    SUPPORTED_LANGUAGES = {
        "python", "javascript", "typescript", "java", "go", 
        "rust", "cpp", "c", "csharp", "ruby", "php", "swift"
    }
    
    def __init__(self, config: Optional[AgentConfig] = None) -> None:
        """Initialize the Code Agent."""
        super().__init__(config)
    
    def _default_config(self) -> AgentConfig:
        """Return default configuration."""
        return AgentConfig(
            name="Code Agent",
            description="Specializes in writing, analyzing, and debugging code "
                       "across multiple programming languages.",
            model_name="llama3.2",
            temperature=0.2,  # Low for precise code generation
            max_tokens=4096,  # Higher for code blocks
            capabilities=[
                AgentCapability.CODE_GENERATION,
                AgentCapability.CODE_ANALYSIS,
            ],
            system_prompt="""You are a Code Agent specialized in software development.

## Your Expertise
- Writing clean, efficient, well-documented code
- Debugging and fixing issues
- Code review and best practices
- Multiple programming languages (Python, JS, TS, Go, Rust, etc.)

## Guidelines
1. Always include proper error handling
2. Add docstrings and comments for complex logic
3. Follow language-specific conventions and best practices
4. Provide explanation alongside code when helpful
5. Consider edge cases and input validation

## Code Format
Always wrap code in appropriate markdown code blocks with language specification.
"""
        )
    
    def process(
        self,
        message: str,
        context: Optional[dict] = None
    ) -> AgentResponse:
        """Process a code-related request.
        
        Args:
            message: The coding task or question.
            context: Optional context (language, existing code, etc.).
        
        Returns:
            AgentResponse: Generated code or analysis.
        """
        context = context or {}
        language = context.get("language", "python")
        existing_code = context.get("code", "")
        
        self.add_to_history(AgentMessage(role="user", content=message))
        
        # Build enhanced prompt
        enhanced_prompt = f"Task: {message}\n"
        if language:
            enhanced_prompt += f"\nLanguage: {language}"
        if existing_code:
            enhanced_prompt += f"\n\nExisting code to work with:\n```{language}\n{existing_code}\n```"
        
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": enhanced_prompt}
        ]
        
        response_text = self._call_llm(messages)
        
        self.add_to_history(AgentMessage(
            role="assistant",
            content=response_text,
            agent_name=self.name
        ))
        
        # Detect if response contains code
        has_code = "```" in response_text
        
        return AgentResponse(
            agent_name=self.name,
            content=response_text,
            success=True,
            confidence=0.85 if has_code else 0.7,
            reasoning=f"Code generation for {language}" if has_code else "Code analysis",
            metadata={"language": language, "has_code_block": has_code}
        )
    
    def generate_code(
        self,
        description: str,
        language: str = "python"
    ) -> str:
        """Generate code from a description.
        
        Args:
            description: What the code should do.
            language: Target programming language.
        
        Returns:
            str: Generated code.
        """
        response = self.process(description, {"language": language})
        return response.content
    
    def analyze_code(self, code: str, language: str = "python") -> str:
        """Analyze existing code.
        
        Args:
            code: The code to analyze.
            language: Programming language.
        
        Returns:
            str: Analysis results.
        """
        response = self.process(
            "Analyze this code for potential issues, suggest improvements",
            {"language": language, "code": code}
        )
        return response.content
    
    def debug_code(self, code: str, error: str, language: str = "python") -> str:
        """Debug code with a specific error.
        
        Args:
            code: The problematic code.
            error: The error message.
            language: Programming language.
        
        Returns:
            str: Debugging suggestions and fixed code.
        """
        response = self.process(
            f"Debug this code. Error: {error}",
            {"language": language, "code": code}
        )
        return response.content
