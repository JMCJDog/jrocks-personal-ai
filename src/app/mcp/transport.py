"""Transport Layer - Communication protocols for MCP.

Implements various transport mechanisms for MCP communication:
- stdio: Standard input/output for local processes
- SSE: Server-Sent Events for HTTP streaming
- WebSocket: Bidirectional real-time communication
"""

from abc import ABC, abstractmethod
from typing import Optional, AsyncIterator, Callable
from dataclasses import dataclass
import asyncio
import json
import sys

from .protocol import MCPMessage


class Transport(ABC):
    """Abstract base class for MCP transports.
    
    Defines the interface for sending and receiving MCP messages
    over different communication protocols.
    """
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish the transport connection."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close the transport connection."""
        pass
    
    @abstractmethod
    async def send(self, message: MCPMessage) -> MCPMessage:
        """Send a message and wait for response.
        
        Args:
            message: The message to send.
        
        Returns:
            MCPMessage: The response message.
        """
        pass
    
    @abstractmethod
    async def send_notification(self, message: MCPMessage) -> None:
        """Send a notification (no response expected).
        
        Args:
            message: The notification message.
        """
        pass
    
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if transport is connected."""
        pass


class StdioTransport(Transport):
    """Standard I/O transport for subprocess communication.
    
    Used for communicating with MCP servers running as
    child processes via stdin/stdout.
    
    Example:
        >>> transport = StdioTransport(["python", "server.py"])
        >>> await transport.connect()
        >>> response = await transport.send(message)
    """
    
    def __init__(
        self,
        command: list[str],
        env: Optional[dict] = None,
    ) -> None:
        """Initialize stdio transport.
        
        Args:
            command: Command to spawn the server process.
            env: Environment variables for the process.
        """
        self.command = command
        self.env = env
        self._process: Optional[asyncio.subprocess.Process] = None
        self._pending: dict[str, asyncio.Future] = {}
        self._read_task: Optional[asyncio.Task] = None
    
    @property
    def is_connected(self) -> bool:
        return self._process is not None and self._process.returncode is None
    
    async def connect(self) -> None:
        """Start the server process."""
        self._process = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.env,
        )
        
        # Start reading responses
        self._read_task = asyncio.create_task(self._read_loop())
    
    async def disconnect(self) -> None:
        """Stop the server process."""
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        
        if self._process:
            self._process.terminate()
            await self._process.wait()
    
    async def send(self, message: MCPMessage) -> MCPMessage:
        """Send a message and wait for response."""
        if not self.is_connected:
            raise RuntimeError("Transport not connected")
        
        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self._pending[message.id] = future
        
        # Send message
        data = message.to_json() + "\n"
        self._process.stdin.write(data.encode())
        await self._process.stdin.drain()
        
        # Wait for response
        try:
            return await asyncio.wait_for(future, timeout=30)
        finally:
            self._pending.pop(message.id, None)
    
    async def send_notification(self, message: MCPMessage) -> None:
        """Send a notification without waiting."""
        if not self.is_connected:
            raise RuntimeError("Transport not connected")
        
        data = message.to_json() + "\n"
        self._process.stdin.write(data.encode())
        await self._process.stdin.drain()
    
    async def _read_loop(self) -> None:
        """Read responses from the server."""
        while self.is_connected:
            try:
                line = await self._process.stdout.readline()
                if not line:
                    break
                
                message = MCPMessage.from_json(line.decode())
                
                # Match to pending request
                if message.id and message.id in self._pending:
                    self._pending[message.id].set_result(message)
                    
            except asyncio.CancelledError:
                break
            except Exception:
                continue


class SSETransport(Transport):
    """Server-Sent Events transport for HTTP streaming.
    
    Provides a unidirectional streaming connection from server
    with HTTP POST for client-to-server messages.
    
    Example:
        >>> transport = SSETransport("http://localhost:8000/mcp")
        >>> await transport.connect()
    """
    
    def __init__(
        self,
        url: str,
        headers: Optional[dict] = None,
    ) -> None:
        """Initialize SSE transport.
        
        Args:
            url: Server URL.
            headers: Optional HTTP headers.
        """
        self.url = url
        self.headers = headers or {}
        self._session = None
        self._connected = False
        self._pending: dict[str, asyncio.Future] = {}
        self._event_task: Optional[asyncio.Task] = None
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    async def connect(self) -> None:
        """Connect to the SSE endpoint."""
        try:
            import aiohttp
            self._session = aiohttp.ClientSession(headers=self.headers)
            self._connected = True
            
            # Start listening for events
            self._event_task = asyncio.create_task(self._event_loop())
            
        except ImportError:
            raise ImportError("aiohttp required: pip install aiohttp")
    
    async def disconnect(self) -> None:
        """Disconnect from the server."""
        self._connected = False
        
        if self._event_task:
            self._event_task.cancel()
            try:
                await self._event_task
            except asyncio.CancelledError:
                pass
        
        if self._session:
            await self._session.close()
    
    async def send(self, message: MCPMessage) -> MCPMessage:
        """Send a message via HTTP POST."""
        if not self.is_connected:
            raise RuntimeError("Transport not connected")
        
        future = asyncio.get_event_loop().create_future()
        self._pending[message.id] = future
        
        async with self._session.post(
            f"{self.url}/message",
            json=message.to_dict(),
        ) as resp:
            if resp.status != 200:
                raise RuntimeError(f"HTTP error: {resp.status}")
        
        try:
            return await asyncio.wait_for(future, timeout=30)
        finally:
            self._pending.pop(message.id, None)
    
    async def send_notification(self, message: MCPMessage) -> None:
        """Send a notification via HTTP POST."""
        if not self.is_connected:
            raise RuntimeError("Transport not connected")
        
        async with self._session.post(
            f"{self.url}/message",
            json=message.to_dict(),
        ) as resp:
            if resp.status != 200:
                raise RuntimeError(f"HTTP error: {resp.status}")
    
    async def _event_loop(self) -> None:
        """Listen for SSE events."""
        try:
            async with self._session.get(f"{self.url}/events") as resp:
                async for line in resp.content:
                    if not self._connected:
                        break
                    
                    line = line.decode().strip()
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            message = MCPMessage.from_json(data)
                            if message.id and message.id in self._pending:
                                self._pending[message.id].set_result(message)
                        except Exception:
                            continue
                            
        except asyncio.CancelledError:
            pass


class WebSocketTransport(Transport):
    """WebSocket transport for bidirectional communication.
    
    Provides full-duplex real-time communication with the
    MCP server over WebSocket.
    
    Example:
        >>> transport = WebSocketTransport("ws://localhost:8000/mcp")
        >>> await transport.connect()
    """
    
    def __init__(
        self,
        url: str,
        headers: Optional[dict] = None,
    ) -> None:
        """Initialize WebSocket transport.
        
        Args:
            url: WebSocket URL.
            headers: Optional HTTP headers.
        """
        self.url = url
        self.headers = headers or {}
        self._ws = None
        self._connected = False
        self._pending: dict[str, asyncio.Future] = {}
        self._receive_task: Optional[asyncio.Task] = None
    
    @property
    def is_connected(self) -> bool:
        return self._connected and self._ws is not None
    
    async def connect(self) -> None:
        """Connect to the WebSocket server."""
        try:
            import websockets
            self._ws = await websockets.connect(
                self.url,
                extra_headers=self.headers,
            )
            self._connected = True
            
            # Start receiving messages
            self._receive_task = asyncio.create_task(self._receive_loop())
            
        except ImportError:
            raise ImportError("websockets required: pip install websockets")
    
    async def disconnect(self) -> None:
        """Disconnect from the server."""
        self._connected = False
        
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        if self._ws:
            await self._ws.close()
    
    async def send(self, message: MCPMessage) -> MCPMessage:
        """Send a message and wait for response."""
        if not self.is_connected:
            raise RuntimeError("Transport not connected")
        
        future = asyncio.get_event_loop().create_future()
        self._pending[message.id] = future
        
        await self._ws.send(message.to_json())
        
        try:
            return await asyncio.wait_for(future, timeout=30)
        finally:
            self._pending.pop(message.id, None)
    
    async def send_notification(self, message: MCPMessage) -> None:
        """Send a notification without waiting."""
        if not self.is_connected:
            raise RuntimeError("Transport not connected")
        
        await self._ws.send(message.to_json())
    
    async def _receive_loop(self) -> None:
        """Receive messages from the server."""
        try:
            async for data in self._ws:
                if not self._connected:
                    break
                
                try:
                    message = MCPMessage.from_json(data)
                    if message.id and message.id in self._pending:
                        self._pending[message.id].set_result(message)
                except Exception:
                    continue
                    
        except asyncio.CancelledError:
            pass


def create_transport(
    transport_type: str,
    **kwargs
) -> Transport:
    """Factory function to create a transport.
    
    Args:
        transport_type: Transport type (stdio, sse, websocket).
        **kwargs: Transport-specific options.
    
    Returns:
        Transport: Configured transport instance.
    """
    transports = {
        "stdio": StdioTransport,
        "sse": SSETransport,
        "websocket": WebSocketTransport,
    }
    
    transport_class = transports.get(transport_type.lower())
    if not transport_class:
        raise ValueError(f"Unknown transport: {transport_type}")
    
    return transport_class(**kwargs)
