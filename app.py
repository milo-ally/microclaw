import asyncio
import sys
import uuid
import traceback
from pathlib import Path
from typing import Optional
from enum import Enum 
import time
import os  # 新增：用于跨平台清屏
import pyfiglet
from termcolor import colored  # 搭配termcolor实现彩色输出
from pydantic import BaseModel 

# 统一导入，避免局部作用域覆盖问题
from config import get_base_dir, get_llm_config, get_rag_mode
from graph.agent import agent_manager
from graph.session_manager import session_manager
from tools.skills_scanner import scan_skills

DEBUGMODE = True

class PrintColor:
    """Terminal color styling class"""
    # Basic colors
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    PURPLE = "\033[35m"
    ORANGE = "\033[38;5;208m"
    CYAN = "\033[36m"
    PINK = "\033[38;5;205m"
    WHITE = "\033[37m"
    # Styles
    BOLD = "\033[1m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    DIM = "\033[2m"  # 新增：暗淡样式，提升层级感
    # Background colors
    BG_BLUE = "\033[44m"
    BG_GRAY = "\033[48;5;237m"
    BG_DARK = "\033[48;5;234m"  # 新增：深色背景，更有科技感
    # Reset
    RESET = "\033[0m"

# 新增：跨平台清屏函数（替代原有简单清屏）
def clear_terminal():
    """Cross-platform terminal clear"""
    os.system('cls' if os.name == 'nt' else 'clear')

class EventType(Enum): 
    REASONING_TOKEN_EVENT = "reasoning_token"
    TOKEN_EVENT = "token" 
    TOOL_CALLING_EVENT = "tool_calling"
    TOOL_EXECUTE_EVENT = "tool_execute"
    TOOL_RESPONSE_EVENT = "tool_response"
    TOOL_EXECUTE_DONE_EVENT = "tool_execute_done"
    RETRIEVAL_EVENT = "retrieval"
    ALL_DONE_EVENT = "all_done"

async def event_generator(
    base_dir: Path,
    session_id: str,
    enable_thinking: bool, 
    message: str, 
    image_url: Optional[str] = None
): 
    # ========== 关键修改：设置显眼的think标签 ==========
    THINK_WRAPPER_START = "\n<think>\n"  # 思考开始标签（换行+标记，更易区分）
    THINK_WRAPPER_END = "\n</think>\n"   # 思考结束标签
    has_output_start_tag = False  # 标记是否已输出开始标签

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
                # ========== 核心逻辑：处理思考内容的标签包裹 ==========
                if event["type"] == EventType.REASONING_TOKEN_EVENT.value:
                    if enable_thinking:
                        reasoning_content = event["content"]
                        # 1. 首次输出思考内容时，先输出开始标签
                        if not has_output_start_tag:
                            yield {
                                "type": EventType.REASONING_TOKEN_EVENT.value,
                                "content": THINK_WRAPPER_START  # 输出<think>开始标签
                            }
                            has_output_start_tag = True
                        # 2. 输出思考内容本身
                        yield {
                            "type": EventType.REASONING_TOKEN_EVENT.value,
                            "content": reasoning_content
                        }

                elif event["type"] == EventType.TOKEN_EVENT.value:
                    # 1. 遇到回复内容时，先闭合思考标签（如果已开启）
                    if enable_thinking and has_output_start_tag:
                        yield {
                            "type": EventType.REASONING_TOKEN_EVENT.value,
                            "content": THINK_WRAPPER_END  # 输出[/think]结束标签
                        }
                        has_output_start_tag = False
                    # 2. 输出回复内容
                    yield {
                        "type": EventType.TOKEN_EVENT.value,
                        "content": event["content"]
                    }

                # ========== 其他事件类型保持不变 ==========
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

                elif event["type"] == EventType.TOOL_RESPONSE_EVENT.value:
                    yield {
                        "type": EventType.TOOL_RESPONSE_EVENT.value,
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

                    # 输出完成事件
                    yield {
                        "type": EventType.ALL_DONE_EVENT.value,
                        "input_content": event["input_content"],
                        "reasoning_content": event["reasoning_content"],
                        "content": event["content"],
                        "tool_call_content": event["tool_call_content"],
                        "tool_response_content": event["tool_response_content"],
                        "retrieval_content": event["retrieval_content"],
                    }

                else: 
                    print(f"\n{PrintColor.RED}❌ Unknown event type: {event['type']}{PrintColor.RESET}")

            except Exception as e:
                print(f"\n{PrintColor.RED}[Event Processing Error] {type(e).__name__}: {str(e)}{PrintColor.RESET}")
                print(f"{PrintColor.RED}Stack trace: {traceback.format_exc()}{PrintColor.RESET}")
                raise RuntimeError(f"Error processing event: {str(e)}")
                
    except Exception as e:
        print(f"\n{PrintColor.RED}[Generator Initialization Error] {type(e).__name__}: {str(e)}{PrintColor.RESET}")
        print(f"{PrintColor.RED}Stack trace: {traceback.format_exc()}{PrintColor.RESET}")
        raise


def print_art_logo():
    ascii_art = pyfiglet.figlet_format("AUTOX", font="bulbhead")
    colored_art = colored(ascii_art, color="blue", attrs=["bold"])
    print(colored_art)
    print(f"{PrintColor.DIM}{PrintColor.CYAN}Automation AI Tool • v1.0{PrintColor.RESET}\n")

def print_loading_animation(text, duration=1.5):
    chars = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
    start_time = time.time()
    idx = 0
    while time.time() - start_time < duration:
        sys.stdout.write(f"\r{PrintColor.CYAN}{PrintColor.BOLD}[*] {PrintColor.RESET}{chars[idx % len(chars)]} {text}{PrintColor.RESET}")
        sys.stdout.flush()
        time.sleep(0.08)
        idx += 1
    sys.stdout.write(f"\r{PrintColor.GREEN}{PrintColor.BOLD}[+] {text} {PrintColor.DIM}(completed){PrintColor.RESET}\n")

def get_session_id_from_user():
    """Get session ID from user input, auto-generate if empty"""
    print(f"\n{PrintColor.BOLD}{PrintColor.PINK}🔑 Session ID Configuration {PrintColor.RESET}")
    print(f"{PrintColor.WHITE}• Enter a custom session ID to restore historical session")
    print(f"• Press Enter directly to auto-generate a new session ID{PrintColor.RESET}")
    
    while True:
        try:
            user_input = input(f"\n{PrintColor.BOLD}{PrintColor.YELLOW}Please enter session ID (leave blank for auto-generation): {PrintColor.RESET}").strip()
            
            # Auto-generate if user input is empty
            if not user_input:
                auto_session_id = f"session_{uuid.uuid4().hex[:8]}"
                print(f"{PrintColor.GREEN}✅ Auto-generated session ID: {auto_session_id}{PrintColor.RESET}")
                return auto_session_id
            
            # Validate session ID format (simple validation to avoid illegal characters)
            import re
            if re.match(r'^[a-zA-Z0-9_-]{3,32}$', user_input):
                # Check if session exists
                try:
                    existing_history = session_manager.load_session_for_agent(user_input)
                    if existing_history:
                        print(f"{PrintColor.BLUE}ℹ️  Historical session found, will load {len(existing_history)} records{PrintColor.RESET}")
                    else:
                        print(f"{PrintColor.YELLOW}⚠️  Session ID does not exist, new session will be created{PrintColor.RESET}")
                    return user_input
                except Exception:
                    # Use user input ID even if loading fails
                    print(f"{PrintColor.YELLOW}⚠️  Unable to verify session status, will create new session with custom ID{PrintColor.RESET}")
                    return user_input
            else:
                print(f"{PrintColor.RED}❌ Invalid session ID format! Only letters, numbers, underscores, hyphens allowed, length 3-32 characters{PrintColor.RESET}")
        except (KeyboardInterrupt, EOFError):
            # Auto-generate ID if user interrupts input
            auto_session_id = f"session_{uuid.uuid4().hex[:8]}"
            print(f"\n{PrintColor.YELLOW}⚠️  Input interrupted, auto-generating session ID: {auto_session_id}{PrintColor.RESET}")
            return auto_session_id

# Interactive main function
async def main(): 
    try:
        # ========== Stylized startup interface ==========
        clear_terminal()
        
        # Print logo
        print_art_logo()
        
        # 优化：启动提示样式（深色背景+更专业的文案）
        print(f"{PrintColor.BG_DARK}{PrintColor.WHITE}{PrintColor.BOLD} Initializing AUTOX Core... {PrintColor.RESET}\n")
        
        # Load configurations (with animation)
        print_loading_animation("Loading base configuration", 0.8)
        base_dir = Path(get_base_dir())
        
        print_loading_animation("Initializing LLM configuration", 0.8)
        llm_config = get_llm_config()
        
        print_loading_animation("Configuring RAG mode", 0.8)
        rag_mode = get_rag_mode()
        
        # ========== New: Get/generate session ID ==========
        session_id = get_session_id_from_user()
        
        # ========== Print initialization info (优化排版，更有层级感) ==========
        print(f"\n{PrintColor.BOLD}{PrintColor.BLUE}{PrintColor.UNDERLINE}📋 System Information {PrintColor.RESET}")
        print(f"{PrintColor.CYAN}┌─────────────────────────────────────────────────────{PrintColor.RESET}")
        print(f"{PrintColor.CYAN}│ Base directory: {PrintColor.WHITE}{base_dir}{PrintColor.RESET}")
        print(f"{PrintColor.CYAN}│ LLM model:      {PrintColor.WHITE}{llm_config.get('info', {}).get('model', 'Unknown')}{PrintColor.RESET}")
        print(f"{PrintColor.CYAN}│ RAG mode:       {PrintColor.WHITE}{'✅ Enabled' if rag_mode else '❌ Disabled'}{PrintColor.RESET}")
        print(f"{PrintColor.CYAN}│ Thinking mode:  {PrintColor.WHITE}{'✅ Enabled' if llm_config.get('info', {}).get('enable_thinking', False) else '❌ Disabled'}{PrintColor.RESET}")
        print(f"{PrintColor.CYAN}│ Vision model:   {PrintColor.WHITE}{'✅ Enabled' if llm_config.get('info', {}).get('is_vision_model', False) else '❌ Disabled'}{PrintColor.RESET}")
        print(f"{PrintColor.CYAN}│ Session ID:     {PrintColor.WHITE}{session_id}{PrintColor.RESET}")
        print(f"{PrintColor.CYAN}└─────────────────────────────────────────────────────{PrintColor.RESET}")
        
        # Check session_manager
        try:
            history = session_manager.load_session_for_agent(session_id) or []
            print(f"\n{PrintColor.GREEN}✅ Session manager is ready, number of history records: {len(history)}{PrintColor.RESET}")
        except Exception as e:
            history = []
            print(f"\n{PrintColor.YELLOW}⚠️  Failed to load session history, using empty history: {e}{PrintColor.RESET}")
        
        enable_thinking = llm_config.get("info", {}).get("enable_thinking", False)
        is_vision_model = llm_config.get("info", {}).get("is_vision_model", False)
        test_image_url = "https://ark-project.tos-cn-beijing.ivolces.com/images/view.jpeg" if is_vision_model else None

        # ========== Welcome message ==========
        print(f"\n{PrintColor.BG_BLUE}{PrintColor.WHITE}{PrintColor.BOLD} Welcome to AUTOX AI Platform {PrintColor.RESET}")
        print(f"{PrintColor.BOLD}{PrintColor.CYAN}💡 Operation Instructions:{PrintColor.RESET}")
        print(f"   {PrintColor.WHITE}• Enter {PrintColor.YELLOW}exit/quit {PrintColor.WHITE}to exit the program")
        print(f"   • Enter {PrintColor.YELLOW}clear {PrintColor.WHITE}to clear current session history")
        print(f"   • Enter content directly to start conversation")
        print(f"   • Current session ID: {PrintColor.PURPLE}{session_id}{PrintColor.RESET}")
        print(f"\n{PrintColor.BOLD}{PrintColor.BLUE}──────────────────────────────────────────────{PrintColor.RESET}\n")

        while True:
            # Reset full response content for each conversation
            full_response = ""
            tool_call_content = ""
            tool_response_content = ""
            retrieval_content = ""
            
            # Get user input (stylized prompt)
            try:
                user_input = input(f"{PrintColor.BOLD}{PrintColor.GREEN}YOU > {PrintColor.RESET}").strip()  
            except (KeyboardInterrupt, EOFError):
                print(f"\n\n{PrintColor.CYAN}👋 Goodbye! {PrintColor.RESET}")
                break

            # Exit logic
            if user_input.lower() in {"exit", "quit"}:
                print(f"\n{PrintColor.CYAN}👋 Goodbye! {PrintColor.RESET}")
                break

            # Clear history
            if user_input.lower() == "clear":
                try:
                    session_manager.delete_session(session_id)
                    print(f"\n{PrintColor.GREEN}🗑️  Session {session_id} cleared! {PrintColor.RESET}\n")
                except Exception as e:
                    print(f"{PrintColor.RED}❌ Failed to clear session: {e}{PrintColor.RESET}")
                continue

            # Skip empty input
            if not user_input:
                continue

            print(f"{PrintColor.BOLD}{PrintColor.BLUE}AUTOX > {PrintColor.RESET}", end="", flush=True)
            
            # Start interaction (stylized prompt)
            try:
                async for event in event_generator(
                    base_dir=base_dir, 
                    session_id=session_id, 
                    enable_thinking=enable_thinking,
                    message=user_input,
                    image_url=test_image_url
                ):
                    # Output event content 
                    if event["type"] == EventType.REASONING_TOKEN_EVENT.value:
                        print(f"{PrintColor.CYAN}{PrintColor.ITALIC}{event['content']}{PrintColor.RESET}", end="", flush=True)

                    elif event["type"] == EventType.TOKEN_EVENT.value:
                        full_response += event["content"]
                        print(f"{PrintColor.BLUE}{event['content']}{PrintColor.RESET}", end="", flush=True)

                    elif event["type"] == EventType.TOOL_CALLING_EVENT.value:
                        tool_call_content += event["content"]
                        if DEBUGMODE:
                            print(f"{PrintColor.ORANGE}{event['content']}{PrintColor.RESET}", end="", flush=True)

                    elif event["type"] == EventType.TOOL_EXECUTE_EVENT.value:
                        print()
                        print(f"{PrintColor.BOLD}{PrintColor.YELLOW}🛠️  [Tool Execution]{PrintColor.RESET}")
                        print(f"   {PrintColor.YELLOW}Tool name: {event['tool']}{PrintColor.RESET}")
                        print(f"   {PrintColor.YELLOW}Input parameters: {str(event['input'])[:80]}{PrintColor.RESET}", flush=True)

                    elif event["type"] == EventType.TOOL_RESPONSE_EVENT.value:
                        tool_response_content += str(event["output"])
                        print()
                        print(f"{PrintColor.BOLD}{PrintColor.PURPLE}📊 [Tool Response]{PrintColor.RESET}")
                        print(f"   {PrintColor.PURPLE}Response result: {str(event['output'])[:120]}{PrintColor.RESET}", flush=True)

                    elif event["type"] == EventType.TOOL_EXECUTE_DONE_EVENT.value:
                        print(f"\n{PrintColor.BOLD}{PrintColor.YELLOW}✅ [Tool Execution Completed]{PrintColor.RESET}\n")

                    elif event["type"] == EventType.RETRIEVAL_EVENT.value:
                        retrieval_content += str(event["results"])
                        print()
                        print(f"{PrintColor.BOLD}{PrintColor.BLUE}📚 [RAG Retrieval]{PrintColor.RESET}")
                        print(f"   {PrintColor.BLUE}Found {len(event['results'])} relevant items{PrintColor.RESET}")
                        print(f"   {PrintColor.BLUE}Content summary: {event['results']}{PrintColor.RESET}")

                    elif event["type"] == EventType.ALL_DONE_EVENT.value:
                        print()
                        if DEBUGMODE:
                            print(f"\n{PrintColor.BOLD}{PrintColor.WHITE}📈 Session Statistics {PrintColor.RESET}")
                            print(f"{PrintColor.CYAN}├── Input length: {len(event['input_content'])}{PrintColor.RESET}")
                            print(f"{PrintColor.CYAN}├── Reasoning content length: {len(event['reasoning_content'])}{PrintColor.RESET}")
                            print(f"{PrintColor.CYAN}├── Response content length: {len(event['content'])}{PrintColor.RESET}")
                            print(f"{PrintColor.CYAN}├── Tool call content length: {len(event['tool_call_content'])}{PrintColor.RESET}")
                            print(f"{PrintColor.CYAN}├── Tool response content length: {len(event['tool_response_content'])}{PrintColor.RESET}")
                            print(f"{PrintColor.CYAN}└── Retrieval content length: {len(event['retrieval_content'])}{PrintColor.RESET}")
                        
                        # Save session information
                        try:
                            session_manager.save_message(session_id, "user", user_input)
                            session_manager.save_message(session_id, "assistant", full_response)
                            if rag_mode:
                                session_manager.save_message(session_id, "retrieval", retrieval_content)
                            if DEBUGMODE:
                                print(f"DEBUG: Saving session_id={session_id}")
                                print(f"\n{PrintColor.GREEN}✅ Session saved{PrintColor.RESET}")
                        except Exception as e:
                            print(f"{PrintColor.RED}❌ Failed to save session: {e}{PrintColor.RESET}")
                        
                        # Stylized separator（换行后输出分隔线）
                        print(f"\n{PrintColor.BOLD}{PrintColor.BLUE}──────────────────────────────────────────────{PrintColor.RESET}\n")
                    else: 
                        print(f"\n{PrintColor.RED}❌ Unknown event type: {event['type']}{PrintColor.RESET}")
            except Exception as e:
                print(f"\n{PrintColor.RED}❌ [Interaction Error] {type(e).__name__}: {str(e)}{PrintColor.RESET}")
                print(f"{PrintColor.RED}📝 Error details: {traceback.format_exc()}{PrintColor.RESET}")
                continue
    except Exception as e:
        print(f"\n{PrintColor.RED}💥 [Main Function Error] {type(e).__name__}: {str(e)}{PrintColor.RESET}")
        print(f"{PrintColor.RED}📝 Full error information:\n{traceback.format_exc()}{PrintColor.RESET}")
        sys.exit(1)

if __name__ == "__main__":
    # Ultimate error capture
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n{PrintColor.RED}💥 [Program Crash] {type(e).__name__}: {str(e)}{PrintColor.RESET}")
        print(f"{PrintColor.RED}📝 Full stack trace:\n{traceback.format_exc()}{PrintColor.RESET}")
        sys.exit(1)