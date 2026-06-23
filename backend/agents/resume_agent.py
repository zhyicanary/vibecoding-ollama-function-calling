import json
import logging
import os
import re

from langchain_core.messages import AIMessage, HumanMessage
from langchain_ollama import ChatOllama
from state import TeamState

logger = logging.getLogger(__name__)


def resume_agent_node(state: TeamState) -> dict:
    """Resume screening pipeline — parse, match, evaluate, report."""
    pending = state.get("pending_tasks", [])
    if not pending:
        return {"messages": [AIMessage(content="没有待执行的简历评估任务。")]}

    task = pending[0]
    task_type = task.get("task_type", "unknown")

    if task_type != "resume":
        return {"messages": [AIMessage(content=f"未知任务类型: {task_type}")]}

    resume_text = task.get("resume_text", "")
    job_requirements = task.get("job_requirements", "")

    if not resume_text:
        return {"messages": [AIMessage(content="请提供简历内容。")]}

    ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    agent_model = os.environ.get("RESUME_AGENT_MODEL", "qwen3.5:4b")
    llm = ChatOllama(model=agent_model, base_url=ollama_host, temperature=0.2)

    try:
        # Step 1: Parse resume
        parse_prompt = f"""你是一位专业HR。从以下简历内容中提取结构化信息。如果包含职位要求也提取出来。
输出JSON：{{"candidate_info": {{"name":"","education":"","school":"","major":"","years_of_experience":"","current_position":""}}, "skills":[], "work_experience":[], "projects":[], "certifications":[], "languages":[], "job_requirements":""}}
只输出JSON，不要其他内容。
简历内容：{resume_text[:3000]}
职位要求：{job_requirements[:1000] if job_requirements else "未提供"}"""

        raw = llm.invoke([HumanMessage(content=parse_prompt)]).content.strip()
        raw = raw.strip("```json").strip("```").strip()
        parsed = json.loads(_extract_json(raw))

        if not job_requirements:
            parsed_jr = parsed.get("job_requirements", "")
            if not parsed_jr:
                info = parsed.get("candidate_info", {})
                skills = ", ".join(parsed.get("skills", ["未识别"]))
                summary = f"""## 简历解析结果

**基本信息：** 姓名：{info.get("name", "未知")} | 学历：{info.get("education", "未知")} | 学校：{info.get("school", "未知")} | 专业：{info.get("major", "未知")}
**技能：** {skills}
**工作经历：** {len(parsed.get("work_experience", []))}段

如需评估匹配度，请提供职位要求。"""
                return {"messages": [AIMessage(content=summary)]}
            job_requirements = parsed_jr

        # Step 2: Match
        match_prompt = f"""比对候选人和职位要求，输出匹配分析JSON：
{{"overall_match_score": 85, "skill_match": {{"matched":[],"missing":[],"score":80}}, "experience_match": {{"analysis":"","score":80}}, "education_match": {{"analysis":"","score":80}}, "strengths":[], "weaknesses":[], "recommendation":""}}
候选人：{json.dumps(parsed, ensure_ascii=False)[:2000]}
职位要求：{job_requirements[:1000]}
只输出JSON。"""

        raw2 = llm.invoke([HumanMessage(content=match_prompt)]).content.strip()
        raw2 = raw2.strip("```json").strip("```").strip()
        match_data = json.loads(_extract_json(raw2))

        # Step 3: Generate report
        report_prompt = f"""生成专业的简历评估报告：
候选人：{json.dumps(parsed.get("candidate_info", {}), ensure_ascii=False)}
匹配分析：{json.dumps(match_data, ensure_ascii=False)[:2000]}
包含：候选人概况、技能/经验/学历匹配度、优势不足、综合评分建议。用中文，格式清晰。"""

        report = llm.invoke([HumanMessage(content=report_prompt)]).content

        final = f"""## 简历评估报告

{report}

---
*AI生成，仅供参考。最终决策请结合面试。*"""

        return {"messages": [AIMessage(content=final)]}

    except Exception as e:
        logger.error(f"ResumeAgent error: {e}")
        return {"messages": [AIMessage(content=f"简历评估失败：{e}")]}


def _extract_json(text: str) -> str:
    """Extract the first JSON object from text."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group() if match else text
