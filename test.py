import colorsys
import json
import os
import re
import urllib.parse
from playwright.sync_api import sync_playwright

# ============================================================
# 1. CẤU HÌNH DANH SÁCH & ĐƯỜNG DẪN
# ============================================================
# Danh sách chữ cần cào (đang để mẫu chữ "月", sau này bạn thêm chữ tùy thích)
KANJI_LIST = ["月"]

# Thư mục xuất file kết quả (lưu cùng thư mục hoặc folder riêng để check)
OUTPUT_DIR = "./test_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Đường dẫn file json màu
JSON_COLOR_PATH = "./kanji_colors.json"


def load_kanji_colors():
    """Đọc file kanji_colors.json nếu tồn tại."""
    if os.path.exists(JSON_COLOR_PATH):
        try:
            with open(JSON_COLOR_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Lỗi đọc file {JSON_COLOR_PATH}: {e}")
    return {}


def get_fallback_color(idx, total):
    """Màu Spectrum dự phòng nếu trong JSON chưa có chữ đó."""
    h = idx / max(1, total)
    r, g, b = colorsys.hsv_to_rgb(h, 0.95, 0.75)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


# ============================================================
# 2. HÀM DỰNG NỘI DUNG FILE SVG (CHUẨN BẢN MẪU VÀNG)
# ============================================================
def build_svg(kanji_char, strokes):
    timeline = []
    paths = []
    badges = []

    for s in strokes:
        idx = s["idx"]
        len_val = f"{s['length']:.4f}"

        # Timeline riêng của chữ
        timeline.append(
            f'#{kanji_char}-bg{idx} {{ animation-delay: {s["bg_delay"]:.2f}s; }}'
        )
        timeline.append(
            f'#{kanji_char}-s{idx}  {{ stroke-dasharray: {len_val}; stroke-dashoffset: {len_val}; animation: drawStroke {s["duration"]:.2f}s ease-out {s["stroke_delay"]:.2f}s forwards; }}'
        )

        # Thẻ nét vẽ
        paths.append(
            f'<path id="{kanji_char}-s{idx}" class="stroke" stroke="{s["color"]}" d="{s["d"]}"/>'
        )

        # Thẻ bóng số: x, y ra trước, dx, dy ra sau, bán kính chuẩn r="3.5"
        if idx < 10:
            badges.append(
                f'<g id="{kanji_char}-bg{idx}"  class="badge-group"><circle cx="{s["x"]}" cy="{s["y"]}" r="3.5" fill="{s["color"]}"/><text class="num-single" x="{s["x"]}" y="{s["y"]}" dx="0" dy="-0.5">{idx}</text></g>'
            )
        else:
            badges.append(
                f'<g id="{kanji_char}-bg{idx}" class="badge-group"><circle cx="{s["x"]}" cy="{s["y"]}" r="3.5" fill="{s["color"]}"/><text class="num-double" x="{s["x"]}" y="{s["y"]}" dx="-0.4" dy="-0.475">{idx}</text></g>'
            )

    timeline_str = "\n".join(timeline)
    paths_str = "\n".join(paths)
    badges_str = "\n".join(badges)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg height="100%" version="1.1" width="100%" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 110 110" style="background:#181a1f; border-radius:16px;">
<style type="text/css"><![CDATA[
/* ============================================================
   BẢNG CHỈ DẪN THÔNG SỐ ĐIỀU CHỈNH ({kanji_char})
   ============================================================ */

/* 1. HIỆU ỨNG VẼ NÉT & HIỆN SỐ */
@keyframes drawStroke {{
    0%   {{ opacity: 1; }}
    100% {{ stroke-dashoffset: 0; opacity: 1; }}
}}

@keyframes softFade {{
    from {{ opacity: 0; }}
    to   {{ opacity: 1; }}
}}

/* 2. ĐƯỜNG LƯỚI CHỮ THẬP NỀN (Màu xám tối, nét đứt 4-2) */
.grid-cross {{
    stroke: #2d333b;
    stroke-width: 0.6;
    stroke-dasharray: 4, 2;
}}

/* 3. NÉT VẼ BÚT THUẬN:
   - stroke-width: Độ dày nét bút (2.8 là chuẩn thanh mảnh)
   - opacity: 0 để triệt tiêu lỗi chấm đầu nét lúc chưa vẽ */
.stroke {{
    stroke-width: 2.8 !important;
    stroke-linecap: round !important;
    stroke-linejoin: round !important;
    fill: none;
    opacity: 0;
}}

/* 4. HIỆU ỨNG HIỆN QUẢ BÓNG */
.badge-group {{
    opacity: 0;
    animation: softFade 0.2s ease-out forwards;
}}

/* 5. ĐỊNH DẠNG SỐ 1 CHỮ SỐ (1-9): */
.num-single {{
    font-family: "Segoe UI", -apple-system, sans-serif, "Arial Narrow", "Roboto Condensed";
    font-size: 7.6px !important;
    font-weight: 375 !important;
    font-style: normal !important;
    fill: #ffffff !important;
    text-anchor: middle;
    dominant-baseline: central;
}}

/* 5. ĐỊNH DẠNG SỐ 2 CHỮ SỐ (10-14): */
.num-double {{
    font-family: "Segoe UI", -apple-system, sans-serif, "Arial Narrow", "Roboto Condensed";
    font-size: 6.5px !important;
    font-weight: 375 !important;
    font-style: normal !important;
    letter-spacing: -0.35px !important;
    fill: #ffffff !important;
    text-anchor: middle;
    dominant-baseline: central;
}}

/* ============================================================
   TIMELINE ĐIỀU KHIỂN THỜI GIAN:
   ============================================================ */
{timeline_str}
]]>
</style>

<!-- LƯỚI CHỮ THẬP CỐ ĐỊNH -->
<path class="grid-cross" d="M55,0 L55,110" /><path class="grid-cross" d="M0,55 L110,55" />

<!-- {len(strokes)} ĐƯỜNG NÉT VẼ (QUY TẮC ID SCOPING: #{kanji_char}-s[i]) -->
{paths_str}

<!-- {len(strokes)} QUẢ BÓNG CHỨA SỐ -->
{badges_str}
</svg>"""


# ============================================================
# 3. HÀM DỰNG NỘI DUNG FILE MARKDOWN (.md)
# ============================================================
def build_md(meta):
    jlpt_lower = meta["jlpt"].lower() if meta["jlpt"] else "n5"

    return f"""---
kanji: {meta['kanji']}
han_viet: {meta['han_viet']}
jlpt: {meta['jlpt']}
so_net: {meta['so_net']}
bo_thu: ""
luc_thu: ""
on: {meta['on']}
kun: {meta['kun']}
nghia: {meta['nghia']}
tags:
  - kanji/{jlpt_lower}
  - luc-thu
order: {meta['order']}
do_thong_dung: {meta['do_thong_dung']}
---

```dataviewjs
await eval(await app.vault.adapter.read(`${{app.vault.configDir}}/scripts/kanji-view.js`));
```

---

### 1. Chiết tự & Nguồn gốc (Lục thư)

---

### 2. Từ vựng ghép quan trọng
"""


# ============================================================
# 4. HÀM CÀO MAZII & BÓC TÁCH DỮ LIỆU
# ============================================================
def crawl_kanji(page, kanji_char, order_num, kanji_colors):
    encoded = urllib.parse.quote(kanji_char)
    url = f"https://mazii.net/vi-VN/search/kanji/javi/{encoded}"
    print(f"\n=======================================================")
    print(f"🔍 BẮT ĐẦU CÀO CHỮ: '{kanji_char}' (Thứ tự: {order_num})...")

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=25000)

        # Chờ container chính của Mazii xuất hiện
        page.wait_for_selector(".kanji-main-infor", timeout=15000)

        # Lấy số nét từ giao diện trước để biết chính xác số lượng path cần đợi
        so_net_text = page.evaluate("""() => {
            const titles = Array.from(document.querySelectorAll('.item-title, h2'));
            const strokeTitle = titles.find(t => t.textContent.includes('Số nét'));
            if (strokeTitle && strokeTitle.parentElement) {
                const info = strokeTitle.parentElement.querySelector('.item-infor');
                return info ? info.textContent.trim() : null;
            }
            return null;
        }""")
        expected_strokes = int(so_net_text) if so_net_text and so_net_text.isdigit() else 0

        # Đợi các nét vẽ xuất hiện đầy đủ trong DOM
        if expected_strokes > 0:
            page.wait_for_function(
                f"""() => {{
                const paths = document.querySelectorAll('svg.dmak-svg path');
                return paths.length >= {expected_strokes + 2};
            }}""",
                timeout=15000,
            )
        else:
            page.wait_for_selector("svg.dmak-svg path", state="attached", timeout=15000)
            page.wait_for_timeout(1500)

    except Exception as e:
        print(f"❌ Không tải được thông tin Mazii cho chữ '{kanji_char}': {e}")
        return

    # Trích xuất toàn bộ dữ liệu từ DOM của Mazii theo đúng ảnh F12
    data = page.evaluate("""() => {
        const root = document.querySelector('.kanji-main-infor');
        if (!root) return null;

        // 1. Hán Việt: Lấy sạch text trong thẻ han-viet-word
        const hvElem = root.querySelector('.han-viet-word');
        let han_viet = "";
        if (hvElem) {
            han_viet = hvElem.textContent.replace(/[\\r\\n]+/g, ' ').trim().toUpperCase();
        }

        // 2. Kunyomi: Lấy các thẻ span tiếng Nhật trong item-infor-kun
        const kunSpans = Array.from(root.querySelectorAll('.item-infor-kun .japanese-char, .item-infor-kun .txt-kun'));
        const kun = kunSpans.map(s => s.textContent.trim()).filter(Boolean).join(', ');

        // 3. Onyomi: Lấy các thẻ span tiếng Nhật trong item-infor-on
        const onSpans = Array.from(root.querySelectorAll('.item-infor-on .japanese-char'));
        const on = onSpans.map(s => s.textContent.trim()).filter(t => t && t !== ';' && t !== ',').join(', ');

        // 4. Số nét, JLPT, Tần suất (độ thông dụng)
        let so_net = 0;
        let jlpt = "N5";
        let do_thong_dung = "";

        const lineItems = Array.from(root.querySelectorAll('.line-item'));
        lineItems.forEach(item => {
            const title = item.querySelector('.item-title')?.textContent || "";
            const info = item.querySelector('.item-infor')?.textContent || "";

            if (title.includes("Số nét")) {
                so_net = parseInt(info.trim(), 10) || 0;
            } else if (title.includes("JLPT")) {
                jlpt = info.trim();
            } else if (title.includes("Tần suất")) {
                const match = info.match(/#?(\\d+)/);
                if (match) do_thong_dung = match[1];
            }
        });

        // 5. Nghĩa: Chỉ lấy phần text ngay sau marker, bỏ phần 'VD:'
        const meanLis = Array.from(root.querySelectorAll('.item-infor-mean li'));
        const meanings = [];
        meanLis.forEach(li => {
            let text = "";
            for (const node of li.childNodes) {
                if (node.nodeType === Node.TEXT_NODE) {
                    const t = node.textContent.trim();
                    if (t && !t.startsWith("VD:") && !t.startsWith("::marker")) {
                        text = t;
                        break;
                    }
                }
            }
            if (!text) {
                text = li.textContent.replace('::marker', '').split(/VD:|VD\\s*:/i)[0].trim();
            }
            if (text && !/[\u3040-\u30ff\u4e00-\u9faf]/.test(text) && !meanings.includes(text)) {
                meanings.push(text);
            }
        });
        const nghia = meanings.join(', ');

        // 6. Trích xuất đường nét SVG và độ dài 4 số thập phân
        const svg = root.querySelector('svg.dmak-svg');
        const paths = [];
        if (svg) {
            const allPaths = Array.from(svg.querySelectorAll('path')).filter(p => {
                const d = p.getAttribute('d') || '';
                return !d.startsWith('M55,0') && !d.startsWith('M0,55');
            });

            allPaths.forEach((p, idx) => {
                const d = p.getAttribute('d');
                let length = 50.0;
                
                // Lấy độ dài từ stroke-dasharray của Mazii
                const styleStr = p.getAttribute('style') || '';
                const dashMatch = styleStr.match(/stroke-dasharray:\\s*([0-9.]+)/);
                if (dashMatch) {
                    length = parseFloat(dashMatch[1]);
                } else {
                    try { length = p.getTotalLength(); } catch(e) {}
                }

                // Tọa độ đầu nét
                const mMatch = d.match(/^[Mm]\\s*([0-9.]+)[,\\s]+([0-9.]+)/);
                const startX = mMatch ? parseFloat(mMatch[1]) : 55.0;
                const startY = mMatch ? parseFloat(mMatch[2]) : 55.0;

                paths.push({ d, length, startX, startY });
            });
        }

        return {
            han_viet, kun, on, so_net, jlpt, do_thong_dung, nghia, paths
        };
    }""")

    if not data or not data["paths"]:
        print(f"❌ Không trích xuất được dữ liệu của '{kanji_char}'!")
        return

    # Lấy màu từ file kanji_colors.json (nếu có), không thì dùng màu quang phổ dự phòng
    preset_colors = kanji_colors.get(kanji_char, [])
    total_strokes = len(data["paths"])

    strokes = []
    current_time = 0.05

    for idx, p in enumerate(data["paths"], start=1):
        color = (
            preset_colors[idx - 1]
            if idx - 1 < len(preset_colors)
            else get_fallback_color(idx - 1, total_strokes)
        )
        duration = round(min(0.55, max(0.22, p["length"] * 0.0055)), 2)

        strokes.append(
            {
                "idx": idx,
                "d": p["d"],
                "color": color,
                "length": round(p["length"], 4),
                "x": round(p["startX"], 2),
                "y": round(p["startY"], 2),
                "bg_delay": round(current_time, 2),
                "stroke_delay": round(current_time + 0.13, 2),
                "duration": duration,
            }
        )
        current_time += duration + 0.15

    # Tự động chống đè bóng (< 7px)
    for j in range(len(strokes) - 1):
        for k in range(j + 1, len(strokes)):
            dist = (
                (strokes[j]["x"] - strokes[k]["x"]) ** 2
                + (strokes[j]["y"] - strokes[k]["y"]) ** 2
            ) ** 0.5
            if dist < 7.0:
                strokes[j]["y"] = round(strokes[j]["y"] - 3.5, 2)
                strokes[k]["y"] = round(strokes[k]["y"] + 3.5, 2)

    # 1. Ghi file SVG
    svg_data = build_svg(kanji_char, strokes)
    svg_file = os.path.join(OUTPUT_DIR, f"{kanji_char}.svg")
    with open(svg_file, "w", encoding="utf-8") as f:
        f.write(svg_data)

    # 2. Ghi file Markdown (.md)
    meta = {
        "kanji": kanji_char,
        "han_viet": data["han_viet"],
        "jlpt": data["jlpt"],
        "so_net": data["so_net"] or total_strokes,
        "on": data["on"],
        "kun": data["kun"],
        "nghia": data["nghia"],
        "order": order_num,
        "do_thong_dung": data["do_thong_dung"],
    }
    md_data = build_md(meta)
    md_file = os.path.join(OUTPUT_DIR, f"{kanji_char}.md")
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(md_data)

    print(f"✅ ĐÃ TẠO XONG 2 FILE:")
    print(f"   📄 Markdown: {md_file}")
    print(f"   🎨 Vector  : {svg_file}")
    print(
        f"   📌 Metadata: Hán Việt: {meta['han_viet']} | JLPT: {meta['jlpt']} | Nét: {meta['so_net']} | Tần suất: {meta['do_thong_dung']}"
    )
    print(f"   📖 Ý nghĩa : {meta['nghia']}")


# ============================================================
# 5. CHẠY CHƯƠNG TRÌNH
# ============================================================
def main():
    print(f"🚀 BẮT ĐẦU QUY TRÌNH CÀO TỰ ĐỘNG CHO: {KANJI_LIST}")

    kanji_colors = load_kanji_colors()
    if kanji_colors:
        print(
            f"🎨 Đã nạp thành công file '{JSON_COLOR_PATH}' ({len(kanji_colors)} chữ có màu sẵn)!"
        )
    else:
        print(f"ℹ️ Không tìm thấy {JSON_COLOR_PATH}, sẽ dùng dải màu Spectrum tự động.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for index, char in enumerate(KANJI_LIST, start=1):
            crawl_kanji(page, char, index, kanji_colors)

        browser.close()

    print(f"\n🎉 HOÀN THÀNH TẤT CẢ! Kiểm tra thư mục: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()