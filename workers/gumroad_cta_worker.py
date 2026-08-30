"""Leverage Gumroad CTA Worker.

Updates only Product 1's description with a tracked free-calculator CTA and
verifies the public Gumroad listing. Uses the existing authenticated browser
profile. No pricing, payout, payment, or account changes.
"""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

P001_ID = "neiqwz"
GUMROAD_EDIT = f"https://gumroad.com/products/{P001_ID}/edit"
GUMROAD_PUBLIC = f"https://newbiezz.gumroad.com/l/{P001_ID}"
CTA_URL = "https://leverage-tools.pages.dev/fabrication-quote-calculator/?utm_source=gumroad&utm_medium=product&utm_campaign=p001&utm_content=free-calculator"
CTA_LABEL = "Try the FREE Fabrication Quote Calculator"
PROFILE = Path(os.environ.get("LEVERAGE_BROWSER_PROFILE", r"D:\Leverage\browser-profile"))
SUMMARY = "Know the cost and margin before you quote."
DESCRIPTION = (
    f"{SUMMARY}\n\n"
    "A macro-free Excel toolkit for small fabrication, welding, machine and job shops.\n\n"
    "TRY THE FREE TOOL FIRST\n"
    f"{CTA_LABEL}\n{CTA_URL}\n\n"
    "WHAT YOU GET\n"
    "- Shop Rate Calculator\n- Quote Builder\n- Material and Consumables Costing\n"
    "- Target-Margin Profit Check\n- Job Log - Quoted vs Actual\n- Change Order Register\n"
    "- Sample Job Data\n- Quick-Start Guide\n\n"
    "WHY IT IS DIFFERENT\n"
    "- Macro-free - no VBA required\n- No subscription for the workbook\n"
    "- Uses your own rates and assumptions\n- Built around fabrication and job-shop quoting\n"
    "- Includes the post-job actual-vs-estimate learning loop\n\n"
    "WHO IT IS FOR\n"
    "Fabrication shops, welding businesses, machine/job shops, engineering workshops and small contractors pricing custom work.\n\n"
    "IMPORTANT\n"
    "This is a quoting and job-costing tool, not accounting, tax, legal or engineering certification software. Replace example assumptions with your own verified business inputs.\n\n"
    "DIGITAL PRODUCT\n"
    "You receive downloadable digital files after purchase."
)


def playwright() -> str:
    for name in ("playwright-cli.cmd", "playwright-cli"):
        found = shutil.which(name)
        if found:
            return found
    fallback = os.path.join(
        os.environ.get("LEVERAGE_NPM_GLOBAL", r"D:\development\node.js\npm-global"),
        "playwright-cli.cmd",
    )
    if os.path.exists(fallback):
        return fallback
    raise FileNotFoundError("playwright-cli was not found")


