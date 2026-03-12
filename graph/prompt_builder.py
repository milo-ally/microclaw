"""Build system prompt for agent."""

from pathlib import Path

from microclaw.config import get_platform

MAX_COMPONENT_LENGTH = 20000

def _read_component(path: Path) -> str: 
    """Read component from file"""
    if not path.exists():
        return ""
    content = path.read_text(encoding="utf-8")
    if len(content) > MAX_COMPONENT_LENGTH:
        content = content[:MAX_COMPONENT_LENGTH] + "\n\n[...truncated]"
    return content 

RAG_GUIDANCE = """注意: 长期记忆(MEMORY.md)已切换为RAG检索模式。
系统会根据用户的问题自动检索相关记忆片段并注入上下文。
如果检索到了相关记忆, 它们会以 "[记忆检索结果]" 标记呈现在上下文中。
"""



def build_system_prompt(base_dir: Path | str, rag_mode: bool = False) -> str:
    base = Path(base_dir) if isinstance(base_dir, str) else base_dir
    components = [
        ("BOOT STRAP", base / "workplace" / "BOOTSTRAP.md"),
        ("Skills Snapshot", base / "skills" / "SKILL_SNAPSHOT.md"),
        ("Soul", base / "workplace" / "SOUL.md"),
        ("Identity", base / "workplace" / "IDENTITY.md"),
        ("User Profile", base / "workplace" / "USER.md"),
        ("Agent Guide", base / "workplace" / "AGENTS.md")
    ]
    if not rag_mode:
        components.append(("long term memory", base / "memory" / "MEMORY.md"))

    parts: list[str] = []
    for label, path in components:
        content = _read_component(path)
        if content:
            parts.append(f"<!-- {label} -->\n{content}")
    if rag_mode:
        parts.append(f"<!-- RAG MODE -->\n{RAG_GUIDANCE}")
    # Read platform lazily so prompt builder does not depend on config being valid at import-time.
    parts.append(f"<!-- USER PLATFORM -->\n{get_platform()}")

    return "\n\n".join(parts)


if __name__ == "__main__": 
    # ========== 测试配置 ==========
    # 1. 指定测试目录（请替换为你实际的目录路径）
    TEST_BASE_DIR = Path(__file__).resolve().parent / "test_prompt_dir"
    # 2. 创建测试目录和空文件（避免文件不存在导致无内容）
    TEST_BASE_DIR.mkdir(exist_ok=True)
    (TEST_BASE_DIR / "skills").mkdir(exist_ok=True)
    (TEST_BASE_DIR / "workplace").mkdir(exist_ok=True)
    (TEST_BASE_DIR / "memory").mkdir(exist_ok=True)
    
    # 写入测试内容到各文件
    test_files = {
        "skills/SKILL_SNAPSHOT.md": "精通Python编程、LLM应用开发、工具调用",
        "workplace/SOUL.md": "核心价值观：用户至上、专业严谨、持续学习",
        "workplace/IDENTITY.md": "角色：AI助手，定位：解决编程问题，风格：通俗易懂",
        "workplace/USER.md": "用户：milo，场景：AI Agent开发，需求：构建系统提示词",
        "workplace/AGENTS.md": "Agent规则：1. 优先使用工具获取准确信息 2. 输出结构化内容",
        "memory/MEMORY.md": "长期记忆：用户曾询问Tavily API Key申请方法，已解决TypeError错误"
    }
    for rel_path, content in test_files.items():
        file_path = TEST_BASE_DIR / rel_path
        file_path.write_text(content, encoding="utf-8")

    # ========== 执行测试 ==========
    print("="*80)
    print("测试1：非RAG模式（包含MEMORY.md）")
    print("="*80)
    prompt_non_rag = build_system_prompt(TEST_BASE_DIR, rag_mode=False)
    print(f"【提示词长度】: {len(prompt_non_rag)} 字符")
    print(f"【提示词内容】:\n{prompt_non_rag}")

    print("\n" + "="*80)
    print("测试2：RAG模式（不包含MEMORY.md，增加RAG指引）")
    print("="*80)
    prompt_rag = build_system_prompt(TEST_BASE_DIR, rag_mode=True)
    print(f"【提示词长度】: {len(prompt_rag)} 字符")
    print(f"【提示词内容】:\n{prompt_rag}")

    # ========== 验证关键标记 ==========
    print("\n" + "="*80)
    print("关键标记验证")
    print("="*80)
    check_items = [
        ("<!-- Skills Snapshot -->", "技能快照", prompt_non_rag),
        ("<!-- RAG MODE -->", "RAG指引", prompt_rag),
        ("<!-- USER PLATFORM -->", "用户平台", prompt_non_rag),
        ("<!-- long term memory -->", "长期记忆", prompt_non_rag),
    ]
    for marker, desc, prompt in check_items:
        if marker in prompt:
            print(f"✅ {desc} 已正确注入")
        else:
            print(f"❌ {desc} 未找到")
