from typing import Literal

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers.openai_functions import JsonOutputFunctionsParser
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.tools.retriever import create_retriever_tool
from langgraph.graph import StateGraph, END

from bot.core.ai.setup import get_llm
from bot.core.ai.state import AgentState
from bot.core.knowledge.vector_db import get_retriever

# --- 1. Define the Agents ---

def economy_agent(state: AgentState) -> dict:
    return {"messages": [AIMessage(content="I am the Economy Agent, I would handle this.")]}

def lore_agent(state: AgentState) -> dict:
    """
    Lore Agent (RAG): Uses vector DB to answer questions about organization rules and lore.
    """
    llm = get_llm()
    retriever = get_retriever()

    # Create the RAG tool
    tool = create_retriever_tool(
        retriever,
        "knowledge_base",
        "Searches and returns documents regarding organization rules and lore."
    )
    tools = [tool]

    # System Prompt
    system_prompt_text = (
        "You are the Organization Historian. Use the 'knowledge_base' tool to answer questions about rules and lore. "
        "Do not make things up."
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt_text),
        MessagesPlaceholder(variable_name="messages"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    # Create Agent and Executor
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools)

    # Invoke
    # AgentExecutor expects 'messages' key if using MessagesPlaceholder with that name?
    # No, typically it expects 'input' or 'chat_history'.
    # With `create_tool_calling_agent` + `MessagesPlaceholder("messages")`,
    # we usually pass `{"messages": state["messages"]}`.

    response = agent_executor.invoke({"messages": state["messages"]})

    # The output of AgentExecutor is a dict with keys like 'output'.
    return {"messages": [AIMessage(content=response['output'])]}

def chat_agent(state: AgentState) -> dict:
    """
    Chat Agent (Personality): 'The Hive' personality.
    """
    llm = get_llm()

    # System Prompt
    system_prompt_text = (
        "You are 'The Hive', a ship-board AI for the organization. "
        "You are helpful, slightly robotic, and loyal. Keep answers concise."
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt_text),
        MessagesPlaceholder(variable_name="messages"),
    ])

    chain = prompt | llm

    response = chain.invoke(state)
    return {"messages": [response]}


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

def supervisor_node(state: AgentState) -> dict:
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

    result = supervisor_chain.invoke(state)
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
