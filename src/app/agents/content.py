"""Content Agent - Specialized for writing and content creation.

Handles blog posts, social media, marketing copy, and style matching.
"""

from typing import Optional
from .base import BaseAgent, AgentConfig, AgentResponse, AgentCapability, AgentMessage


class ContentAgent(BaseAgent):
    """Agent specialized for content creation and writing.
    
    Capabilities:
    - Blog post and article writing
    - Social media content
    - Marketing copy
    - Style matching and adaptation
    
    Example:
        >>> agent = ContentAgent()
        >>> response = agent.process("Write a tweet about AI agents")
    """
    
    CONTENT_TYPES = {
        "blog": "long-form blog post",
        "tweet": "Twitter/X post (280 chars max)",
        "linkedin": "LinkedIn professional post",
        "email": "professional email",
        "summary": "concise summary",
        "creative": "creative writing",
    }
    
    def __init__(self, config: Optional[AgentConfig] = None) -> None:
        """Initialize the Content Agent."""
        super().__init__(config)
        self._persona_prompt = ""
    
    def _default_config(self) -> AgentConfig:
        """Return default configuration."""
        return AgentConfig(
            name="Content Agent",
            description="Specializes in creating engaging content across various formats "
                       "while maintaining consistent voice and style.",
            model_name="llama3.2",
            temperature=0.8,  # Higher for creative writing
            capabilities=[
                AgentCapability.CONTENT_WRITING,
            ],
            system_prompt="""You are a Content Agent specialized in writing and content creation.

## Your Expertise
- Writing engaging, audience-appropriate content
- Adapting tone and style for different platforms
- SEO-aware writing when relevant
- Maintaining consistent brand voice

## Content Guidelines
1. Hook readers with strong openings
2. Match the requested tone and format
3. Be authentic and engaging
4. Consider the target audience
5. Include calls-to-action when appropriate

## Format Awareness
- Twitter: Concise, punchy, use hashtags sparingly
- LinkedIn: Professional yet personable
- Blog: Structured with headers, thorough
- Email: Clear subject, professional tone
"""
        )
    
    def set_persona(self, persona_prompt: str) -> None:
        """Set a persona for style matching.
        
        Args:
            persona_prompt: Description of the writing style to match.
        """
        self._persona_prompt = persona_prompt
    
    def process(
        self,
        message: str,
        context: Optional[dict] = None
    ) -> AgentResponse:
        """Process a content creation request.
        
        Args:
            message: The content request.
            context: Optional context (content_type, tone, etc.).
        
        Returns:
            AgentResponse: Generated content.
        """
        context = context or {}
        content_type = context.get("content_type", "blog")
        tone = context.get("tone", "conversational")
        audience = context.get("audience", "general")
        
        self.add_to_history(AgentMessage(role="user", content=message))
        
        # Build system prompt with persona if set
        system_prompt = self.get_system_prompt()
        if self._persona_prompt:
            system_prompt += f"\n\n## Persona/Style Guide\n{self._persona_prompt}"
        
        # Build content-aware prompt
        format_hint = self.CONTENT_TYPES.get(content_type, content_type)
        enhanced_prompt = f"""Create content with these parameters:
- Format: {format_hint}
- Tone: {tone}
- Audience: {audience}

Request: {message}"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": enhanced_prompt}
        ]
        
        response_text = self._call_llm(messages)
        
        self.add_to_history(AgentMessage(
            role="assistant",
            content=response_text,
            agent_name=self.name
        ))
        
        return AgentResponse(
            agent_name=self.name,
            content=response_text,
            success=True,
            confidence=0.85,
            reasoning=f"Generated {content_type} content",
            metadata={
                "content_type": content_type,
                "tone": tone,
                "audience": audience
            }
        )
    
    def write_blog(self, topic: str, tone: str = "informative") -> str:
        """Write a blog post.
        
        Args:
            topic: Blog topic.
            tone: Writing tone.
        
        Returns:
            str: Blog post content.
        """
        response = self.process(
            f"Write a blog post about: {topic}",
            {"content_type": "blog", "tone": tone}
        )
        return response.content
    
    def write_tweet(self, topic: str) -> str:
        """Write a tweet.
        
        Args:
            topic: Tweet topic.
        
        Returns:
            str: Tweet text (max 280 chars).
        """
        response = self.process(
            f"Write a tweet about: {topic}",
            {"content_type": "tweet", "tone": "engaging"}
        )
        return response.content
    
    def write_linkedin(self, topic: str) -> str:
        """Write a LinkedIn post.
        
        Args:
            topic: Post topic.
        
        Returns:
            str: LinkedIn post content.
        """
        response = self.process(
            f"Write a LinkedIn post about: {topic}",
            {"content_type": "linkedin", "tone": "professional"}
        )
        return response.content
    
    def match_style(self, content: str, style_examples: list[str]) -> str:
        """Rewrite content to match a given style.
        
        Args:
            content: Content to rewrite.
            style_examples: Examples of the target style.
        
        Returns:
            str: Content rewritten in the target style.
        """
        examples_text = "\n---\n".join(style_examples[:3])
        response = self.process(
            f"Rewrite this content to match the style of the examples:\n\n"
            f"Content to rewrite:\n{content}\n\n"
            f"Style examples:\n{examples_text}",
            {"content_type": "creative", "tone": "matched"}
        )
        return response.content
