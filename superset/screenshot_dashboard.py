"""Dashboard sekmelerinin ekran görüntülerini docs/ altına kaydeder (Playwright, headless Chromium)."""
import pathlib, sys, time
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "docs"
BASE = "http://127.0.0.1:8088"
env = dict(l.split("=", 1) for l in (HERE / ".env").read_text().split() if "=" in l)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1600, "height": 1000})
    pg.goto(f"{BASE}/login/")
    pg.fill("input[name=username]", env["ADMIN_USERNAME"])
    pg.fill("input[name=password]", env["ADMIN_PASSWORD"])
    pg.click("input[type=submit], button[type=submit]")
    pg.wait_for_load_state("networkidle")
    pg.goto(f"{BASE}/superset/dashboard/dc-planning/?standalone=1")
    pg.wait_for_load_state("networkidle"); time.sleep(6)
    tabs = pg.locator("div[role=tab]")
    n = tabs.count()
    print("tabs:", n)
    for i, name in enumerate(["01_genel_bakis", "02_depo_yerlesimi", "03_magaza_sevkiyati", "04_lojistik_agi"][:max(n, 1)]):
        if n:
            tabs.nth(i).click(); time.sleep(7)
        pg.screenshot(path=str(OUT / f"dashboard_{name}.png"), full_page=True)
        print("saved", OUT / f"dashboard_{name}.png")
    b.close()
