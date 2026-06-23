"""Supervisor Agent — LLM-based task planner and dispatcher for the multi-agent team.

The supervisor operates in two phases:

  Phase 1 (Planning):
      When ``pending_tasks`` is empty, the supervisor uses an LLM to understand the
      user's latest message, decompose it into a list of atomic tasks, and assign
      each task to the most suitable agent.

  Phase 2 (Dispatch):
      After each agent completes, the supervisor pops the finished task, records it
      as done, and routes the next pending task to the appropriate agent.  When all
      tasks are finished, the supervisor invokes the LLM to synthesise all partial
      results into a single, cohesive final response.

  Safety:
      A maximum iteration count (``MAX_ITER = 15``) prevents infinite loops.
"""

import json
import logging
import os
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, HumanMessage
from langchain_ollama import ChatOllama
from state import TeamState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — read from environment with sensible defaults
# ---------------------------------------------------------------------------
OLLAMA_HOST: str = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
SUPERVISOR_MODEL: str = os.environ.get("SUPERVISOR_AGENT_MODEL", "qwen3.5:4b")

# ---------------------------------------------------------------------------
# Agent registry — used by the planner prompt to inform the LLM of capabilities
# ---------------------------------------------------------------------------
AGENTS: Dict[str, Dict[str, Any]] = {
    "utility": {
        "description": "天气查询、时间查询",
        "task_types": ["weather", "time"],
    },
    "comm": {
        "description": "发送邮件、发送钉钉消息",
        "task_types": ["email", "dingtalk"],
    },
    "finance": {
        "description": "股票价格查询、行情分析",
        "task_types": ["stock"],
    },
    "knowledge": {
        "description": "《智能应用系统设计》课程问答",
        "task_types": ["course_qa"],
    },
    "resume": {
        "description": "简历解析、技能匹配、候选人评估",
        "task_types": ["resume"],
    },
    "chat": {
        "description": "普通对话、闲聊",
        "task_types": ["chat"],
    },
}

_MAX_ITER: int = 15

# ---------------------------------------------------------------------------
# Prompt templates (Chinese, matching the project's user base)
# ---------------------------------------------------------------------------

_PLAN_PROMPT = """你是一个智能任务规划器。分析用户输入，拆解为需要执行的任务列表。

可用的 agent 和它们能处理的任务类型：
- utility: weather(天气查询，参数city), time(时间查询，参数format可为full/date/time)
- comm: email(发送邮件), dingtalk(发送钉钉)
- finance: stock(股票查询，参数ticker)
- knowledge: course_qa(课程问答，参数question)
- resume: resume(简历评估，参数resume_text, job_requirements可选)
- chat: chat(普通对话)

规则：
1. 每个任务只做一件事
2. 同一个 agent 可以多次调用（如同时查天气和时间）
3. 如果用户只是闲聊，返回单个 chat 任务
4. 如果用户的消息不完整，返回单个 chat 任务让 agent 追问

输出 JSON 数组格式（只输出 JSON，不要其他内容）：
[
  {{"agent": "utility", "task_type": "weather", "city": "广州"}},
  {{"agent": "utility", "task_type": "time", "format": "full"}}
]

用户输入：{user_msg}"""

_SYNTHESIS_PROMPT = """根据以下任务执行结果，生成一个简洁、友好的中文回复给用户：

{results}

用户原始问题：{user_msg}"""


# ===================================================================
#  Public node — called by the LangGraph runtime
# ===================================================================


