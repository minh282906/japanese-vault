// ============================================================
// FILE: .obsidian/scripts/kanji-view.js
// ============================================================

(async () => {
  // 1. Tự động lấy dữ liệu từ Frontmatter của file hiện tại
  const current = dv.current();
  const kanji = current.kanji || current.file.name;
  const strokeCount = current.strokes || 14;
  const hanviet = current.han_viet || "HÁN VIỆT";
  const meaning = current.nghia || "";
  const onReading = current.on || "";
  const kunReading = current.kun || "";

  // 2. Tìm chính xác file SVG theo tên chữ Hán trong toàn bộ Vault
  const targetName = `${kanji}.svg`;
  const file = app.vault.getFiles().find((f) => f.name === targetName);

  if (!file) {
    dv.el("div", `⚠️ Không tìm thấy file: ${targetName} trong thư mục.`);
    return;
  }

  // 3. Đọc nội dung file SVG
  const svgContent = await app.vault.read(file);

  // 4. Render giao diện Sugedict
  const root = dv.el("div", "");
  root.innerHTML = `
    <div class="kanji-hero">
    <details class="kanji-popup-container">
    <summary class="kanji-box-trigger"><span class="kanji-char">${kanji}</span></summary>
    <div class="sugedict-modal">
      <div style="font-size: 1.25rem; font-weight: 700; color: #ffffff;">${kanji} (${strokeCount} NÉT)</div>
      <div class="sugedict-canvas"></div>
      <div class="sugedict-switches">
        <details id="sw-color" class="switch-toggle" open>
          <summary class="switch-item">
            <span>Hiện màu</span>
            <div class="toggle-pill"><div class="toggle-knob"></div></div>
          </summary>
        </details>
        <details id="sw-strokes" class="switch-toggle" open>
          <summary class="switch-item">
            <span>Hiện nét</span>
            <div class="toggle-pill"><div class="toggle-knob"></div></div>
          </summary>
        </details>
      </div>
    </div>
    </details>

    <div class="kanji-info">
      <div class="kanji-hv-title">${hanviet}</div>
      <div class="kanji-quick-meaning">${meaning}</div>
      <div class="kanji-readings-inline">
        <div><b>音:</b> ${onReading}</div>
        <div><b>訓:</b> ${kunReading}</div>
      </div>
    </div>
    </div>
    `;

  const canvas = root.querySelector(".sugedict-canvas");
  const popup = root.querySelector(".kanji-popup-container");

  function renderFresh() {
    if (!canvas) return;
    canvas.innerHTML = svgContent;
  }

  // A. Thoát ra vào lại: Xóa sạch khi đóng, mở ra mới vẽ (Chống chớp hình cũ)
  if (popup) {
    popup.addEventListener("toggle", () => {
      if (popup.open) {
        renderFresh();
      } else {
        canvas.innerHTML = "";
      }
    });
  }

  // B. Bấm vào giữa Canvas: Vẽ lại từ Nét 1
  if (canvas) {
    canvas.addEventListener("click", () => {
      renderFresh();
    });
  }

  // C. Đổi công tắc: Xóa sạch ngay lúc click (Chống giật màu)
  const switches = root.querySelectorAll(".switch-toggle");
  switches.forEach((sw) => {
    const item = sw.querySelector(".switch-item");
    if (item) {
      item.addEventListener("click", () => {
        canvas.innerHTML = "";
      });
    }
    sw.addEventListener("toggle", () => {
      renderFresh();
    });
  });
})();