def run(*args: str, timeout: int = 90, allow_fail: bool = False) -> str:
    proc = subprocess.run(
        [playwright(), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        shell=False,
    )
    out = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
    if proc.returncode and not allow_fail:
        raise RuntimeError(out or f"playwright-cli exited {proc.returncode}")
    return out


def snap() -> str:
    return run("snapshot", timeout=60)


def ref(snapshot_text: str, role: str, name: str) -> str | None:
    match = re.search(rf'{role} "{re.escape(name)}" \[ref=([^\]]+)\]', snapshot_text)
    return match.group(1) if match else None


def attach() -> None:
    try:
        attached = run("attach", "default", timeout=30, allow_fail=True)
    except Exception:
        attached = ""
    if "attached" not in attached.lower():
        run(
            "open",
            "https://gumroad.com/products",
            "--browser=chromium",
            "--headed",
            "--persistent",
            f"--profile={PROFILE}",
            timeout=90,
        )


def _js_b64(value: str, encoding: str = "utf-8") -> str:
    return base64.b64encode(value.encode(encoding)).decode("ascii")


def update_description() -> None:
    run("goto", GUMROAD_EDIT, timeout=60)
    s = snap()
    save = ref(s, "button", "Save changes")
    if not save:
        raise RuntimeError("Gumroad Save changes button not found")

    text64 = _js_b64(DESCRIPTION)
    url64 = _js_b64(CTA_URL, "ascii")
    label64 = _js_b64(CTA_LABEL)
    js = (
        "async () => {"
        f"const text=Array.from(atob({json.dumps(text64)}),c=>String.fromCharCode(c.charCodeAt(0))).join('');"
        f"const url=Array.from(atob({json.dumps(url64)}),c=>String.fromCharCode(c.charCodeAt(0))).join('');"
        f"const label=Array.from(atob({json.dumps(label64)}),c=>String.fromCharCode(c.charCodeAt(0))).join('');"
        "const editors=page.locator('[contenteditable=\"true\"]');"
        "const count=await editors.count();"
        "if(!count) throw new Error('No contenteditable Gumroad description editor found');"
        "const editor=editors.last();"
        "await editor.click();"
        "await editor.fill(text);"
        "const walker=document.createTreeWalker(editor,NodeFilter.SHOW_TEXT);"
        "let node=null,start=-1;"
        "while(walker.nextNode()){const n=walker.currentNode;const i=(n.nodeValue||'').indexOf(label);if(i>=0){node=n;start=i;break;}}"
        "if(!node) throw new Error('CTA label text was not inserted into editor');"
        "const range=document.createRange();range.setStart(node,start);range.setEnd(node,start+label.length);"
        "const sel=window.getSelection();sel.removeAllRanges();sel.addRange(range);"
        "document.execCommand('createLink',false,url);"
        "editor.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:null}));"
        "editor.dispatchEvent(new Event('change',{bubbles:true}));"
        "return JSON.stringify({editors:count,linked:true});"
        "}"
    )
    run("run-code", js, timeout=60)

    # Re-snapshot because the editor DOM can rerender after input.
    fresh = snap()
    save = ref(fresh, "button", "Save changes")
    if not save:
        raise RuntimeError("Gumroad Save changes button not found after description update")
    run("click", save, timeout=30)


def verify() -> dict[str, Any]:
    run("goto", GUMROAD_PUBLIC, timeout=60)
    s = snap()
    read_more = ref(s, "button", "Read more")
    if read_more:
        run("click", read_more, timeout=30)
        s = snap()

    url64 = _js_b64(CTA_URL, "ascii")
    label64 = _js_b64(CTA_LABEL)
    js = (
        "async () => {"
        f"const url=Array.from(atob({json.dumps(url64)}),c=>String.fromCharCode(c.charCodeAt(0))).join('');"
        f"const label=Array.from(atob({json.dumps(label64)}),c=>String.fromCharCode(c.charCodeAt(0))).join('');"
        "const links=await page.locator('a').evaluateAll(els=>els.map(a=>({text:(a.innerText||'').trim(),href:a.href})));"
        "const exact=links.find(x=>x.href===url||x.href===url.replace(/\\/$/,''));"
        "const text=links.find(x=>(x.text||'').toLowerCase().includes(label.toLowerCase()));"
        "return JSON.stringify({url_guard:!!exact,label_guard:!!text,clickable_link_guard:!!exact,exact_link:exact||null,text_link:text||null});"
        "}"
    )
    raw = run("run-code", js, timeout=60)
    try:
        result = json.loads(raw.splitlines()[-1])
    except Exception:
        result = {
            "url_guard": False,
            "label_guard": False,
            "clickable_link_guard": False,
            "raw": raw,
        }
    body = s.lower()
    result["summary_guard"] = SUMMARY.lower() in body
    result["page_url"] = GUMROAD_PUBLIC
    return result


def main() -> int:
    attach()
    update_description()
    result = verify()
    ok = bool(
        result.get("url_guard")
        and result.get("label_guard")
        and result.get("clickable_link_guard")
        and result.get("summary_guard")
    )
    print(json.dumps({"ok": ok, "action": "gumroad_cta_update", **result}, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
