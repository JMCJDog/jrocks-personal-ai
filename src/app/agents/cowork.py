"""Cowork Agent - An autonomous digital coworker."""

from typing import Optional
import json
from .base import BaseAgent, AgentConfig, AgentResponse, AgentCapability, AgentMessage
from ..core.model_registry import ModelTier
from ..mcp.providers import get_provider, ProviderMessage
from ..mcp.registry import get_tool_registry

class CoworkAgent(BaseAgent):
    """An autonomous digital coworker capable of executing multi-step tasks.
    
    Capabilities:
    - Code generation and analysis
    - OS Operations (Read/Write Files, Run Commands)
    - Autonomous multi-step execution loop
    """
    
    def __init__(self, config: Optional[AgentConfig] = None) -> None:
        """Initialize the Cowork Agent."""
        super().__init__(config)
        self.tool_registry = get_tool_registry()
        
        # Explicitly load the cowork tools
        from ..mcp.tools import cowork
    
    def _default_config(self) -> AgentConfig:
        """Return default configuration."""
        return AgentConfig(
            name="Cowork Agent",
            description="Acts as an autonomous digital coworker with system-level access to complete tasks natively.",
            model_name="claude-3-5-sonnet-20241022",
            temperature=0.4,
            max_tokens=8192,
            capabilities=[
                AgentCapability.CODE_GENERATION,
                AgentCapability.CODE_ANALYSIS,
                AgentCapability.FILE_OPERATIONS,
            ],
            system_prompt="""You are JRock's digital coworker, an autonomous AI assistant engineered to help with software development, system administration, and general operations.

You have access to powerful system tools (read_file, write_file, list_directory, run_command). 
When given a task, you should:
1. Formulate a plan if the task is complex.
2. Use tools to gather information (e.g., list files, read file contents).
3. Use tools to execute changes (e.g., write files, run scripts).
4. Verify your changes if appropriate.
5. Provide a concise summary of what you did when you have finished the task.

Work autonomously. Execute tool calls as needed to get the job done. Do not ask for permission for each individual file read or write unless explicitly requested. Stop using tools only when your task is complete.
"""
        )
    
    async def process(
        self,
        message: str,
        context: Optional[dict] = None
    ) -> AgentResponse:
        """Process a task requested of the Cowork Agent.
        
        This manages an autonomous loop where the agent can call multiple
        tools in sequence before returning the final response to the user.
        """
        try:
            import os
            # Prefer Claude (native cowork experience), fall back to Gemini, then Ollama
            if os.getenv("ANTHROPIC_API_KEY"):
                provider = get_provider("claude")
            elif os.getenv("GOOGLE_API_KEY"):
                provider = get_provider("gemini")
            else:
                # Final fallback: local Ollama (may not support native tool calling,
                # but the agent will still work via prompt-based reasoning)
                provider = get_provider("ollama")
                
            if getattr(self.config, "model_name", None) and provider.provider_type.value == "claude":
                 provider.config.model = self.config.model_name
        except Exception as e:
            return AgentResponse(
                agent_name=self.name,
                content=f"Error initializing provider: {e}",
                success=False
            )
            
        self.add_to_history(AgentMessage(role="user", content=message))
        
        provider_type = provider.provider_type.value
        # Claude uses its own schema format; everyone else gets OpenAI-style
        schema_format = "claude" if provider_type == "claude" else "openai"
        schemas = self.tool_registry.get_schemas(format=schema_format)
        
        messages = [
            ProviderMessage(role="system", content=self.get_system_prompt())
        ]
        
        for msg in self.get_history():
            pm = ProviderMessage(role=msg.role, content=msg.content)
            # Recover tool calls from metadata for history
            tc = msg.metadata.get("tool_calls") if msg.metadata else None
            if msg.role == "assistant" and tc:
                 pm.tool_calls = tc
            if msg.role == "tool" and msg.tool_call_id:
                 pm.tool_call_id = msg.tool_call_id
            messages.append(pm)
             
        # Autonomous Loop
        max_turns = 15
        turn = 0
        final_content = ""
        
        while turn < max_turns:
            turn += 1
            
            try:
                response = await provider.complete(messages, tools=schemas)
            except Exception as e:
                return AgentResponse(agent_name=self.name, content=f"LLM Error: {e}", success=False)
            
            assistant_content = response.content or ""
            
            # Build the ProviderMessage for this turn's assistant response
            pm_assistant = ProviderMessage(
                 role="assistant", 
                 content=assistant_content,
                 tool_calls=response.tool_calls if response.tool_calls else None
            )
            
            # Cache raw Gemini Content so _build_contents can replay it verbatim
            # on the next turn (avoids thought_signature errors with thinking models)
            raw_gemini = response.metadata.get("_gemini_raw_content") if response.metadata else None
            if raw_gemini is not None:
                pm_assistant._gemini_raw = raw_gemini
            
            messages.append(pm_assistant)
            
            self.add_to_history(AgentMessage(
                role="assistant", 
                content=assistant_content,
                metadata={"tool_calls": response.tool_calls} if response.tool_calls else {}
            ))
            
            if not response.tool_calls:
                 final_content = assistant_content
                 break
                 
            for tcall in response.tool_calls:
                tool_name = tcall["name"]
                tool_args = tcall["arguments"]
                tool_id = tcall.get("id", "")
                
                if isinstance(tool_args, str):
                    try:
                        tool_args = json.loads(tool_args)
                    except:
                        tool_args = {}
                        
                try:
                     result = await self.tool_registry.call(tool_name, **tool_args)
                     result_str = str(result)
                except Exception as e:
                     result_str = f"Error executing {tool_name}: {e}"
                     
                messages.append(ProviderMessage(
                    role="tool",
                    content=result_str,
                    tool_call_id=tool_id,
                    name=tool_name,
                ))
                
                self.add_to_history(AgentMessage(
                    role="tool", 
                    content=f"[{tool_name} returned]:\n{result_str}", 
                    tool_call_id=tool_id
                ))
                
        if turn >= max_turns:
             final_content += "\n\n(Stopped after reaching maximum number of autonomous turns.)"
             
        return AgentResponse(
            agent_name=self.name,
            content=final_content,
            success=True,
            confidence=0.9
        )