def supervisor_node(state: TeamState) -> dict:
    """Supervisor graph node — plans and dispatches tasks.

    Args:
        state: The current ``TeamState`` (messages, pending_tasks,
               completed_tasks, iteration_count, etc.).

    Returns:
        A dict of fields to merge into ``TeamState`` via the reducer.
    """
    pending: List[Dict[str, Any]] = state.get("pending_tasks", [])
    completed: List[Dict[str, Any]] = state.get("completed_tasks", [])
    iteration: int = state.get("iteration_count", 0)

    # ------------------------------------------------------------------
    # Safety: hard cap on total iterations to prevent infinite loops.
    # ------------------------------------------------------------------
    if iteration >= _MAX_ITER:
        logger.warning("Max iterations (%d) reached — finishing", _MAX_ITER)
        return {
            "next": "FINISH",
            "messages": [AIMessage(content="任务处理超时，请重新提问。")],
        }

    # ──────────────────────────────────────────────────────────────────
    # Phase 1: PLANNING
    # ──────────────────────────────────────────────────────────────────
    if not pending:
        tasks = _plan_tasks(state)
        if not tasks:
            logger.info("No tasks planned — falling back to chat agent")
            return {"next": "chat", "iteration_count": iteration + 1}

        # Mark the first task as in_progress and set routing target
        tasks[0]["status"] = "in_progress"
        logger.info(
            "Phase 1 — Planned %d task(s): %s",
            len(tasks),
            [{"agent": t["agent"], "task_type": t["task_type"]} for t in tasks],
        )
        return {
            "pending_tasks": tasks,
            "completed_tasks": [],
            "next": tasks[0]["agent"],
            "iteration_count": iteration + 1,
        }

    # ──────────────────────────────────────────────────────────────────
    # Phase 2: DISPATCH
    # ──────────────────────────────────────────────────────────────────

    # Pop the completed task from the front of the queue
    current = pending[0].copy()
    current["status"] = "done"
    remaining = pending[1:]
    completed.append(current)

    logger.info(
        "Phase 2 — Task done: [%s] %s — %d remaining",
        current.get("agent"),
        current.get("task_type"),
        len(remaining),
    )

    if remaining:
        # More tasks remain — mark the next one in_progress and route to it
        remaining[0]["status"] = "in_progress"
        return {
            "pending_tasks": remaining,
            "completed_tasks": completed,
            "next": remaining[0]["agent"],
            "iteration_count": iteration + 1,
        }

    # All tasks are done — synthesise a single final response
    logger.info(
        "Phase 2 — All %d task(s) completed; synthesising final response",
        len(completed),
    )
    synthesis = _synthesize(state, completed)
    return {
        "pending_tasks": [],
        "completed_tasks": completed,
        "next": "FINISH",
        "messages": [AIMessage(content=synthesis)],
        "iteration_count": iteration + 1,
    }


# ===================================================================
#  Internal helpers
# ===================================================================


