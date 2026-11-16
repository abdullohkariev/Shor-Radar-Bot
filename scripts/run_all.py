"""One command to run everything:  python -m scripts.run_all

Starts (1) the web server for the Mini App, (2) a free Cloudflare quick tunnel that gives it a public
HTTPS address (Telegram requires HTTPS), and (3) the Telegram bot with that address configured.
The tunnel address changes every run; the bot re-registers it automatically. Ctrl+C stops all three."""
import asyncio
import os
import pathlib
import re
import shutil
import subprocess
import sys
import threading

ROOT = pathlib.Path(__file__).resolve().parent.parent
PORT = int(os.getenv("PORT", "8000"))


def start_tunnel():
    local = ROOT / "tools" / ("cloudflared.exe" if os.name == "nt" else "cloudflared")
    exe = local if local.exists() else shutil.which("cloudflared")
    if not exe:
        sys.exit("cloudflared not found. Install it once with:  winget install --id Cloudflare.cloudflared  (then reopen the terminal)")
    proc = subprocess.Popen([str(exe), "tunnel", "--url", f"http://localhost:{PORT}", "--no-autoupdate"],
                            stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    found = threading.Event()
    url = {}

    def pump():
        for line in proc.stderr:       # keep draining so the pipe never fills up
            if " ERR " in line or "error" in line.lower():
                print("cloudflared:", line.strip()[:200], flush=True)
            m = re.search(r"https://(?!api\.)[a-z0-9-]+\.trycloudflare\.com", line)   # api.trycloudflare.com is Cloudflare's own server, not our tunnel
            if m and "url" not in url:
                url["url"] = m.group(0)
                found.set()
    threading.Thread(target=pump, daemon=True).start()
    if not found.wait(60):
        proc.terminate()
        sys.exit("Tunnel did not start within 60 s (check your internet connection).")
    return proc, url["url"]


def keep_awake():
    """Windows: stop the laptop from going to sleep while this runs (the screen may still turn off)."""
    if os.name == "nt":
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)    # ES_CONTINUOUS | ES_SYSTEM_REQUIRED


async def healthy(url: str) -> bool:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            return (await c.get(url + "/api/health")).status_code == 200
    except Exception:
        return False


SERVER_CMD = [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(PORT)]


async def run(procs: dict):
    """procs = {"server": Popen, "tunnel": Popen, "url": str}; the watchdog keeps it up to date."""
    from app import bot, config

    async def watchdog():
        """Every 30 s check the PUBLIC address. If the tunnel died or stopped answering 3 times in a row,
        start a new one, move the bot's menu button to the new address and keep going."""
        bad = 0
        while True:
            await asyncio.sleep(30)
            if procs["server"].poll() is not None:
                print("web server exited, restarting", flush=True)
                procs["server"] = subprocess.Popen(SERVER_CMD, cwd=ROOT)
            ok = procs["tunnel"].poll() is None and await healthy(procs["url"])
            bad = 0 if ok else bad + 1
            if bad >= 3 or procs["tunnel"].poll() is not None:
                print("tunnel is down, starting a new one...", flush=True)
                procs["tunnel"].terminate()
                try:
                    procs["tunnel"], procs["url"] = await asyncio.to_thread(start_tunnel)
                except SystemExit as e:
                    print(e, flush=True)
                    continue
                config.WEBAPP_URL = procs["url"]
                await bot.refresh_menu_button()
                print(f"New Mini App address: {procs['url']}/app", flush=True)
                bad = 0

    wd = asyncio.create_task(watchdog())
    try:
        await bot.main()
    finally:
        wd.cancel()


def main():
    keep_awake()
    procs = {"server": subprocess.Popen(SERVER_CMD, cwd=ROOT)}
    procs["tunnel"], procs["url"] = start_tunnel()
    print(f"Mini App address: {procs['url']}/app", flush=True)
    os.environ["WEBAPP_URL"] = procs["url"]
    from app import config
    config.WEBAPP_URL = procs["url"]
    try:
        asyncio.run(run(procs))
    except KeyboardInterrupt:
        pass
    finally:
        procs["tunnel"].terminate()
        procs["server"].terminate()


if __name__ == "__main__":
    main()
