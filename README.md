# iPhone 基金監控 App V2

## 手機部署
1. 登入 GitHub，建立公開 repository `fund-monitor`，不勾選 README。
2. 在 GitHub 網頁的 Add file > Upload files 上傳 `index.html`、`quotes.json`、`update_quotes.py`、`README.md`。GitHub 網頁上傳不一定保留隱藏資料夾，請另外建立 `.github/workflows/pages.yml` 並貼上壓縮檔中的內容，或用 GitHub 桌面版 / git 上傳整個資料夾。
3. Settings > Pages > Build and deployment > Source 選 GitHub Actions。
4. Actions 頁面執行「基金監控網站與每日檢查」。
5. 網址預計為 `https://ananchen-520.github.io/fund-monitor/`（成功部署後才生效）。用 Safari 開啟並選分享 > 加入主畫面。

## 更新機制
- GitHub Actions 每天台灣時間 21:17 執行檢查並重新部署網站；排程可能延遲，公開儲存庫閒置 60 天可能停用排程。
- App 開啟及返回前景時，從 `./quotes.json` 讀取；開啟期間每小時再檢查。
- **目前沒有經驗證的官方基金 NAV API。排程僅更新檢查紀錄，不會虛構基金價格。** `updatedAt` 只有在真正有新淨值時才應改變。
- 基金持倉和成本保存在 iPhone 瀏覽器本機儲存空間，不會由本專案上傳到 GitHub。不要把私人持倉資料提交到公開 repository。
- 原生 iOS Widget 需要後續以 SwiftUI WidgetKit 開發並簽署安裝；GitHub Pages 本身無法提供原生桌面小工具。
