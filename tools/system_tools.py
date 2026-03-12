"""
LangChain @tool wrappers for OS-level actions.

Each function replaces the corresponding handler class. The agent
decides when to call them via natural-language reasoning — no regex
intent classification needed.
"""
from __future__ import annotations

import logging
import os
import subprocess
import time
import webbrowser
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus

import psutil
import requests
from langchain_core.tools import tool

from app_indexer.windows_app_indexer import WindowsAppIndexer
from config.constants import N8N_WEBHOOK_URL, DEFAULT_OLLAMA_URL, DEFAULT_LLM_MODEL
from os_control.win32_app_close import close_app_gracefully
from os_control.win32_window import get_main_window_for_pid
from os_control.screenshot import capture_monitor, capture_all_monitors, capture_monitor_for_screen_read

# ── Shared singletons ────────────────────────────────────────────────
_app_indexer = WindowsAppIndexer()

# These will be injected at boot-time by VoiceAssistant
_assistant_state = None  # type: ignore


def set_assistant_state(state):
    """Called once during startup to inject the global AssistantState."""
    global _assistant_state
    _assistant_state = state


# ── App Management ───────────────────────────────────────────────────

def _wait_for_window(pid: int, timeout: float = 2.0):
    end = time.time() + timeout
    while time.time() < end:
        hwnd = get_main_window_for_pid(pid)
        if hwnd:
            return hwnd
        time.sleep(0.1)
    return None


def _find_new_process_pid(app_name: str, timeout: float = 3.0):
    end = time.time() + timeout
    name = app_name.lower()
    while time.time() < end:
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if name in proc.info["name"].lower():
                    return proc.info["pid"]
            except Exception:
                continue
        time.sleep(0.2)
    return None


