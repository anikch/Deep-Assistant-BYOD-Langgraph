"""
Deep Agents SDK - LangGraph implementation.

Graph nodes:
1. analyze_input: analyze user message, detect intent & clarification need
2. clarify_if_needed: generate clarification question and halt
3. build_plan: create step-by-step research plan
4. choose_skills: select applicable skills
5. retrieve_context: search Chroma for relevant chunks
6. decide_code_execution: decide if code generation/execution is needed
7. run_tools_or_code: execute code or skill tools
8. revise_plan: revise plan based on retrieved context
9. compose_answer: generate final answer with citations
10. persist_memory: save to DB (handled externally)
"""

import json
import logging
from typing import Literal

from langgraph.graph import StateGraph, END

try:
    from langgraph.checkpoint.memory import MemorySaver
except ImportError:
    try:
        from langgraph.checkpoint import MemorySaver
    except ImportError:
        # Fallback: create a simple in-memory checkpointer
        class MemorySaver:
            def __init__(self):
                self._data = {}

            def get(self, config):
                thread_id = config.get("configurable", {}).get("thread_id", "default")
                return self._data.get(thread_id)

            def put(self, config, checkpoint, metadata):
                thread_id = config.get("configurable", {}).get("thread_id", "default")
                self._data[thread_id] = checkpoint

from app.agents.state import AgentState
from app.core.llm_provider import get_llm
from app.services.knowledge_store import KnowledgeStore

logger = logging.getLogger(__name__)

# Shared in-memory checkpointer (session-scoped via thread_id)
memory_saver = MemorySaver()


def _llm_call(prompt: str, system: str = "", provider: str = "gemini") -> str:
    """Helper to call LLM and return text response."""
    try:
        llm = get_llm(provider)
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))

        response = llm.invoke(messages)
        return response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return f"[LLM Error: {e}]"


def _format_history(messages: list) -> str:
    """Format conversation history for context injection."""
    if not messages:
        return "No previous conversation."
    parts = []
    for m in messages[-10:]:  # Last 10 messages
        role = m.get("role", "unknown")
        content = m.get("content", "")[:500]  # Truncate
        parts.append(f"{role.upper()}: {content}")
    return "\n".join(parts)


# ─── Node definitions ────────────────────────────────────────────────────────

def analyze_input(state: AgentState) -> AgentState:
    """Analyze user message and determine if clarification is needed."""
    user_msg = state["user_message"]
    history = _format_history(state.get("messages", []))
    provider = state.get("llm_provider", "gemini")

    system = (
        "You are an intelligent research assistant. "
        "Analyze the user's message and determine: "
        "1. Is the message clear enough to act on? "
        "2. Does it need clarification before proceeding? "
        "Only ask for clarification if the request is genuinely ambiguous."
    )

    prompt = f"""Conversation history:
{history}

Current user message: {user_msg}

Analyze this message. Respond in JSON:
{{
  "is_clear": true/false,
  "needs_clarification": true/false,
  "clarification_question": "..." or null,
  "intent_summary": "brief description of what the user wants"
}}"""

    response = _llm_call(prompt, system, provider)

    try:
        # Extract JSON from response
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
        else:
            parsed = {"is_clear": True, "needs_clarification": False}
    except Exception:
        parsed = {"is_clear": True, "needs_clarification": False}

    state["clarification_needed"] = parsed.get("needs_clarification", False)
    state["clarification_question"] = parsed.get("clarification_question")
    return state


def clarify_if_needed(state: AgentState) -> AgentState:
    """Generate a clarification question and set final_answer to halt gracefully."""
    question = state.get("clarification_question") or "Could you please provide more details about your request?"
    state["final_answer"] = question
    state["citations"] = []
    state["current_plan"] = ["Awaiting clarification from user"]
    return state


