import operator
from typing import TypedDict, Annotated, Optional, List, Dict, Any
from langchain_core.messages import BaseMessage


class TeamState(TypedDict, total=False):
    """Shared state flowing through all agents in the Supervisor + Team graph.

    Fields:
        messages: Conversation history, accumulated via operator.add.
        next: The routing decision — which agent or FINISH.
        session_id: Unique identifier for the conversation session.
        model: Optional model name override.
        pending_tasks: Tasks to be executed, planned by the supervisor LLM.
        completed_tasks: Tasks that have been completed.
        iteration_count: Safety counter to prevent infinite loops.
    """
    messages: Annotated[List[BaseMessage], operator.add]
    next: str
    session_id: str
    model: Optional[str]
    pending_tasks: List[Dict[str, Any]]
    completed_tasks: List[Dict[str, Any]]
    iteration_count: int