def _plan_tasks(state: TeamState) -> List[Dict[str, Any]]:
    """Use the supervisor LLM to decompose the user's last message into tasks.

    Returns:
        A list of task dicts (each with at least ``agent`` and ``task_type``
        keys, plus any extracted parameters).  Returns a single ``chat`` task
        when parsing fails or the message is empty.
    """
    # Extract the last human message
    last_user_msg: str = ""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage):
            last_user_msg = msg.content
            break

    if not last_user_msg:
        logger.warning("No user message found in state — defaulting to chat task")
        return [{"agent": "chat", "task_type": "chat"}]

    # ------------------------------------------------------------------
    # Create a deterministic, cold LLM for planning
    # ------------------------------------------------------------------
    try:
        llm = ChatOllama(
            model=SUPERVISOR_MODEL,
            base_url=OLLAMA_HOST,
            temperature=0,
        )
    except Exception as e:
        logger.error("Failed to initialise planner ChatOllama: %s", e)
        return [{"agent": "chat", "task_type": "chat"}]

    prompt = _PLAN_PROMPT.format(user_msg=last_user_msg)

    # ------------------------------------------------------------------
    # Invoke the LLM
    # ------------------------------------------------------------------
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = (
            response.content.strip()
            if hasattr(response, "content")
            else str(response).strip()
        )
    except Exception as e:
        logger.error("Planner LLM invocation failed: %s", e)
        return [{"agent": "chat", "task_type": "chat"}]

    # ------------------------------------------------------------------
    # Strip optional markdown code fences
    # ------------------------------------------------------------------
    raw = raw.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    # ------------------------------------------------------------------
    # Parse JSON
    # ------------------------------------------------------------------
    try:
        tasks: List[Dict[str, Any]] = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning(
            "Failed to parse planner JSON output: %s\nRaw (first 200 chars): %s",
            e,
            raw[:200],
        )
        return [{"agent": "chat", "task_type": "chat"}]

    if not isinstance(tasks, list):
        logger.warning("Planner output is not a JSON list: %s", tasks)
        return [{"agent": "chat", "task_type": "chat"}]

    # ------------------------------------------------------------------
    # Validate each entry
    # ------------------------------------------------------------------
    validated: List[Dict[str, Any]] = []
    for i, task in enumerate(tasks):
        if not isinstance(task, dict):
            logger.warning("Task entry %d is not a dict — skipping", i)
            continue
        agent = task.get("agent")
        task_type = task.get("task_type")
        if not agent or not task_type:
            logger.warning(
                "Task entry %d missing 'agent' or 'task_type' — skipping: %s",
                i,
                task,
            )
            continue
        # Keep all extra keys (parameters like city, format, ticker, etc.)
        extra = {
            k: v for k, v in task.items() if k not in ("agent", "task_type", "status")
        }
        validated.append({"agent": agent, "task_type": task_type, **extra})

    if not validated:
        logger.warning("No valid tasks after validation — defaulting to chat")
        return [{"agent": "chat", "task_type": "chat"}]

    logger.info("Planner produced %d valid task(s): %s", len(validated), validated)
    return validated


def _synthesize(state: TeamState, completed_tasks: List[Dict[str, Any]]) -> str:
    """Use the supervisor LLM to generate a natural-language final response.

    Args:
        state: The current ``TeamState`` (contains all agent-result messages).
        completed_tasks: The list of finished task dicts (used for logging).

    Returns:
        A final response string summarising all agent results.
    """
    # Extract the last user message for context
    last_user_msg: str = ""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage):
            last_user_msg = msg.content
            break

    # Collect AIMessages that were appended by agent nodes.
    # These represent the actual results from each tool/agent call.
    agent_results: List[str] = []
    for msg in state.get("messages", []):
        if isinstance(msg, AIMessage):
            agent_results.append(msg.content)

    # If there are no agent results (edge case), return a simple message.
    if not agent_results:
        logger.warning("No agent result messages found in state")
        return "所有任务已完成。"

    # Format results for the prompt, truncating each to avoid context overflow
    results_text = "\n\n".join(
        f"任务 {i + 1}: {r[:500]}" for i, r in enumerate(agent_results)
    )

    logger.info(
        "Synthesising %d agent result(s) for: %s",
        len(agent_results),
        last_user_msg[:60],
    )

    # ------------------------------------------------------------------
    # Create LLM instance
    # ------------------------------------------------------------------
    try:
        llm = ChatOllama(
            model=SUPERVISOR_MODEL,
            base_url=OLLAMA_HOST,
            temperature=0,
        )
    except Exception as e:
        logger.error("Failed to initialise synthesis ChatOllama: %s", e)
        return results_text if results_text else "所有任务已完成。"

    prompt = _SYNTHESIS_PROMPT.format(
        results=results_text,
        user_msg=last_user_msg or "",
    )

    # ------------------------------------------------------------------
    # Invoke LLM
    # ------------------------------------------------------------------
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        synthesis = (
            response.content.strip()
            if hasattr(response, "content")
            else str(response).strip()
        )
        logger.info("Synthesis complete — %d character(s)", len(synthesis))
        return synthesis
    except Exception as e:
        logger.error("Synthesis LLM invocation failed: %s", e)
        return results_text if results_text else "所有任务已完成。"
