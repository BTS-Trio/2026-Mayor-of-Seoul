import asyncio
import json
import os
import socket
import sqlite3
import subprocess
import threading
import time
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlopen

import uvicorn
from websockets.sync.client import connect

root = Path(__file__).resolve().parent
chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


def until(callback, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = callback()
        if result:
            return result
        time.sleep(0.1)
    raise RuntimeError("Timed out waiting for " + repr(callback))


with TemporaryDirectory(prefix="housing-review-browser-", ignore_cleanup_errors=True) as work:
    directory = Path(work)
    db = directory / "housing-review.sqlite3"
    os.environ["HOUSING_REVIEW_DB"] = str(db)
    os.environ["ELECTION_REVIEW_KEY"] = "browser-test-key"
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config("app:app", log_level="warning"))
    thread = threading.Thread(
        target=lambda: asyncio.run(server.serve(sockets=[listener]), loop_factory=asyncio.SelectorEventLoop),
        daemon=True,
    )
    thread.start()
    with (directory / "chrome.log").open("wb") as log:
        browser = None
        try:
            until(lambda: server.started)
            address = f"http://127.0.0.1:{port}/housing-review"
            print("Server ready", urlopen(address, timeout=5).status, flush=True)
            profile = directory / "chrome-profile"
            browser = subprocess.Popen([
                str(chrome), "--headless=new", "--no-first-run", "--disable-gpu",
                "--disable-background-networking", "--remote-debugging-port=0",
                f"--user-data-dir={profile}", "about:blank",
            ], stdout=log, stderr=log)
            endpoint = profile / "DevToolsActivePort"
            def browser_port():
                if browser.poll() is not None:
                    raise RuntimeError(f"Chrome exited with {browser.returncode}")
                if endpoint.is_file():
                    return endpoint.read_text().splitlines()[0]
            debugging = until(browser_port)
            targets = json.load(urlopen(f"http://127.0.0.1:{debugging}/json/list", timeout=5))
            page = next(item for item in targets if item["type"] == "page")
            with connect(page["webSocketDebuggerUrl"], open_timeout=5, proxy=None) as client:
                sequence = 0
                def command(method, **params):
                    global sequence
                    sequence += 1
                    client.send(json.dumps(dict(id=sequence, method=method, params=params)))
                    while True:
                        reply = json.loads(client.recv(timeout=8))
                        if reply.get("id") == sequence:
                            if "error" in reply:
                                raise RuntimeError(reply["error"])
                            return reply.get("result", {})

                def js(expression):
                    result = command("Runtime.evaluate", expression=expression, returnByValue=True)
                    if "exceptionDetails" in result:
                        raise RuntimeError(result["exceptionDetails"])
                    return result["result"].get("value")

                command("Page.navigate", url=f"http://127.0.0.1:{port}/offline-preview.html")
                until(lambda: js("document.querySelector('#housing-editor')?.hidden === false"))
                js("document.querySelector('#housing-editor summary').click(); document.querySelector('a[href=\"/housing-review\"]').click()")
                until(lambda: js("document.querySelector('#history li')?.textContent"))
                js("get('reviewer').value='Browser QA'; get('review-key').value='browser-test-key'; get('run').click()")
                until(lambda: js("get('validation').textContent && !get('run').disabled"))
                assert js("!get('approve').disabled"), js("get('validation').textContent")
                js("get('approve').click()")
                until(lambda: js("get('message').textContent.includes('\\uc2b9\\uc778 \\uc644\\ub8cc')"))

                js("get('scenario').value='missing_source'; get('run').click()")
                until(lambda: js("get('validation').textContent && !get('run').disabled"))
                assert js("get('approve').disabled && !get('reject').disabled")
                js("get('reason').value='Missing source browser check'; get('reject').click()")
                until(lambda: js("get('message').textContent.includes('\\ubc18\\ub824 \\uc644\\ub8cc')"))
                history = "[...document.querySelectorAll('#history li')].map(li=>li.textContent)"
                before = until(lambda: (rows if len(rows := js(history)) == 4 else None))
                assert any(" · 승인 · " in row and "Browser QA" in row for row in before)
                assert any(" · 반려 · " in row and "Missing source browser check" in row for row in before)

                marker = js("window.previousPage = true; performance.timeOrigin")
                with closing(sqlite3.connect(db)) as database:
                    tables = database.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                print("SQLite tables:", tables, flush=True)
                command("Page.reload", ignoreCache=True)
                until(lambda: js("!window.previousPage && performance.timeOrigin") not in (False, None, marker))
                after = until(lambda: (rows if len(rows := js(history)) == 4 else None))
                assert before == after, (before, after)
                assert js("performance.getEntriesByType('navigation')[0].type") == "reload"
                print(json.dumps({"browser": command("Browser.getVersion")["product"],
                                  "reload": True, "events": after}, ensure_ascii=True), flush=True)
                # Exercise question-driven generation through the actual browser UI.
                command('Page.navigate',url=f'http://127.0.0.1:{port}/housing-search')
                until(lambda: js("document.querySelector('#generate')?.disabled === false"))
                question='강도윤 청년 지원 예산은 얼마야?'
                js("document.querySelector('#question').value="+json.dumps(question)+";document.querySelector('#generate').click()")
                until(lambda: js("document.querySelector('#generated-article')?.hidden === false"))
                assert js("document.querySelector('#generated-sentences').textContent.includes('864억')")
                review_url=js("document.querySelector('#review-generated').getAttribute('href')")
                assert '?draft_id=' in review_url
                draft_id=review_url.split('draft_id=')[1]
                command('Page.reload',ignoreCache=True)
                until(lambda: js("[...document.querySelectorAll('#saved-drafts a')].some(a=>a.getAttribute('href')==="+json.dumps(review_url)+")"))
                command('Page.navigate',url=f'http://127.0.0.1:{port}'+review_url)
                until(lambda: js("document.querySelector('#fixture-controls')?.hidden && !document.querySelector('#approve').disabled"))
                assert js("document.querySelector('#review-question').textContent.includes("+json.dumps(question)+")")
                js("get('reviewer').value='Generated Browser QA'; get('review-key').value='browser-test-key'; get('approve').click()")
                until(lambda: js("get('message').textContent.includes('승인 완료')"))
                command('Page.reload',ignoreCache=True)
                until(lambda: js("document.querySelector('#message')?.textContent.includes('저장 상태: 승인')"))
                assert js("get('approve').disabled && get('reject').disabled")
                with closing(sqlite3.connect(db)) as database:
                    assert database.execute('SELECT status FROM ARTICLE WHERE article_id=?',(draft_id,)).fetchone()[0]=='approve'
                    assert database.execute('PRAGMA foreign_key_check').fetchall()==[]
                print(json.dumps({'generated_article':draft_id,'generation_reload':True,'generation_approval':True}),flush=True)
        except Exception:
            log.flush()
            print((directory / "chrome.log").read_text(errors="replace")[-1500:], flush=True)
            raise
        finally:
            if browser is not None and browser.poll() is None:
                browser.terminate()
                browser.wait(timeout=8)
            server.should_exit = True
            thread.join(timeout=6)