def build_plan(state: AgentState) -> AgentState:
    """Create a step-by-step research plan."""
    user_msg = state["user_message"]
    history = _format_history(state.get("messages", []))
    active_skills = state.get("active_skills", [])
    provider = state.get("llm_provider", "gemini")

    skills_info = ""
    if active_skills:
        skill_names = [s.get("name", "unknown") for s in active_skills]
        skills_info = f"\nAvailable skills: {', '.join(skill_names)}"

    system = (
        "You are a meticulous research planner. "
        "Create concise, actionable research plans. "
        "Each step should be clear and achievable."
    )

    prompt = f"""Conversation history:
{history}

User request: {user_msg}{skills_info}

Create a step-by-step plan to answer this request.
Respond in JSON:
{{
  "plan": [
    "Step 1: ...",
    "Step 2: ...",
    ...
  ]
}}

Keep it to 3-6 steps. Be specific and actionable."""

    response = _llm_call(prompt, system, provider)

    try:
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            plan = parsed.get("plan", [])
        else:
            plan = [f"Research: {user_msg}", "Analyze findings", "Compose answer"]
    except Exception:
        plan = [f"Research: {user_msg}", "Analyze findings", "Compose answer"]

    if not plan:
        plan = [f"Research: {user_msg}", "Analyze findings", "Compose answer"]

    state["current_plan"] = plan
    state["plan_revision_count"] = 0
    return state


def retrieve_context(state: AgentState) -> AgentState:
    """Search Chroma for relevant chunks."""
    user_msg = state["user_message"]
    session_id = state["session_id"]
    plan = state.get("current_plan", [])

    # Build a comprehensive search query from user message + plan
    search_query = user_msg
    if plan:
        search_query += " " + " ".join(plan[:3])

    ks = KnowledgeStore()
    chunks = ks.search(session_id=session_id, query=search_query, top_k=8)

    state["retrieved_chunks"] = chunks
    return state


def choose_skills(state: AgentState) -> AgentState:
    """Select applicable skills for this request."""
    active_skills = state.get("active_skills", [])
    provider = state.get("llm_provider", "gemini")
    logger.info(f"choose_skills: {len(active_skills)} active skill(s): {[s.get('name') for s in active_skills]}")
    if not active_skills:
        state["selected_skills"] = []
        return state

    user_msg = state["user_message"]

    system = "You are a skill selector. Choose which skills are relevant for this task."
    skill_list = "\n".join(
        [f"- {s.get('name')}: {s.get('description', '')}" for s in active_skills]
    )

    prompt = f"""User request: {user_msg}

Available skills:
{skill_list}

Which skills are relevant? Respond in JSON:
{{"selected_skills": ["skill_name1", ...]}}

If none are relevant, return empty list."""

    response = _llm_call(prompt, system, provider)

    try:
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            selected = parsed.get("selected_skills", [])
        else:
            selected = []
    except Exception:
        selected = []

    logger.info(f"choose_skills: selected={selected}")
    state["selected_skills"] = selected
    return state


def decide_code_execution(state: AgentState) -> AgentState:
    """Decide if code generation and execution is needed."""
    from app.core.config import settings

    if not settings.enable_code_execution:
        state["code_execution_needed"] = False
        return state

    # If any skills were selected, always execute — skills ARE code
    if state.get("selected_skills"):
        state["code_execution_needed"] = True
        return state

    user_msg = state["user_message"]

    # Keywords suggesting code execution is needed
    code_keywords = [
        "calculate", "compute", "plot", "chart", "graph", "analyze data",
        "run", "execute", "script", "code", "python", "csv", "excel",
        "statistics", "regression", "sort", "filter", "transform",
    ]

    msg_lower = user_msg.lower()
    needs_code = any(kw in msg_lower for kw in code_keywords)

    state["code_execution_needed"] = needs_code
    return state