@tool
def open_app(app_name: str) -> str:
    """Open (launch) an application on Windows by its common name.
    Examples: 'Chrome', 'Notepad', 'Spotify', 'Visual Studio Code'."""
    from state.assistant_state import AppProcess

    entry = _app_indexer.search(app_name)
    if entry is None:
        return f"Could not find an application matching '{app_name}'. Please check the name and try again."

    app_type = entry["type"]

    if app_type == "exe":
        path = entry.get("path")
        if not path:
            return "Executable path missing for this application."
        try:
            proc = subprocess.Popen(path)
        except Exception as e:
            return f"Failed to open {app_name}: {e}"

        hwnd = _wait_for_window(proc.pid)
        if _assistant_state:
            app = AppProcess(
                name=app_name, pid=proc.pid, exe_path=path,
                opened_at=datetime.now(), hwnd=hwnd, focused=True,
            )
            _assistant_state.register_app(app)
        return f"{app_name} opened successfully."

    if app_type == "uwp":
        aumid = entry.get("aumid")
        if not aumid:
            return "UWP app id missing."
        subprocess.Popen(
            ["explorer.exe", f"shell:AppsFolder\\{aumid}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        pid = _find_new_process_pid(app_name)
        hwnd = _wait_for_window(pid) if pid else None
        if _assistant_state and pid:
            app = AppProcess(
                name=app_name, pid=pid, exe_path=aumid,
                opened_at=datetime.now(), hwnd=hwnd, focused=True,
            )
            _assistant_state.register_app(app)
        return f"{app_name} opened successfully."

    return f"Unsupported application type: {app_type}"


@tool
def close_app(app_name: Optional[str] = None) -> str:
    """Close an application. If no name given, closes the currently focused app."""
    if not _assistant_state:
        return "Assistant state not available."

    target_app = None
    target_pid = None

    if app_name:
        for pid, app in list(_assistant_state.opened_apps.items()):
            if app.name.lower().strip('.') == app_name.lower():
                target_app = app
                target_pid = pid
                break
    else:
        target_app = _assistant_state.get_focused_app() or _assistant_state.get_last_opened_app()

    if not target_app:
        return "No application found to close."

    success = close_app_gracefully(
        pid=target_pid or target_app.pid,
        hwnd=target_app.hwnd,
        app_name=target_app.name,
    )
    if success:
        _assistant_state.unregister_app(target_app.pid)
        return f"{target_app.name} closed."
    return f"Could not close {target_app.name}."


# ── Volume Control ───────────────────────────────────────────────────

@tool
def set_volume(level: int) -> str:
    """Set the system volume to a specific percentage (0-100)."""
    from os_control.win32_volume import set_volume as _set
    try:
        _set(level)
        return f"Volume set to {level}%."
    except Exception as e:
        return f"Volume control failed: {e}"


@tool
def increase_volume() -> str:
    """Increase the system volume by a step."""
    from os_control.win32_volume import increase_volume as _inc
    try:
        new = _inc()
        return f"Volume increased to {new}%."
    except Exception as e:
        return f"Volume control failed: {e}"


@tool
def decrease_volume() -> str:
    """Decrease the system volume by a step."""
    from os_control.win32_volume import decrease_volume as _dec
    try:
        new = _dec()
        return f"Volume decreased to {new}%."
    except Exception as e:
        return f"Volume control failed: {e}"


@tool
def mute_volume() -> str:
    """Mute the system audio."""
    from os_control.win32_volume import mute as _mute
    try:
        _mute()
        return "Volume muted."
    except Exception as e:
        return f"Volume control failed: {e}"


@tool
def unmute_volume() -> str:
    """Unmute the system audio."""
    from os_control.win32_volume import unmute as _unmute
    try:
        _unmute()
        return "Volume unmuted."
    except Exception as e:
        return f"Volume control failed: {e}"


@tool
def get_volume() -> str:
    """Get the current system volume level."""
    from os_control.win32_volume import get_volume as _get
    try:
        level = _get()
        return f"Current volume is {level}%."
    except Exception as e:
        return f"Volume control failed: {e}"


# ── Web Search ───────────────────────────────────────────────────────

@tool
def search_web(query: str) -> str:
    """Search the web using Google for the given query."""
    encoded = quote_plus(query)
    url = f"https://www.google.com/search?q={encoded}"
    webbrowser.open(url, new=0)
    return f"Searching for '{query}'."


# ── Weather & Email (via n8n) ────────────────────────────────────────

@tool
def get_weather() -> str:
    """Get the current weather information."""
    try:
        payload = {"intent_name": "GET_WEATHER", "data": ""}
        resp = requests.post(N8N_WEBHOOK_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        data = resp.json()
        msg = data.get("message", {})
        return msg.get("content", "Sorry, there was an error retrieving the weather.")
    except Exception as e:
        return f"Weather lookup failed: {e}"


@tool
def check_email() -> str:
    """Check and summarise the user's recent emails."""
    try:
        payload = {"intent_name": "CHECK_EMAIL", "data": ""}
        resp = requests.post(N8N_WEBHOOK_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        data = resp.json()
        msg = data.get("message", {})
        return msg.get("content", "Sorry, there was an error retrieving email information.")
    except Exception as e:
        return f"Email check failed: {e}"


# ── Screenshot ───────────────────────────────────────────────────────

@tool
def take_screenshot(monitor: str = "primary") -> str:
    """Take a screenshot. Monitor can be 'primary', 'all', or a monitor number like '1'."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_path = os.path.join(os.getcwd(), "screenshots")
    os.makedirs(base_path, exist_ok=True)

    if monitor == "all":
        path = os.path.join(base_path, f"screenshot_all_{timestamp}.png")
        capture_all_monitors(path)
        return "Screenshot of all monitors taken."

    if _assistant_state:
        if monitor in ("primary", "0"):
            mon = _assistant_state.monitors.get_primary()
        else:
            try:
                mon = _assistant_state.monitors.get_by_id(int(monitor))
            except Exception:
                return "Invalid monitor specified."

        if not mon:
            return "Monitor not found."

        path = os.path.join(base_path, f"screenshot_monitor_{mon.id}_{timestamp}.png")
        capture_monitor(mon, path)
        return f"Screenshot taken on monitor {mon.id}."

    return "Could not determine monitor layout."


# ── Read Screen (VLM) ────────────────────────────────────────────────

@tool
def read_screen() -> str:
    """Describe what is currently visible on the screen using a vision model."""
    try:
        import numpy as np
        import onnxruntime
        from transformers import AutoConfig, AutoProcessor

        model_id = "HuggingFaceTB/SmolVLM-256M-Instruct"
        config = AutoConfig.from_pretrained(model_id)
        processor = AutoProcessor.from_pretrained(model_id)

        vision_session = onnxruntime.InferenceSession("vision/vlm_model/vision_encoder_q4.onnx")
        embed_session = onnxruntime.InferenceSession("vision/vlm_model/embed_tokens_q4.onnx")
        decoder_session = onnxruntime.InferenceSession("vision/vlm_model/decoder_model_merged_q4.onnx")

        img = capture_monitor_for_screen_read()

        messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": "What is on this image?"}]}]
        prompt = processor.apply_chat_template(messages, add_generation_prompt=True)
        inputs = processor(text=prompt, images=[img], return_tensors="np")

        num_kv = config.text_config.num_key_value_heads
        head_dim = config.text_config.head_dim
        n_layers = config.text_config.num_hidden_layers
        eos = config.text_config.eos_token_id
        img_tok = config.image_token_id

        batch = inputs["input_ids"].shape[0]
        pkv = {
            f"past_key_values.{l}.{kv}": np.zeros([batch, num_kv, 0, head_dim], dtype=np.float32)
            for l in range(n_layers) for kv in ("key", "value")
        }

        input_ids = inputs["input_ids"]
        attn = inputs["attention_mask"]
        pos = np.cumsum(attn, axis=-1)
        gen = np.array([[]], dtype=np.int64)
        img_feat = None

        for _ in range(500):
            emb = embed_session.run(None, {"input_ids": input_ids})[0]
            if img_feat is None:
                img_feat = vision_session.run(
                    ["image_features"],
                    {"pixel_values": inputs["pixel_values"], "pixel_attention_mask": inputs["pixel_attention_mask"].astype(np.bool_)},
                )[0]
                emb[inputs["input_ids"] == img_tok] = img_feat.reshape(-1, img_feat.shape[-1])

            logits, *pkv_out = decoder_session.run(None, dict(inputs_embeds=emb, attention_mask=attn, position_ids=pos, **pkv))
            input_ids = logits[:, -1].argmax(-1, keepdims=True)
            attn = np.ones_like(input_ids)
            pos = pos[:, -1:] + 1
            for j, key in enumerate(pkv):
                pkv[key] = pkv_out[j]
            gen = np.concatenate([gen, input_ids], axis=-1)
            if (input_ids == eos).all():
                break

        text = processor.batch_decode(gen)[0]
        if "Assistant:" in text:
            text = text.split("Assistant:", 1)[1].strip()

        # Send to n8n for richer response
        payload = {"intent_name": "READ_SCREEN", "data": text}
        resp = requests.post(N8N_WEBHOOK_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        data = resp.json()
        msg = data.get("message", {})
        return msg.get("content", text)

    except Exception as e:
        logging.error(f"read_screen error: {e}")
        return "Sorry, I am unable to look at the screen at the moment."


# ── System Health ────────────────────────────────────────────────────

@tool
def system_health_check() -> str:
    """Check the health of all voice assistant modules and services."""
    modules = _assistant_state.module_status if _assistant_state else {}

    llm_ok = False
    try:
        r = requests.get(DEFAULT_OLLAMA_URL.replace("/api/generate", "/api/tags"), timeout=2)
        llm_ok = r.status_code == 200
    except Exception:
        pass

    n8n_ok = False
    try:
        base = N8N_WEBHOOK_URL.split("/webhook/")[0]
        r = requests.get(base, timeout=2)
        n8n_ok = r.status_code == 200
    except Exception:
        pass

    report = {
        "modules": modules,
        "services": {"llm": llm_ok, "n8n": n8n_ok},
    }

    parts = []
    for name, ok in modules.items():
        parts.append(f"{name}: {'online' if ok else 'offline'}")
    parts.append(f"LLM service: {'online' if llm_ok else 'offline'}")
    parts.append(f"n8n service: {'online' if n8n_ok else 'offline'}")
    return "System health report — " + ", ".join(parts) + "."


# ── Window Management ───────────────────────────────────────────────

@tool
def move_window(direction: str) -> str:
    """Move the currently focused window to another monitor.
    Direction should be 'left' or 'right'."""
    try:
        import win32gui, win32process, win32api
        import pygetwindow as gw
        import screeninfo
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32

        monitors = screeninfo.get_monitors()
        if len(monitors) < 2:
            return "Window moving requires at least two monitors."

        monitor_index = 1 if direction == "left" else 0

        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return "No foreground window found."

        class RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                        ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

        work_areas = []
        def callback(hMon, hdc, lprc, data):
            info = win32api.GetMonitorInfo(hMon)
            work_areas.append(info["Work"])
            return True

        user32.EnumDisplayMonitors(
            0, 0,
            ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HMONITOR, wintypes.HDC,
                               ctypes.POINTER(RECT), wintypes.LPARAM)(callback),
            0,
        )

        if monitor_index >= len(work_areas):
            return "Monitor index out of range."

        left, top, right, bottom = work_areas[monitor_index]
        window = gw.Win32Window(hwnd)
        mon = monitors[monitor_index]

        if window.isMinimized or window.isMaximized:
            window.restore()

        window.moveTo(mon.x, mon.y)
        window.resizeTo(right - left, bottom - top)
        return f"Moved window to the {direction} monitor."

    except Exception as e:
        return f"Failed to move window: {e}"


# ── n8n Workflow Trigger ─────────────────────────────────────────────

@tool
def trigger_n8n(workflow: str, parameters: Optional[dict] = None) -> str:
    """Trigger an n8n automation workflow by name.
    Use for complex multi-step tasks like sending messages, creating reminders, etc."""
    parameters = parameters or {}
    payload = {
        "workflow": workflow,
        "parameters": parameters,
        "raw_intent": "TRIGGER_N8N",
        "user_context": {},
    }
    try:
        resp = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("speech", data.get("message", "Workflow executed successfully."))
    except requests.exceptions.RequestException as e:
        logging.error(f"n8n request failed: {e}")
        return "Failed to connect to the automation server."
    except Exception as e:
        logging.error(f"n8n handler error: {e}")
        return "An error occurred while executing the automation."


# ── Collect all tools ────────────────────────────────────────────────

ALL_TOOLS = [
    open_app,
    close_app,
    set_volume,
    increase_volume,
    decrease_volume,
    mute_volume,
    unmute_volume,
    get_volume,
    search_web,
    get_weather,
    check_email,
    take_screenshot,
    read_screen,
    system_health_check,
    move_window,
    trigger_n8n,
]
