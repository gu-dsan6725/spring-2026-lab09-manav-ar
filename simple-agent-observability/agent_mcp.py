"""
Simple Strands Agent with DuckDuckGo, MCP (Context7), and Braintrust Observability.

This agent demonstrates:
- DuckDuckGo web search tool
- MCP (Model Context Protocol) integration with Context7 documentation search
- Braintrust observability using OpenTelemetry
- Anthropic Claude Haiku via Strands
"""

import asyncio
import json
import logging
import os
from typing import Optional

from braintrust.otel import BraintrustSpanProcessor
from ddgs import DDGS
from dotenv import load_dotenv
from opentelemetry.sdk.trace import TracerProvider
from strands import Agent
from strands.telemetry import StrandsTelemetry
from strands.tools.decorator import tool
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,p%(process)s,{%(filename)s:%(lineno)d},%(levelname)s,%(message)s",
)
logger = logging.getLogger(__name__)


# Load environment variables
load_dotenv()


def _get_env_var(
    key: str,
    default: Optional[str] = None
) -> str:
    """Get environment variable or raise error if not found."""
    value = os.getenv(key, default)
    if value is None:
        raise ValueError(f"Environment variable {key} not set")
    return value


@tool
def duckduckgo_search(
    query: str,
    max_results: int = 5
) -> str:
    """
    Search DuckDuckGo for the given query. Use this for current events, news, general information, or any topic that requires web search.

    Args:
        query: The search query string
        max_results: Maximum number of results to return

    Returns:
        JSON string containing search results
    """
    try:
        logger.info(f"Searching DuckDuckGo for: {query}")

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        logger.info(f"Found {len(results)} results")
        return json.dumps(results, indent=2)

    except Exception as e:
        logger.error(f"DuckDuckGo search failed: {e}")
        return json.dumps({"error": str(e)})


def _setup_observability() -> TracerProvider:
    """
    Set up OpenTelemetry with Braintrust for observability.

    Returns:
        Configured TracerProvider instance
    """
    logger.info("Setting up Braintrust observability")

    # Get Braintrust configuration
    braintrust_api_key = _get_env_var("BRAINTRUST_API_KEY")
    braintrust_project = _get_env_var("BRAINTRUST_PROJECT")

    # Create TracerProvider and add Braintrust processor
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(
        BraintrustSpanProcessor(
            api_key=braintrust_api_key,
            parent=braintrust_project
        )
    )

    # Set tracer provider as global
    from opentelemetry import trace
    trace.set_tracer_provider(tracer_provider)

    logger.info(f"Braintrust observability configured for project: {braintrust_project}")
    return tracer_provider


def _create_mcp_transport():
    """Create a streamable HTTP transport for the Context7 MCP server."""
    return streamablehttp_client("https://mcp.context7.com/mcp")


def _create_agent() -> tuple:
    """
    Create and configure the Strands agent with DuckDuckGo and MCP tools.

    Returns:
        Tuple of (Agent instance, MCPClient instance)
    """
    logger.info("Creating Strands agent")

    # Set up observability
    tracer_provider = _setup_observability()
    telemetry = StrandsTelemetry(tracer_provider=tracer_provider)

    # Get API key and set it in environment for LiteLLM
    anthropic_api_key = _get_env_var("ANTHROPIC_API_KEY")
    os.environ["ANTHROPIC_API_KEY"] = anthropic_api_key

    # Configure the agent with system prompt
    system_prompt = """You are a helpful AI assistant with access to DuckDuckGo web search and Context7 documentation search.

Use the DuckDuckGo search tool to find current information, news, and answers to questions.
Use the Context7 MCP tools to search programming documentation and find code examples.
Provide clear, accurate, and helpful responses based on the search results.
Always cite your sources when using search results."""

    # Create Anthropic model
    from strands.models import AnthropicModel

    model = AnthropicModel(
        model_id="claude-3-haiku-20240307",
        max_tokens=4096
    )

    # Initialize MCP client for Context7
    logger.info("Connecting to Context7 MCP server...")
    mcp_client = MCPClient(_create_mcp_transport)

    # Start MCP connection and get tools
    mcp_client.start()
    mcp_tools = mcp_client.list_tools_sync()
    logger.info(f"Loaded {len(mcp_tools)} MCP tools from Context7")

    for t in mcp_tools:
        logger.info(f"  MCP tool: {t.tool_name if hasattr(t, 'tool_name') else t}")

    # Create agent with both DuckDuckGo and MCP tools
    agent = Agent(
        system_prompt=system_prompt,
        model=model,
        tools=[duckduckgo_search] + mcp_tools
    )

    logger.info("Agent created successfully with DuckDuckGo + MCP tools + Braintrust observability")
    return agent, mcp_client


async def _run_agent_async(
    agent: Agent,
    user_input: str
) -> str:
    """
    Run the agent asynchronously with the given input.

    Args:
        agent: The Strands agent instance
        user_input: User's question or prompt

    Returns:
        Agent's response
    """
    logger.info(f"Processing user input: {user_input}")

    response = await agent.invoke_async(user_input)

    logger.info("Agent response generated")
    return response


def main() -> None:
    """Main function to run the agent."""
    logger.info("Starting Simple Agent with Observability + MCP")

    # Create agent with MCP
    agent, mcp_client = _create_agent()

    print("\n" + "="*80)
    print("Simple Agent with Observability + MCP Demo")
    print("="*80 + "\n")

    # Run interactive loop
    print("Ask me anything! I can search the web with DuckDuckGo")
    print("and search programming documentation with Context7 MCP.")
    print("Type 'quit' to exit.\n")

    try:
        while True:
            try:
                user_input = input("You: ").strip()

                if user_input.lower() in ["quit", "exit", "q"]:
                    print("\nGoodbye!")
                    break

                if not user_input:
                    continue

                # Run agent
                response = asyncio.run(_run_agent_async(agent, user_input))

                print(f"\nAgent: {response}\n")

            except EOFError:
                print("\n\nGoodbye!")
                break
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                logger.error(f"Error running agent: {e}")
                print(f"\nError: {e}\n")
    finally:
        # Clean up MCP connection
        logger.info("Shutting down MCP client...")
        mcp_client.stop()
        logger.info("MCP client stopped")


if __name__ == "__main__":
    main()