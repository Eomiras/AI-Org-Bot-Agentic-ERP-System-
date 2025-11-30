from typing import Literal

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers.openai_functions import JsonOutputFunctionsParser
from langchain_core.messages import HumanMessage, AIMessage
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langgraph.graph import StateGraph, END

from bot.core.ai.setup import get_llm
from bot.core.ai.state import AgentState
from bot.core.ai.tools.economy import get_user_balance, transfer_money

# --- 1. Define the Agents (Mock Workers) ---

def create_agent(llm, tools, system_prompt: str):
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            system_prompt,
        ),
        MessagesPlaceholder(variable_name="messages"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    agent = create_openai_tools_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools)
    return executor

async def economy_agent(state: AgentState) -> dict:
    llm = get_llm()
    tools = [get_user_balance, transfer_money]
    system_prompt = "You are the Economy Agent. You can check balances and transfer money. Use the tools provided."
    agent_executor = create_agent(llm, tools, system_prompt)

    # Run the agent asynchronously
    result = await agent_executor.ainvoke({"messages": state["messages"]})

    # We want to return the last message from the agent as the result
    return {"messages": [AIMessage(content=result["output"])]}

async def lore_agent(state: AgentState) -> dict:
    return {"messages": [AIMessage(content="I am the Lore Agent, I would handle this.")]}

async def chat_agent(state: AgentState) -> dict:
    return {"messages": [AIMessage(content="I am the Chat Agent, I would handle this.")]}


# --- 2. Define the Supervisor ---

# The options for the supervisor to choose from. WE MUST INCLUDE FINISH.
options = ["economy_agent", "lore_agent", "chat_agent", "FINISH"]

# The system prompt
system_prompt = (
    "You are the supervisor. You manage the following workers: [economy_agent, lore_agent, chat_agent]. "
    "Given a user request, respond with the name of the worker to act next, or 'FINISH' if the user request is satisfied or requires no specific worker action."
)

# Function definition for OpenAI function calling (to force structured output)
function_def = {
    "name": "route",
    "description": "Select the next role.",
    "parameters": {
        "title": "routeSchema",
        "type": "object",
        "properties": {
            "next": {
                "title": "Next",
                "anyOf": [
                    {"enum": options},
                ],
            }
        },
        "required": ["next"],
    },
}

async def supervisor_node(state: AgentState) -> dict:
    """
    The supervisor node decides which agent should act next.
    """
    llm = get_llm()
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="messages"),
            (
                "system",
                "Given the conversation above, who should act next? Select one of: {options} or FINISH.",
            ),
        ]
    ).partial(options=str(options), team_members=", ".join(options))

    # Using function calling to ensure we get a valid "next" step
    supervisor_chain = (
        prompt
        | llm.bind_functions(functions=[function_def], function_call="route")
        | JsonOutputFunctionsParser()
    )

    result = await supervisor_chain.ainvoke(state)
    return result


# --- 3. Build the Graph ---

workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("economy_agent", economy_agent)
workflow.add_node("lore_agent", lore_agent)
workflow.add_node("chat_agent", chat_agent)

# Add edges
# From supervisor, we branch to the worker or END
workflow.add_conditional_edges(
    "supervisor",
    lambda x: x["next"],
    {
        "economy_agent": "economy_agent",
        "lore_agent": "lore_agent",
        "chat_agent": "chat_agent",
        "FINISH": END
    }
)

# From workers, we go back to supervisor
workflow.add_edge("economy_agent", "supervisor")
workflow.add_edge("lore_agent", "supervisor")
workflow.add_edge("chat_agent", "supervisor")

# Set entry point
workflow.set_entry_point("supervisor")

# Compile
app = workflow.compile()
