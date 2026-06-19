"""本地工作流运行器 — script-generate"""
import json
import os
import httpx
from jinja2 import Template

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")
TEMPLATE_DIR = os.path.join(PROMPT_DIR, "templates")


def _read_prompt(template: str, filename: str) -> str:
    path = os.path.join(TEMPLATE_DIR, template, filename)
    if not os.path.exists(path):
        # fallback to script_generate dir
        path = os.path.join(PROMPT_DIR, "script_generate", filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


async def run_script_generate(
    api_key: str,
    base_url: str,
    model: str,
    params: dict,
    template: str = "default",
) -> dict:
    """本地执行剧本生成"""
    product_info = params.get("product_info", {})
    style = params.get("style", "电商带货")
    duration = params.get("duration", 30)
    materials = params.get("materials", []) or params.get("selected_materials", [])

    # 读取 prompt 模板
    system_prompt = _read_prompt(template, "system.md")
    # 追加通用规则（独立文件）
    RULES_PATH = os.path.join(PROMPT_DIR, "rules.md")
    if os.path.exists(RULES_PATH):
        with open(RULES_PATH, "r", encoding="utf-8") as f:
            system_prompt += "\n\n" + f.read()
    # 追加输出格式（独立文件，只读）
    OUTPUT_FORMAT_PATH = os.path.join(PROMPT_DIR, "output_format.md")
    if os.path.exists(OUTPUT_FORMAT_PATH):
        with open(OUTPUT_FORMAT_PATH, "r", encoding="utf-8") as f:
            system_prompt += "\n\n" + f.read()
    user_template = _read_prompt(template, "user.md.j2")

    # 渲染用户 prompt
    up_tpl = Template(user_template)
    user_prompt = up_tpl.render(
        product_info={
            "name": product_info.get("name", ""),
            "description": product_info.get("description", ""),
            "selling_points": product_info.get("selling_points", []),
        },
        style=style,
        duration=duration,
        materials=[
            {
                "material_id": m.get("material_id", i + 1),
                "text_content": m.get("text_content", "") or m.get("description", ""),
                "tags": m.get("tags", []),
            }
            for i, m in enumerate(materials)
        ],
    )

    # 调 LLM
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.8,
        "max_tokens": 8192,
    }

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers=headers, json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"]

    # 解析 JSON
    json_start = content.find("{")
    json_end = content.rfind("}") + 1
    if json_start == -1 or json_end == 0:
        raise ValueError("LLM响应中未找到有效的JSON格式剧本")
    script = json.loads(content[json_start:json_end])

    # 修正：每条 scene 最后一句台词的 end_sec 不能超过 duration-1
    for s in script.get("scenes", []):
        dur = s.get("duration", 5)
        lines = s.get("lines", [])
        if lines:
            last = lines[-1]
            max_end = dur - 1
            if last.get("end_sec", 0) > max_end:
                last["end_sec"] = max_end

    return {"script": script}
