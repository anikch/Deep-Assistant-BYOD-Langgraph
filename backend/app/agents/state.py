from typing import TypedDict, List, Optional, Any


class AgentState(TypedDict):
    user_message: str
    session_id: str
    user_id: str
    messages: List[Any]       # conversation history as dicts {role, content}
    retrieved_chunks: List[dict]
    current_plan: List[str]
    clarification_needed: bool
    clarification_question: Optional[str]
    selected_skills: List[str]
    code_execution_needed: bool
    execution_outputs: List[dict]
    final_answer: Optional[str]
    citations: List[dict]
    plan_revision_count: int
    agent_run_id: str
    active_skills: List[dict]  # loaded skill definitions
    llm_provider: str           # "gemini" or "azure_openai"
    error: Optional[str]
