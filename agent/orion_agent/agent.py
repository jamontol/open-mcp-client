"""
This is the main entry point for the agent.
It defines the workflow graph, state, tools, nodes and edges.
"""
import os
from typing_extensions import Literal, TypedDict, Dict, List, Any, Union, Optional
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from copilotkit import CopilotKitState
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from copilotkit.langgraph import (copilotkit_exit)
from dotenv import load_dotenv

load_dotenv()

MCP_TRANSPORT = os.getenv("SERVER__TRANSPORT", "streamable-http")
MCP_HOST = os.getenv("SERVER__HOST", "localhost")
MCP_PORT = int(os.getenv("SERVER__PORT", 8005))
MCP_PATH = os.getenv("SERVER__PATH", "/mcp")
MCP_CLIENT_P7 = os.getenv("SERVER__CLIENT_P7", "xxx")
MCP_AGENTCORE_URL = os.getenv(
    "CLOUD_AGENTCORE_URL", "https://amrt0001-es-gw-uq4rbba6kp.gateway.bedrock-agentcore.eu-west-1.amazonaws.com/mcp"
)

# https://amrt0001-es-gw-xtechzd7oz.gateway.bedrock-agentcore.eu-west-1.amazonaws.com/mcp

# OAuth client credentials
CLIENT_ID = "gl;onyx-obsidian;work/f9c088b4-9717-4987-9742-f7cfcbdb76d2"  # "mvp-oauth-client"
CLIENT_SECRET = os.getenv("OIDC__CLIENT_SECRET", "xxx")

JWT_URL = "https://onyx-obsidian.work.global.platform.bbva.com/auth/token"
logger.remove()
logger.add(sys.stderr, format="<level>{level}</level> | {message}")
MCP_AGENTCORE_URL = os.getenv(
    "CLOUD_AGENTCORE_URL", "https://amrt0001-es-gw-uq4rbba6kp.gateway.bedrock-agentcore.eu-west-1.amazonaws.com/mcp"
)


def get_jwt_token() -> str:
    """Retrieve JWT token using OAuth2 client_credentials."""
    try:
        response = httpx.post(
            JWT_URL, params={"grant_type": "client_credentials"}, auth=(CLIENT_ID, CLIENT_SECRET), data=""
        )

        response.raise_for_status()
        token_response = response.json()

        token = token_response.get("access_token")
        if not token:
            raise RuntimeError("JWT token not found in response")

        return token

    except httpx.HTTPStatusError as e:
        logger.error(f"JWT request failed: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Error retrieving JWT token: {e}")
        raise


# Define the connection type structures
class StdioConnection(TypedDict):
    command: str
    args: List[str]
    transport: Literal["stdio"]

class SSEConnection(TypedDict):
    url: str
    transport: Literal["sse"]

class HTTPConnection(TypedDict):
    url: str
    transport: Literal["http_streamable"]

# Type for MCP configuration
MCPConfig = Dict[str, Union[StdioConnection, SSEConnection, HTTPConnection]]

class AgentState(CopilotKitState):
    """
    Here we define the state of the agent

    In this instance, we're inheriting from CopilotKitState, which will bring in
    the CopilotKitState fields. We're also adding a custom field, `mcp_config`,
    which will be used to configure MCP services for the agent.
    """
    # Define mcp_config as an optional field without skipping validation
    mcp_config: Optional[MCPConfig]
    openai_api_key: Optional[str]

# Default MCP configuration to use when no configuration is provided in the state
# Uses relative paths that will work within the project structure

ORION_MCP_CONFIG: MCPConfig = {
    "orion-mcp": {
        "url": MCP_AGENTCORE_URL,
        "transport": "http_streamable",
    },
}

async def chat_node(state: AgentState, config: RunnableConfig) -> Command[Literal["__end__"]]:
    """
    This is a simplified agent that uses the ReAct agent as a subgraph.
    It handles both chat responses and tool execution in one node.
    """
    # Get MCP configuration from state, or use the default config if not provided
    mcp_config = state.get("mcp_config", DEFAULT_MCP_CONFIG)
    # Get OpenAI API key from state
    openai_api_key = state.get("openai_api_key") 

    print(f"mcp_config: {mcp_config}, default: {DEFAULT_MCP_CONFIG}")
    # Set up the MCP client and tools using the configuration from state

    mcp_client = MultiServerMCPClient(mcp_config)
    mcp_tools = await mcp_client.get_tools()
    
    # async with MultiServerMCPClient(mcp_config) as mcp_client:
    #     # Get the tools
    #     mcp_tools = mcp_client.get_tools()
        
    # Create the react agent
    model = ChatOpenAI(model="gpt-4o", api_key=openai_api_key)
    '''
    model = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-lite",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0,
    convert_system_message_to_human=True # Helper for older Gemini versions if needed
    )


    model = ChatOpenRouter(
    model="nvidia/nemotron-3-super-120b-a12b:free",
    api_key= os.getenv("OPENROUTER_API_KEY"),
    temperature=0
    )
    '''
    react_agent  = create_agent(model, mcp_tools)
    #react_agent = create_react_agent(model, mcp_tools)
    
    # Prepare messages for the react agent
    agent_input = {
        "messages": state["messages"]
    }
    
    # Run the react agent subgraph with our input
    agent_response = await react_agent.ainvoke(agent_input)
    
    # Update the state with the new messages
    updated_messages = state["messages"] + agent_response.get("messages", []) 
    await copilotkit_exit(config)
    # End the graph with the updated messages
    # added the openai_api_keyand the mcp_config to modify the state
    return Command(
        goto=END,
        update={
            "messages": updated_messages,
            "openai_api_key": state.get("openai_api_key"),
            "mcp_config": state.get("mcp_config", DEFAULT_MCP_CONFIG)
        },
    )


# Define the workflow graph with only a chat node
workflow = StateGraph(AgentState)
workflow.add_node("chat_node", chat_node)
workflow.set_entry_point("chat_node")

# Compile the workflow graph
graph = workflow.compile() # MemorySaver()