"""Leverage Browser Worker v1."""
from __future__ import annotations
import json, os, re, shutil, subprocess
from dataclasses import dataclass
from typing import Any
FORBIDDEN_TERMS={"price","pricing","amount","payout","bank","password","email","payment","refund","unpublish","publish","delete","money","withdraw","tax","security","account owner"}
@dataclass
class BrowserResult:
    ok: bool
    action: str
    detail: str
    data: dict[str,Any]
def _playwright_executable()->str:
    for c in ("playwright-cli.cmd","playwright-cli"):
        p=shutil.which(c)
        if p:return p
    p=os.path.join(os.environ.get("LEVERAGE_NPM_GLOBAL",r"D:\development\node.js\npm-global"),"playwright-cli.cmd")
    if os.path.exists(p):return p
    raise FileNotFoundError("playwright-cli was not found")
def _run_cli(*args:str,timeout:int=60,allow_fail:bool=False)->str:
    proc=subprocess.run([_playwright_executable(),*args],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=timeout,shell=False)
    out=(proc.stdout or "")+"\n"+(proc.stderr or "")
    out=out.strip()
    if proc.returncode and not allow_fail: raise RuntimeError(out or f"playwright-cli exited {proc.returncode}")
    return out
def authorize_goal(goal:str)->BrowserResult:
    hits=sorted(t for t in FORBIDDEN_TERMS if t in goal.lower())
    return BrowserResult(not hits,"authorize","Goal is allowed." if not hits else "Blocked protected action.",{"blocked_terms":hits})
def snapshot()->str:return _run_cli("snapshot",timeout=60)
def attach_or_open(profile:str)->BrowserResult:
    a=_run_cli("attach","default",timeout=30,allow_fail=True)
    if "attached" in a.lower(): return BrowserResult(True,"attach","Attached to existing browser.",{"snapshot":snapshot()})
    _run_cli("open","https://gumroad.com/products","--browser=chromium","--headed","--persistent",f"--profile={profile}",timeout=90)
    return BrowserResult(True,"open","Opened browser.",{"snapshot":snapshot()})
def _extract_ref(snap:str,label:str)->str|None:
    m=re.search(rf'(?:textbox|button|combobox) "{re.escape(label)}" \[ref=([^\]]+)\]',snap)
    return m.group(1) if m else None
def find_product(product_id:str)->BrowserResult:
    _run_cli("goto","https://gumroad.com/products",timeout=60); snap=snapshot(); ok=product_id in snap and "Fabrication Shop Profit & Quote System".lower() in snap.lower(); return BrowserResult(ok,"find_product","Existing product located." if ok else "Product not found.",{"snapshot":snap})
def edit_p001_listing()->BrowserResult:
    summary="Know the cost and margin before you quote."
    html=("<p><strong>Know the cost and margin before you quote.</strong></p>"
    "<p>A macro-free Excel toolkit for small fabrication, welding, machine and job shops.</p>"
    "<p><strong>WHAT YOU GET</strong></p><p>• Shop Rate Calculator<br>• Quote Builder<br>• Material &amp; Consumables Costing<br>• Target-Margin Profit Check<br>• Job Log — Quoted vs Actual<br>• Change Order Register<br>• Sample Job Data<br>• Quick-Start Guide</p>"
    "<p><strong>WHY IT IS DIFFERENT</strong></p><p>• Macro-free — no VBA required<br>• No subscription for the workbook<br>• Uses your own rates and assumptions<br>• Built around fabrication and job-shop quoting<br>• Includes the post-job actual-vs-estimate learning loop</p>"
    "<p><strong>WHO IT IS FOR</strong></p><p>Fabrication shops, welding businesses, machine/job shops, engineering workshops and small contractors pricing custom work.</p>"
    "<p><strong>IMPORTANT</strong></p><p>This is a quoting and job-costing tool, not accounting, tax, legal or engineering certification software. Replace example assumptions with your own verified business inputs.</p>"
    "<p><strong>DIGITAL PRODUCT</strong></p><p>You receive downloadable digital files after purchase.</p>")
    _run_cli("goto","https://gumroad.com/products/neiqwz/edit",timeout=60); snap=snapshot(); sr=_extract_ref(snap,"Summary"); save=_extract_ref(snap,"Save changes")
    if not sr or not save:return BrowserResult(False,"edit","Required controls not found.",{"snapshot":snap})
    _run_cli("fill",sr,summary,timeout=30)
    payload=json.dumps(html,ensure_ascii=False)
    js=f"() => {{ const el=document.querySelector('[contenteditable=true]'); if(!el) throw new Error('Description editor not found'); el.innerHTML={payload}; el.dispatchEvent(new InputEvent('input',{{bubbles:true,inputType:'insertText'}})); return el.innerText; }}"
    _run_cli("eval",js,timeout=30); _run_cli("click",save,timeout=30); verify=snapshot()
    price_ok=bool(re.search(r'textbox "Amount"[^\n]*"19"',verify)); pub_ok='button "Unpublish"' in verify; sum_ok=summary.lower() in verify.lower(); ok=price_ok and pub_ok and sum_ok
    return BrowserResult(ok,"edit_p001_listing","Listing saved and guards verified." if ok else "Verification failed.",{"price_guard":price_ok,"published_guard":pub_ok,"summary_guard":sum_ok,"snapshot":verify})
def execute(goal:str,profile:str)->BrowserResult:
    a=authorize_goal(goal)
    if not a.ok:return a
    b=attach_or_open(profile)
    if not b.ok:return b
    p=find_product("neiqwz")
    if not p.ok:return p
    if "optimize" not in goal.lower() and "update" not in goal.lower():return BrowserResult(True,"plan_only","Goal validated; no edit requested.",{})
    return edit_p001_listing()
if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument("goal"); ap.add_argument("--profile",default=os.environ.get("LEVERAGE_BROWSER_PROFILE",r"D:\Leverage\browser-profile")); a=ap.parse_args(); r=execute(a.goal,a.profile); print(json.dumps({"ok":r.ok,"action":r.action,"detail":r.detail,**r.data},indent=2,ensure_ascii=False))
