# 실행: python3 tests/cta_tracking_test.py .   (Chrome·playwright 필요)
"""랜딩 페이지 CTA 노출·클릭 수집 테스트.
Amplitude 전송 요청은 가로채서(실제 프로젝트에 쌓이지 않게) 내용만 검사한다."""
import gzip, json, subprocess, sys, time, collections
from playwright.sync_api import sync_playwright

ROOT = sys.argv[1]; PORT = 8765
srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "-d", ROOT], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
URL = f"http://localhost:{PORT}/baemin_landing.html?utm_source=qa_test&seg=winback"
MUA = "Mozilla/5.0 (Linux; Android 14; SM-S921N) AppleWebKit/537.36 Chrome/126 Mobile Safari/537.36"

def run(p, name, viewport, mobile, actions):
    sent = []
    b = p.chromium.launch(channel="chrome")
    ctx = b.new_context(viewport=viewport, is_mobile=mobile, has_touch=mobile, user_agent=MUA if mobile else None)
    def amp(route):
        try:
            raw = route.request.post_data_buffer or b"{}"
            if raw[:2] == b"\x1f\x8b": raw = gzip.decompress(raw)
            body = json.loads(raw)
            sent.extend(body.get("events", []))
        except Exception: pass
        route.fulfill(status=200, content_type="application/json", body='{"code":200,"events_ingested":1}')
    ctx.route("**/api2.amplitude.com/**", amp)
    ctx.route("**/api-sr.amplitude.com/**", lambda r: r.fulfill(status=200, body="{}"))
    ctx.route("**/apps.apple.com/**", lambda r: r.fulfill(status=200, body="APP STORE"))
    ctx.route("**/play.google.com/**", lambda r: r.fulfill(status=200, body="PLAY STORE"))
    pg = ctx.new_page(); pg.goto(URL); pg.wait_for_timeout(2500)
    actions(pg)
    pg.wait_for_timeout(2500)
    b.close()
    imp = collections.Counter(e["event_properties"]["cta_id"] for e in sent if e["event_type"] == "cta_impression")
    clk = collections.Counter(e["event_properties"]["cta_id"] for e in sent if e["event_type"] == "cta_click")
    sample = next((e["event_properties"] for e in sent if e["event_type"] == "cta_click"), None)
    return imp, clk, sample

def scroll_all(pg):
    h = pg.evaluate("document.documentElement.scrollHeight")
    y = 0
    while y < h:
        y += 350; pg.mouse.wheel(0, 350); pg.wait_for_timeout(1300)

def mobile_actions(pg):
    scroll_all(pg)
    pg.click("[data-cta=invite_share]"); pg.wait_for_timeout(500)
    pg.evaluate("window.scrollTo(0, 2500)"); pg.wait_for_timeout(1500)
    pg.click("[data-cta=sticky_bar]")   # 스토어로 이동

def desktop_actions(pg):
    scroll_all(pg)
    pg.evaluate("window.scrollTo(0, 0)"); pg.wait_for_timeout(500)
    pg.click("[data-cta=header_install]"); pg.wait_for_timeout(1600)   # QR 모달 → 노출
    with pg.context.expect_page():
        pg.click("[data-cta=modal_store_ios]")

EXPECT = {
  "mobile": {"imp": {"header_install","hero_main","benefits_all","coupon_claim","club_trial","invite_share","invite_signup","final_main","sticky_bar"},
             "never": {"hero_qr","hero_store_ios","hero_store_android","modal_qr","modal_store_ios","modal_store_android"},
             "clk": {"invite_share","sticky_bar"}},
  "desktop": {"imp": {"header_install","hero_qr","hero_store_ios","hero_store_android","benefits_all","coupon_claim","club_trial","invite_share","invite_signup","final_main","modal_qr","modal_store_ios","modal_store_android"},
              "never": {"hero_main","sticky_bar"},
              "clk": {"header_install","modal_store_ios"}},
}
ok = True
with sync_playwright() as p:
    for name, vp, mob, act in [("mobile", {"width": 412, "height": 915}, True, mobile_actions),
                               ("desktop", {"width": 1440, "height": 900}, False, desktop_actions)]:
        imp, clk, sample = run(p, name, vp, mob, act)
        ex = EXPECT[name]
        missing = ex["imp"] - set(imp); wrong = ex["never"] & set(imp)
        dup = {k: v for k, v in imp.items() if v > 1}; miss_clk = ex["clk"] - set(clk)
        print(f"\n[{name}] 노출 {sum(imp.values())}건: {dict(sorted(imp.items()))}")
        print(f"[{name}] 클릭 {sum(clk.values())}건: {dict(clk)}")
        print(f"[{name}] 클릭 이벤트 속성 예시: {sample}")
        for label, bad in [("노출 누락", missing), ("보이지 않는 CTA 노출", wrong), ("노출 중복", dup), ("클릭 누락", miss_clk)]:
            print(f"  {'FAIL' if bad else 'PASS'} {label}: {bad or '-'}")
            ok &= not bad
srv.terminate()
print("\n결과:", "모두 통과" if ok else "실패 항목 있음")
