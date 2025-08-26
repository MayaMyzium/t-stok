# 加密貨幣與台股分析儀表板（無 data 版本）

本專案整合了兩個功能頁面：

1. **加密貨幣儀表板（index.html）** – 使用即時 API 顯示恐懼貪婪指數、指定比特幣地址餘額變化，以及多種加密貨幣（BTC、ETH、XRP、DOGE、ADA、SOL）的即時價格與 RSI 指標。
2. **永續合約分析頁（analysis.html）** – 統整幣安與 Bybit 永續合約的做多/做空比率、資金費率與情緒分數，並展示 CETS 與 TS 模型分析結果。頁面新增「台股預測摘要」區塊，根據每日 8:30 預測模型產生的資料顯示台股大盤、台積電（2330）與元大台灣50（0050）的上漲機率、下跌機率、預測價格區間及建議進出場點。

本版本取消了 `data/` 資料夾，預測資料直接置於根目錄：
* `latest_predictions_taiwan.json` – 每日早上預測結果（上漲機率、預測價等）。
* `realtime_taiwan.json` – 盤中每 10 分鐘更新的即時漲跌幅，供前端查看（僅在台股預測頁使用）。

您可使用 Python 腳本 `stock_dashboard.py` 產生上述 JSON 檔案，並覆蓋現有檔案以顯示最新資料。

## 部署步驟

1. **準備檔案**：本資料夾內應包含 `index.html`、`analysis.html`、`style.css`、`script.js`、`analysis.js`、`taiwan_summary.js`、`latest_predictions_taiwan.json`、`realtime_taiwan.json`、`stock_dashboard.py`、`README.md`，以及（可選）自訂網域用的 `CNAME` 檔案。
2. **上傳到 GitHub**：將所有檔案上傳至 GitHub 儲存庫根目錄，並提交 commit。您可以使用現有儲存庫，或建立新儲存庫。例如建立 `username.github.io` 儲存庫將會部署為使用者頁面，或在任何儲存庫啟用 Pages。
3. **啟用 GitHub Pages**：在儲存庫的 **Settings → Pages**，選擇 `main`（或您的分支）與根目錄，儲存後即可獲得網站網址（形如 `https://username.github.io/儲存庫名/`）。
4. **設定 Namecheap 網域（可選）**：
   - 若要使用自訂網域，如 `example.com`，在儲存庫根目錄建立 `CNAME` 檔案並填入您的網域。
   - 前往 Namecheap 控制台 → **Advanced DNS**，為您的網域新增四筆 **A 記錄**，指向 GitHub Pages 的 IP 位址：`185.199.108.153`、`185.199.109.153`、`185.199.110.153`、`185.199.111.153`【963741525815197†L3496-L3504】；再新增一筆 **CNAME 記錄**，將 `www` 指向 `username.github.io`。
5. **更新台股預測資料**：
   - 使用 `stock_dashboard.py` 產生新的 `latest_predictions_taiwan.json` 及 `realtime_taiwan.json`，執行方式可參考程式內說明（需安裝 yfinance 等套件）。
   - 將產生的 JSON 檔案覆蓋至儲存庫根目錄並提交，前端網站會自動載入最新資料。

## 注意事項

* 本網站所呈現的所有分析與預測僅供學術研究與學習參考，並不構成任何投資建議。
* 加密貨幣資料來自公共 API，即時更新；台股預測則依賴預先生成的 JSON 檔案。