# 台股分析專案

此專案示範如何透過程式定期下載台灣股市資料、進行簡單的數學模型分析，並將預測結果發布到 GitHub Pages 網站，最後再透過 Namecheap 連結自訂網域。

> **重要聲明**：本專案的程式僅作為教育用途示範，不能視為任何投資建議或保證。投資有風險，請自行評估後再作決定。本專案使用的模型十分簡化，僅示範如何從資料建立預測，請勿用於實際交易。

## 專案內容

* `fetch_and_predict.py`：用於從 FinMind API 下載台灣加權指數（TAIEX）、台積電（2330）及元大台灣50（0050）的日成交資料與融資融券資料，計算簡單特徵，建立邏輯回歸模型，並輸出預測結果 JSON 檔案。您需要註冊 [FinMind](https://finmindtrade.com/) 帳號並取得 `token` 後將其填入程式中才可提高 API 呼叫上限。
* `data/latest_predictions.json`：範例預測結果檔，包含每個商品最新一天的預測漲跌機率與預估價格區間。部署網站前可先用此檔案測試前端儀表板。
* `data/daily_data.csv`：範例歷史資料檔。若您自行執行 `fetch_and_predict.py`，此檔案將會被覆寫為最新資料。
* `index.html`、`style.css`、`script.js`：簡易的前端網頁，會在網頁載入時讀取 `data/latest_predictions.json`，並以儀表板方式顯示預測結果。

## 使用方式

### 1. 下載與分析資料

1. 安裝 Python 3.8+ 環境，並確保已安裝 `requests`、`pandas`、`numpy` 等套件（標準環境已內建）。
2. 註冊 [FinMind](https://finmindtrade.com/) 帳號並驗證電子郵件，取得 API token。
3. 編輯 `fetch_and_predict.py`，在 `TOKEN = ""` 的位置填入您的 API token。
4. 在終端機執行：

   ```bash
   python fetch_and_predict.py
   ```

   程式將會下載近一年的資料，訓練模型，並產生 `data/latest_predictions.json` 及 `data/daily_data.csv`。如果遇到 API 限制或無法存取，可以先使用已提供的範例資料，待您取得 token 後再重新產生。

### 2. 部署到 GitHub Pages

1. 在 GitHub 建立一個新的公開倉庫（假設為 `yourname/stock-dashboard`）。
2. 將 `taiwan_stock_analysis` 目錄中的所有檔案複製到倉庫根目錄，並提交 (`git add . && git commit -m 'init' && git push`)。
3. 進入 GitHub 倉庫頁面，點選 **Settings → Pages**。
4. 在 **Source** 欄位選擇 `main`（或您使用的分支）並設定資料夾為 `/`，儲存後 GitHub 會自動建置網站。稍待片刻後即可透過 `https://yourname.github.io/stock-dashboard/` 存取網站。

### 3. 設定自訂網域（Namecheap）

若您想使用在 Namecheap 購買的自訂網域連結到 GitHub Pages，需同時在 GitHub 與 Namecheap 設定：

#### GitHub 端設定

1. 前往倉庫 **Settings → Pages**。
2. 在 **Custom domain** 欄位輸入您的網域（例如 `example.com`），並點選 **Save**。GitHub 會自動在倉庫根目錄建立一個 `CNAME` 檔案，其內容即為該網域名稱。

#### Namecheap 端設定

1. 登入您的 Namecheap 帳號，在左側選單點選 **Domain List** 並找到要設定的網域，點選 **Manage**。
2. 切換到 **Advanced DNS** 分頁，在 **HOST RECORDS** 區塊新增或修改以下記錄：
   - 為頂級網域（`@`）建立四筆 **A 記錄**，分別指向 GitHub Pages 的 IPv4 位址 `185.199.108.153`、`185.199.109.153`、`185.199.110.153`、`185.199.111.153`，TTL 依預設即可【40005772208324†L124-L160】。
   - 若您希望同時支援 `www` 子網域，新增 **CNAME 記錄**：`Host` 填入 `www`，`Value` 填入您的 GitHub Pages 預設網域，例如 `yourname.github.io`【40005772208324†L232-L239】。
3. 移除 Namecheap 預設自動生成的 A 記錄（若存在），避免影響解析【40005772208324†L170-L172】。
4. DNS 變更可能需要數小時至一天才能完成傳播，耐心等待並檢查 `example.com` 與 `www.example.com` 是否能正確導向您的 GitHub Pages 網站。

#### 更多說明

GitHub 官方文件提供了完整的自訂網域設定指南，包括如何使用 `dig` 或其他工具確認 DNS 設定是否正確。若您需要更詳細的步驟，可以參考【40005772208324†L124-L167】。

## 設計理念

本專案的核心在於練習資料收集與簡單的統計建模，並把結果呈現在網頁上：

1. **資料收集**：透過 FinMind API 抓取台股的大盤與個股資料（收盤價、成交量、融資融券）。
2. **特徵工程**：計算每日報酬率、成交量增長比率、融資增減等簡單指標。
3. **模型建構**：使用邏輯回歸預測隔日漲跌機率，並以歷史報酬率估計可能的價格區間。由於資料量及模型複雜度有限，預測結果僅供參考。
4. **前端展示**：使用 HTML、CSS 及少量 JavaScript 建立儀表板，讀取 JSON 檔並動態更新漲跌機率與預估價位。

完成上述步驟後，您便可以免費地將自己的分析網站部署到 GitHub Pages，並用 Namecheap 連結自訂網域，建立屬於自己的股市分析網站。