# pip install undetected-chromedriver selenium
import csv, os, re, time, random
from pathlib import Path
from urllib.parse import quote_plus

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

HEADLESS = os.getenv("HEADLESS", "1") == "1"
TIMEOUT = int(os.getenv("TIMEOUT", "30"))
RETRIES = int(os.getenv("RETRIES", "2"))
SLEEP_BETWEEN = float(os.getenv("SLEEP_BETWEEN", "1.0"))

INPUT_FILE = "searches.csv"
OUTPUT_FILE = "list_sellers_number.csv"
URL_TMPL = "https://www.noon.com/uae-en/search/?q={q}"

XPATH_SORTBY = "//*[contains(., 'Sort By')]"
CSS_PRODUCT_NAME = "[data-qa='product-name']"  # маркер карточек
XPATH_RESULTS_ALL = "//div[contains(., 'Results for') and contains(@class,'DesktopListHeader')]"
RESULTS_RE = re.compile(r"(\d[\d,.\s]*)\s+Results", re.I)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " \
     "AppleWebKit/537.36 (KHTML, like Gecko) " \
     "Chrome/125.0.0.0 Safari/537.36"  # десктопный Chrome

def log(m): print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {m}", flush=True)

def build_driver():
    opts = uc.ChromeOptions()
    if HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--window-size=1366,900")
    opts.add_argument("--lang=en-US")
    opts.add_argument(f"--user-agent={UA}")
    drv = uc.Chrome(options=opts)
    log(f"User-Agent: {UA}")
    return drv

def parse_count(text: str) -> int:
    m = RESULTS_RE.search(text or "")
    if not m: return 0
    num = re.sub(r"[^\d]", "", m.group(1))
    return int(num) if num.isdigit() else 0

def pick_bottom_results_element(driver):
    # Собираем все узлы “Results for”, выбираем видимые и берём тот, что ниже всех по Y
    els = driver.find_elements(By.XPATH, XPATH_RESULTS_ALL)
    vis = [e for e in els if e.is_displayed()]
    if not vis: return None, []
    vis_with_y = [(e, e.location.get("y", 0)) for e in vis]
    vis_with_y.sort(key=lambda t: t[1])  # по возрастанию Y
    return vis_with_y[-1][0], [f"y={y} | {e.text.strip()!r}" for e, y in vis_with_y]

def fetch_count(driver, keyword: str, outdir: Path) -> int:
    from selenium.common.exceptions import TimeoutException
    url = URL_TMPL.format(q=quote_plus(keyword))
    log(f"Открываю: {url}")
    driver.get(url)

    # небольшой скролл, чтобы триггернуть ленивую отрисовку
    driver.execute_script("window.scrollTo(0, Math.floor(document.body.scrollHeight*0.25));")
    time.sleep(0.7)
    driver.execute_script("window.scrollTo(0, 0);")

    # 1) ждём маркер стабильности (Sort By)
    try:
        WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, XPATH_SORTBY))
        )
        log("Маркер 'Sort By' найден.")
    except TimeoutException:
        log(f"'Sort By' не найден за {TIMEOUT}s, продолжаю…")

    # 2) ждём карточки (не обязательно, но полезно)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, CSS_PRODUCT_NAME))
        )
        log("Карточки товара найдены.")
    except TimeoutException:
        log("Карточки не найдены в отведённое время — пытаюсь взять заголовок.")

    # 3) выбираем нижний видимый “Results for”
    el, dbg = pick_bottom_results_element(driver)
    for i, line in enumerate(dbg):
        log(f"Results[{i}] {line}")
    if el:
        txt = el.text.strip()
        cnt = parse_count(txt)
        log(f"Выбран нижний заголовок: {txt!r} -> {cnt}")
        if cnt > 0:
            return cnt

    # 4) fallback: парс по всей странице
    html = driver.page_source
    cnt = parse_count(html)
    if cnt > 0:
        log(f"Fallback по HTML: {cnt}")
        return cnt

    # 5) диагностика
    diag = outdir / "diagnostics"; diag.mkdir(exist_ok=True, parents=True)
    base = re.sub(r"[^a-zA-Z0-9._-]+", "_", keyword)[:60] + "_" + str(int(time.time()))
    png = diag / f"{base}.png"; htmlp = diag / f"{base}.html"
    try:
        driver.save_screenshot(str(png))
        htmlp.write_text(html, encoding="utf-8")
        log(f"Сохранены диагностика: {png} | {htmlp}")
    except Exception as e:
        log(f"Диагностика не сохранена: {e}")
    return 0

def load_keywords(path: Path):
    if not path.exists():
        path.write_text("keyword\n", encoding="utf-8"); return []
    rows = []
    with path.open("r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        if r.fieldnames and "keyword" in r.fieldnames:
            for row in r:
                kw = (row.get("keyword") or "").strip()
                if kw: rows.append(kw)
        else:
            f.seek(0)
            for i, row in enumerate(csv.reader(f)):
                if i == 0 and len(row) == 1 and row[0].lower() == "keyword": continue
                if row and row[0].strip(): rows.append(row[0].strip())
    return rows

def append_result(path: Path, keyword: str, sellers: int):
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new: w.writerow(["keyword", "sellers_number"])
        w.writerow([keyword, sellers])

def save_remaining(path: Path, queue: list):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["keyword"])
        for kw in queue: w.writerow([kw])

def main():
    script_dir = Path(__file__).parent.resolve()
    input_path = script_dir / INPUT_FILE
    output_path = script_dir / OUTPUT_FILE
    log(f"Script dir: {script_dir}")
    log(f"Файл входа: {input_path}")
    log(f"Файл выхода: {output_path}")

    keys = load_keywords(input_path)
    log(f"Загружено ключей: {len(keys)}")
    if not keys:
        log("Пусто — выхожу."); return

    driver = build_driver()
    try:
        remaining = list(keys)
        for kw in keys:
            got = None
            for attempt in range(1, RETRIES+2):
                try:
                    log(f"=== {kw} | попытка {attempt}/{RETRIES+1}")
                    got = fetch_count(driver, kw, script_dir)
                    break
                except Exception as e:
                    log(f"Ошибка: {e.__class__.__name__}: {e}")
                    time.sleep(1.5*attempt)
                    try: driver.quit()
                    except: pass
                    driver = build_driver()
            sellers = int(got or 0)
            append_result(output_path, kw, sellers)
            if kw in remaining: remaining.remove(kw)
            save_remaining(input_path, remaining)
            log(f"Сохранено: {kw} -> {sellers}")
            time.sleep(SLEEP_BETWEEN)
        log(f"Готово. Результаты: {output_path.resolve()}")
    finally:
        try: driver.quit()
        except: pass

if __name__ == "__main__":
    main()