def _extract_code_block(skill_content: str) -> str:
    """Extract the first ```python ... ``` block from SKILL.md content."""
    import re
    match = re.search(r'```python\n(.*?)```', skill_content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def _adapt_skill_code(code_template: str, user_msg: str, context: str, skill_name: str, provider: str = "gemini") -> str:
    """Ask the LLM to adapt a skill code template with real content."""
    system = (
        "You are a Python code adapter. "
        "You receive a skill code template and must fill in the placeholder data "
        "with real content derived from the user request and retrieved context. "
        "Return ONLY the complete, runnable Python code. No explanations, no markdown fences."
    )

    prompt = f"""Skill: {skill_name}

User request: {user_msg}

Retrieved context (use this to populate slide content, data, etc.):
{context[:3000]}

Code template to adapt:
```python
{code_template}
```

Rules:
- Replace ALL placeholder/example content (like "Overview of the topic", "Finding 1", etc.) with real content derived from the user request and context above.
- Keep the structure, imports, and OUTPUT_PATH exactly as-is.
- Do NOT add new imports beyond what the template already uses.
- Return only the Python code, no markdown fences."""

    adapted = _llm_call(prompt, system, provider)

    # Strip markdown fences if LLM added them anyway
    import re
    adapted = re.sub(r'^```python\n?', '', adapted, flags=re.MULTILINE)
    adapted = re.sub(r'^```\n?', '', adapted, flags=re.MULTILINE)
    return adapted.strip()


def run_tools_or_code(state: AgentState) -> AgentState:
    """Execute skill templates or generate code for general tasks."""
    from app.core.config import settings

    if not settings.enable_code_execution:
        state["execution_outputs"] = []
        return state

    user_msg = state["user_message"]
    provider = state.get("llm_provider", "gemini")
    context_texts = [c["text"] for c in state.get("retrieved_chunks", [])]
    context = "\n\n".join(context_texts[:4]) if context_texts else "No context available."
    selected_skills = state.get("selected_skills", [])
    active_skills = state.get("active_skills", [])

    execution_outputs = []

    logger.info(f"run_tools_or_code: selected_skills={selected_skills}")

    # ── Skill-based execution ─────────────────────────────────────────────────
    if selected_skills:
        # Build a lookup from skill name → skill definition
        skill_map = {s["name"]: s for s in active_skills}

        for skill_name in selected_skills:
            skill = skill_map.get(skill_name)
            if not skill:
                logger.warning(f"Selected skill '{skill_name}' not found in active_skills")
                continue

            skill_content = skill.get("skill_content", "")
            code_template = _extract_code_block(skill_content)
            if not code_template:
                logger.warning(f"No Python code block found in SKILL.md for '{skill_name}'")
                continue

            # Adapt the template with real content
            code = _adapt_skill_code(code_template, user_msg, context, skill_name, provider)

            try:
                from app.execution.executor import execute_python
                result = execute_python(code, timeout=settings.max_code_exec_seconds)

                # Parse stdout for output_path (skills print JSON with output_path)
                output_file = None
                import json as _json
                try:
                    parsed_out = _json.loads(result.stdout.strip())
                    output_file = parsed_out.get("output_path")
                except Exception:
                    pass

                execution_outputs.append({
                    "skill_name": skill_name,
                    "code": code,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.exit_code,
                    "success": result.exit_code == 0,
                    "output_file": output_file,
                })
            except Exception as e:
                execution_outputs.append({
                    "skill_name": skill_name,
                    "code": code,
                    "stdout": "",
                    "stderr": str(e),
                    "exit_code": 1,
                    "success": False,
                    "output_file": None,
                })

    else:
        # ── General code generation (no skills selected) ──────────────────────
        system = (
            "You are a Python code generator. "
            "Write clean, safe Python code to answer the user's request. "
            "Use only standard library modules and pandas/numpy if needed. "
            "Print the result to stdout."
        )

        prompt = f"""User request: {user_msg}

Context from documents:
{context[:2000]}

Write Python code to address this request.
If data processing is needed, use the context above.
Only output the Python code, no explanations."""

        code = _llm_call(prompt, system, provider)

        import re
        code = re.sub(r'^```python\n?', '', code, flags=re.MULTILINE)
        code = re.sub(r'^```\n?', '', code, flags=re.MULTILINE)
        code = code.strip()

        try:
            from app.execution.executor import execute_python
            result = execute_python(code, timeout=settings.max_code_exec_seconds)
            execution_outputs.append({
                "skill_name": None,
                "code": code,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.exit_code,
                "success": result.exit_code == 0,
                "output_file": None,
            })
        except Exception as e:
            execution_outputs.append({
                "skill_name": None,
                "code": code,
                "stdout": "",
                "stderr": str(e),
                "exit_code": 1,
                "success": False,
                "output_file": None,
            })

    state["execution_outputs"] = execution_outputs
    return state


def revise_plan(state: AgentState) -> AgentState:
    """Revise the plan based on retrieved context."""
    plan = state.get("current_plan", [])
    chunks = state.get("retrieved_chunks", [])
    user_msg = state["user_message"]
    revision_count = state.get("plan_revision_count", 0)
    provider = state.get("llm_provider", "gemini")

    context_summary = ""
    if chunks:
        context_summary = "\n".join([c["text"][:200] for c in chunks[:3]])

    system = "You are a research planner. Revise the plan based on what was found."
    prompt = f"""Original request: {user_msg}

Current plan:
{chr(10).join(plan)}

Context found:
{context_summary}

Do we need to revise the plan? Respond in JSON:
{{
  "needs_revision": true/false,
  "revised_plan": ["Step 1: ...", ...]
}}"""

    response = _llm_call(prompt, system, provider)

    try:
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            if parsed.get("needs_revision") and parsed.get("revised_plan"):
                state["current_plan"] = parsed["revised_plan"]
    except Exception:
        pass

    state["plan_revision_count"] = revision_count + 1
    return state


def compose_answer(state: AgentState) -> AgentState:
    """Generate final answer with citations."""
    user_msg = state["user_message"]
    history = _format_history(state.get("messages", []))
    retrieved_chunks = state.get("retrieved_chunks", [])
    plan = state.get("current_plan", [])
    execution_outputs = state.get("execution_outputs", [])
    provider = state.get("llm_provider", "gemini")

    # Build context from retrieved chunks
    context_parts = []
    citations = []
    for i, chunk in enumerate(retrieved_chunks[:6]):
        text = chunk.get("text", "")
        meta = chunk.get("metadata", {})
        source_name = meta.get("source_name", f"Source {i+1}")
        source_id = meta.get("source_id", "")
        chunk_idx = meta.get("chunk_index", i)

        context_parts.append(f"[Source {i+1}: {source_name}]\n{text}")
        citations.append({
            "source_id": source_id,
            "source_name": source_name,
            "chunk_index": chunk_idx,
            "excerpt": text[:300],
        })

    context = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant documents found in the knowledge base."

    # Build execution summary — clearly describe what skills ran and what they produced
    exec_context = ""
    if execution_outputs:
        parts = []
        for out in execution_outputs:
            skill_name = out.get("skill_name")
            if out.get("success"):
                if out.get("output_file"):
                    parts.append(
                        f"✅ Skill '{skill_name}' executed successfully and produced a file: "
                        f"{out['output_file']}. This file has been saved and will be available "
                        f"as a downloadable artifact."
                    )
                elif out.get("stdout"):
                    parts.append(
                        f"✅ Skill '{skill_name}' executed successfully.\nOutput:\n{out['stdout'][:1000]}"
                    )
                else:
                    parts.append(f"✅ Skill '{skill_name}' executed successfully.")
            else:
                parts.append(
                    f"❌ Skill '{skill_name}' failed: {out.get('stderr', 'unknown error')[:300]}"
                )
        exec_context = "\n\nSkill execution results:\n" + "\n\n".join(parts)

    system = (
        "You are a knowledgeable research assistant with skill execution capabilities. "
        "When a skill has successfully produced a file (like a PPTX, PDF, or CSV), "
        "tell the user it has been generated and will appear as a downloadable artifact in the interface. "
        "Provide a summary of what was produced. "
        "Always cite your sources. Use markdown formatting for readability."
    )

    prompt = f"""Conversation history:
{history}

User question: {user_msg}

Research plan completed:
{chr(10).join(f'- {step}' for step in plan)}

Retrieved context:
{context}{exec_context}

Please provide a comprehensive, well-structured answer to the user's question.
If a file was generated by a skill, confirm this clearly and tell the user to look for the download in the artifacts panel.
Reference sources as [Source N] where applicable.
Use markdown formatting (headers, bullet points, etc.) for clarity."""

    answer = _llm_call(prompt, system, provider)

    state["final_answer"] = answer
    state["citations"] = citations
    return state


def persist_memory(state: AgentState) -> AgentState:
    """Final node - state persistence is handled externally by agent_service."""
    return state


# ─── Routing functions ────────────────────────────────────────────────────────

def route_after_analyze(state: AgentState) -> Literal["clarify_if_needed", "build_plan"]:
    if state.get("clarification_needed"):
        return "clarify_if_needed"
    return "build_plan"


def route_after_decide_code(state: AgentState) -> Literal["run_tools_or_code", "compose_answer"]:
    if state.get("code_execution_needed"):
        return "run_tools_or_code"
    return "compose_answer"


def route_after_tools(state: AgentState) -> Literal["revise_plan", "compose_answer"]:
    revision_count = state.get("plan_revision_count", 0)
    if revision_count < 1:
        return "revise_plan"
    return "compose_answer"


def route_after_revise(state: AgentState) -> Literal["retrieve_context", "compose_answer"]:
    # Only re-retrieve if plan changed significantly (limit to 1 revision)
    revision_count = state.get("plan_revision_count", 0)
    if revision_count < 2:
        return "retrieve_context"
    return "compose_answer"


# ─── Build graph ─────────────────────────────────────────────────────────────

def build_agent_graph():
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("analyze_input", analyze_input)
    graph.add_node("clarify_if_needed", clarify_if_needed)
    graph.add_node("build_plan", build_plan)
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("choose_skills", choose_skills)
    graph.add_node("decide_code_execution", decide_code_execution)
    graph.add_node("run_tools_or_code", run_tools_or_code)
    graph.add_node("revise_plan", revise_plan)
    graph.add_node("compose_answer", compose_answer)
    graph.add_node("persist_memory", persist_memory)

    # Set entry point
    graph.set_entry_point("analyze_input")

    # Add edges
    graph.add_conditional_edges(
        "analyze_input",
        route_after_analyze,
        {
            "clarify_if_needed": "clarify_if_needed",
            "build_plan": "build_plan",
        },
    )
    graph.add_edge("clarify_if_needed", "persist_memory")
    graph.add_edge("build_plan", "choose_skills")
    graph.add_edge("choose_skills", "retrieve_context")
    graph.add_edge("retrieve_context", "decide_code_execution")
    graph.add_conditional_edges(
        "decide_code_execution",
        route_after_decide_code,
        {
            "run_tools_or_code": "run_tools_or_code",
            "compose_answer": "compose_answer",
        },
    )
    graph.add_conditional_edges(
        "run_tools_or_code",
        route_after_tools,
        {
            "revise_plan": "revise_plan",
            "compose_answer": "compose_answer",
        },
    )
    graph.add_conditional_edges(
        "revise_plan",
        route_after_revise,
        {
            "retrieve_context": "retrieve_context",
            "compose_answer": "compose_answer",
        },
    )
    graph.add_edge("compose_answer", "persist_memory")
    graph.add_edge("persist_memory", END)

    return graph.compile(checkpointer=memory_saver)


# Singleton compiled graph
_agent_graph = None


def get_agent_graph():
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_agent_graph()
    return _agent_graph
