import asyncio
from sched import Event
import sys
import uuid
import traceback
from pathlib import Path
from typing import Optional
from enum import Enum
import time
import os
import pyfiglet
from termcolor import colored
from pydantic import BaseModel
import shutil

# 统一导入，避免局部作用域覆盖问题
from config import get_base_dir, get_llm_config, get_rag_mode
from graph.agent import agent_manager
from graph.session_manager import session_manager
from tools.skills_scanner import scan_skills

DEBUGMODE = True

class PrintColor:
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    PURPLE = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BOLD = "\033[1m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    BG_DARK = "\033[48;5;234m"
    BG_DARKER = "\033[48;5;233m"
    BG_PANEL = "\033[48;5;235m"

def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

def terminal_width():
    return shutil.get_terminal_size().columns

def bar(color=PrintColor.CYAN):
    w = terminal_width()
    print(f"{color}{'─' * w}{PrintColor.RESET}")

def panel_title(text):
    print(f"\n{PrintColor.BOLD}{PrintColor.CYAN}▶ {text}{PrintColor.RESET}")

# ========== 加载动画（OpenClaw 风格） ==========
def print_loading(text, duration=1.0):
    chars = ["⡿", "⣟", "⣯", "⣷", "⣾", "⣽", "⣻", "⢿"]
    start = time.time()
    i = 0
    while time.time() - start < duration:
        c = chars[i % len(chars)]
        sys.stdout.write(f"\r{PrintColor.CYAN}{PrintColor.BOLD}[{c}] {text}{PrintColor.RESET}")
        sys.stdout.flush()
        time.sleep(0.07)
        i += 1
    sys.stdout.write(f"\r{PrintColor.GREEN}{PrintColor.BOLD}[✓] {text}{PrintColor.RESET}\n")

# ========== 新增：轻量级异步加载动画（无阻塞） ==========
async def async_loading_indicator(stop_event: asyncio.Event, prefix="AI is thinking"):
    """异步加载指示器，通过Event控制停止，无阻塞"""
    chars = ["⡿", "⣟", "⣯", "⣷", "⣾", "⣽", "⣻", "⢿"]
    i = 0
    while not stop_event.is_set():
        c = chars[i % len(chars)]
        # 写入加载动画（覆盖当前行）
        sys.stdout.write(f"\r{PrintColor.BLUE}{PrintColor.BOLD}AUTOX > {PrintColor.RESET}{PrintColor.CYAN}{PrintColor.BOLD}[{c}] {prefix}{PrintColor.RESET}")
        sys.stdout.flush()
        try:
            # 短睡眠，允许事件被中断
            await asyncio.sleep(0.08)
        except asyncio.CancelledError:
            break
        i += 1
    # 清除加载动画行
    sys.stdout.write("\r" + " " * (terminal_width() - 1) + "\r")
    sys.stdout.write(f"{PrintColor.BLUE}{PrintColor.BOLD}AUTOX > {PrintColor.RESET}")
    sys.stdout.flush()

class EventType(Enum):
    REASONING_TOKEN_EVENT = "reasoning_token"
    TOKEN_EVENT = "token"
    TOOL_CALLING_EVENT = "tool_calling"
    AI_MESSAGE = "ai_message"
    TOOLCALL_MESSAGE = "toolcall_message"
    TOOL_EXECUTE_EVENT = "tool_execute"
    TOOL_RESPONSE_MESSAGE = "tool_response"
    TOOL_EXECUTE_DONE_EVENT = "tool_execute_done"
    RETRIEVAL_EVENT = "retrieval"
    ALL_DONE_EVENT = "all_done"
    DEBUG = "debug"

async def event_generator(
    base_dir: Path,
    session_id: str,
    enable_thinking: bool,
    message: str,
    image_url: Optional[str] = None
):
    THINK_WRAPPER_START = "\n\n"
    THINK_WRAPPER_END = "\n\n"
    has_output_start_tag = False

    try:
        agent_manager.initialize(base_dir=base_dir)
        scan_skills(base_dir=base_dir)
        history = session_manager.load_session_for_agent(session_id)

        async for event in agent_manager.astream(
            message=message,
            history=history,
            image_url=image_url
        ):
            try:
                if event["type"] == EventType.REASONING_TOKEN_EVENT.value:
                    if enable_thinking:
                        reasoning_content = event["content"]
                        if not has_output_start_tag:
                            yield {
                                "type": EventType.REASONING_TOKEN_EVENT.value,
                                "content": THINK_WRAPPER_START
                            }
                            has_output_start_tag = True
                        yield {
                            "type": EventType.REASONING_TOKEN_EVENT.value,
                            "content": reasoning_content
                        }

                elif event["type"] == EventType.TOKEN_EVENT.value:
                    if enable_thinking and has_output_start_tag:
                        yield {
                            "type": EventType.REASONING_TOKEN_EVENT.value,
                            "content": THINK_WRAPPER_END
                        }
                        has_output_start_tag = False
                    yield {
                        "type": EventType.TOKEN_EVENT.value,
                        "content": event["content"]
                    }

                elif event["type"] == EventType.TOOL_CALLING_EVENT.value:
                    yield {
                        "type": EventType.TOOL_CALLING_EVENT.value,
                        "content": event["content"]
                    }

                elif event["type"] == EventType.TOOL_EXECUTE_EVENT.value:
                    yield {
                        "type": EventType.TOOL_EXECUTE_EVENT.value,
                        "tool": event["tool"],
                        "input": event["input"]
                    }

                elif event["type"] == EventType.TOOL_RESPONSE_MESSAGE.value:
                    yield {
                        "type": EventType.TOOL_RESPONSE_MESSAGE.value,
                        "output": event["output"]
                    }

                elif event["type"] == EventType.TOOL_EXECUTE_DONE_EVENT.value:
                    yield {
                        "type": EventType.TOOL_EXECUTE_DONE_EVENT.value
                    }

                elif event["type"] == EventType.RETRIEVAL_EVENT.value:
                    yield {
                        "type": EventType.RETRIEVAL_EVENT.value,
                        "results": event["results"]
                    }

                elif event["type"] == EventType.ALL_DONE_EVENT.value:
                    yield {
                        "type": EventType.ALL_DONE_EVENT.value,
                        "input_content": event["input_content"],
                        "reasoning_content": event["reasoning_content"],
                        "content": event["content"],
                        "tool_call_content": event["tool_call_content"],
                        "tool_response_content": event["tool_response_content"],
                        "retrieval_content": event["retrieval_content"],
                    }

                elif event["type"] == EventType.AI_MESSAGE.value:
                    yield {
                        "type": EventType.AI_MESSAGE.value,
                        "content": event["content"]
                    }

                elif event["type"] == EventType.TOOLCALL_MESSAGE.value:
                    yield {
                        "type": EventType.TOOLCALL_MESSAGE.value,
                        "content": event["content"]
                    }

                else:
                    print(f"\n{PrintColor.RED}❌ Unknown event: {event['type']}{PrintColor.RESET}")

            except Exception as e:
                print(f"\n{PrintColor.RED}[Event Error] {e}{PrintColor.RESET}")
                traceback.print_exc()
                raise

    except Exception as e:
        print(f"\n{PrintColor.RED}[Generator Error] {e}{PrintColor.RESET}")
        traceback.print_exc()
        raise

# ========== LOGO ==========
def print_logo():
    clear_terminal()
    art = pyfiglet.figlet_format("AUTOX", font="slant")
    print(colored(art, "cyan", attrs=["bold"]))
    print(f"{PrintColor.DIM}Automation AI Agent • TUI{PrintColor.RESET}\n")

# ========== Session ID ==========
def get_session_id():
    panel_title("Session ID")
    print(f"{PrintColor.WHITE}• Enter to generate new session")
    print(f"{PrintColor.WHITE}• Input ID to load history{PrintColor.RESET}")
    while True:
        inp = input(f"\n{PrintColor.YELLOW}Session ID: {PrintColor.RESET}").strip()
        if not inp:
            sid = f"session_{uuid.uuid4().hex[:8]}"
            print(f"{PrintColor.GREEN}✓ New session: {sid}{PrintColor.RESET}")
            return sid
        if 3 <= len(inp) <= 32:
            print(f"{PrintColor.GREEN}✓ Using session: {inp}{PrintColor.RESET}")
            return inp
        print(f"{PrintColor.RED}✗ Invalid format (3-32 letters/numbers/_-){PrintColor.RESET}")

# ========== MAIN ==========
async def main():
    try:
        print_logo()

        # 初始化加载
        print_loading("Loading base config", 0.7)
        base_dir = Path(get_base_dir())

        print_loading("Loading LLM config", 0.7)
        llm_config = get_llm_config()

        print_loading("Loading RAG mode", 0.7)
        rag_mode = get_rag_mode()

        session_manager.initialize(base_dir)

        # Session
        session_id = get_session_id()
        bar()

        # 系统信息面板
        panel_title("System Info")
        model = llm_config.get("info", {}).get("model", "unknown")
        think = llm_config.get("info", {}).get("enable_thinking", False)
        vision = llm_config.get("info", {}).get("is_vision_model", False)

        print(f"{PrintColor.CYAN}• Base Dir: {PrintColor.WHITE}{base_dir}{PrintColor.RESET}")
        print(f"{PrintColor.CYAN}• LLM:      {PrintColor.WHITE}{model}{PrintColor.RESET}")
        print(f"{PrintColor.CYAN}• RAG:      {PrintColor.WHITE}{'ON' if rag_mode else 'OFF'}{PrintColor.RESET}")
        print(f"{PrintColor.CYAN}• Think:    {PrintColor.WHITE}{'ON' if think else 'OFF'}{PrintColor.RESET}")
        print(f"{PrintColor.CYAN}• Vision:   {PrintColor.WHITE}{'ON' if vision else 'OFF'}{PrintColor.RESET}")
        print(f"{PrintColor.CYAN}• Session:  {PrintColor.WHITE}{session_id}{PrintColor.RESET}")
        bar()

        # 欢迎
        panel_title("Welcome")
        print(f"{PrintColor.WHITE}• exit / quit : exit")
        print(f"{PrintColor.WHITE}• clear       : clear session{PrintColor.RESET}")
        bar()

        enable_thinking = think
        test_image_url = "https://ark-project.tos-cn-beijing.ivolces.com/images/view.jpeg" if vision else None

        while True:
            try:
                user_input = input(f"\n{PrintColor.GREEN}{PrintColor.BOLD}YOU > {PrintColor.RESET}").strip()
            except (KeyboardInterrupt, EOFError):
                print(f"\n{PrintColor.CYAN}👋 Goodbye{PrintColor.RESET}")
                break

            if user_input.lower() in {"exit", "quit"}:
                print(f"\n{PrintColor.CYAN}👋 Goodbye{PrintColor.RESET}")
                break

            if user_input.lower() == "clear":
                session_manager.delete_session(session_id)
                print(f"{PrintColor.GREEN}🗑 Session cleared{PrintColor.RESET}")
                continue

            if not user_input:
                continue

            session_manager.save_message(session_id, "user", user_input)
            
            # ========== 最小化修改：启动异步加载动画 ==========
            stop_loading = asyncio.Event()
            # 启动加载动画任务（后台异步，不阻塞）
            loading_task = asyncio.create_task(async_loading_indicator(stop_loading, "processing"))

            full_response = ""
            tool_call_content = ""
            tool_response_content = ""
            retrieval_content = ""

            try:
                async for event in event_generator(
                    base_dir=base_dir,
                    session_id=session_id,
                    enable_thinking=enable_thinking,
                    message=user_input,
                    image_url=test_image_url
                ):
                    # 收到第一个事件就停止加载动画
                    if not stop_loading.is_set():
                        stop_loading.set()
                        await loading_task  # 等待动画任务清理完毕

                    # 思考流
                    if event["type"] == EventType.REASONING_TOKEN_EVENT.value:
                        print(f"{PrintColor.DIM}{PrintColor.CYAN}{event['content']}{PrintColor.RESET}", end="", flush=True)

                    # 回答流
                    elif event["type"] == EventType.TOKEN_EVENT.value:
                        full_response += event["content"]
                        print(f"{PrintColor.BLUE}{event['content']}{PrintColor.RESET}", end="", flush=True)

                    # 工具调用流
                    elif event["type"] == EventType.TOOL_CALLING_EVENT.value:
                        tool_call_content += event["content"]
                        if DEBUGMODE:
                            print(f"{PrintColor.YELLOW}{event['content']}{PrintColor.RESET}", end="", flush=True)

                    # 工具执行
                    elif event["type"] == EventType.TOOL_EXECUTE_EVENT.value:
                        print(f"\n{PrintColor.YELLOW}🛠 TOOL: {event['tool']}{PrintColor.RESET}")
                        print(f"{PrintColor.DIM}Input: {str(event['input'])[:70]}{PrintColor.RESET}")
                        session_manager.save_message(session_id, "tool_execute", f"Using Tool: {event["tool"]}")

                    # 工具返回
                    elif event["type"] == EventType.TOOL_RESPONSE_MESSAGE.value:
                        tool_response_content += str(event["output"])
                        print(f"\n{PrintColor.PURPLE}📎 RESULT:{PrintColor.RESET} {str(event["output"])[:100]}{PrintColor.RESET}")
                        session_manager.save_message(session_id, "tool_response",  event["output"])

                    elif event["type"] == EventType.TOOL_EXECUTE_DONE_EVENT.value:
                        print(f"\n{PrintColor.GREEN}✅ Tool done{PrintColor.RESET}")

                    # 检索
                    elif event["type"] == EventType.RETRIEVAL_EVENT.value:
                        retrieval_content += str(event["results"])
                        print(f"\n{PrintColor.CYAN}📚 Retrieval: {len(event['results'])} items{PrintColor.RESET}")

                    # 全部结束
                    elif event["type"] == EventType.ALL_DONE_EVENT.value:
                        print()
                        bar()

                    elif event["type"] == EventType.AI_MESSAGE.value:
                        session_manager.save_message(session_id, "assistant", event["content"])

                    elif event["type"] == EventType.TOOLCALL_MESSAGE.value:
                        session_manager.save_message(session_id, "assistant", event["content"])

            except Exception as e:
                # 异常时停止加载动画
                if not stop_loading.is_set():
                    stop_loading.set()
                    await loading_task
                print(f"\n{PrintColor.RED}❌ Error: {e}{PrintColor.RESET}")
                traceback.print_exc()
                continue

    except Exception as e:
        print(f"\n{PrintColor.RED}💥 Crash: {e}{PrintColor.RESET}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n{PrintColor.RED}Fatal: {e}{PrintColor.RESET}")
        traceback.print_exc()
        sys.exit(1)
