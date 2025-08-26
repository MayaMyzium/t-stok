# 虛擬貨幣資訊儀表板部署指南

這個資料夾包含一個簡易的前端網站，可透過 GitHub Pages 免費部署並綁定到您的 Namecheap 網域。網站提供以下功能：

1. **恐懼貪婪指數** – 從 Alternative.me 的 API 取得最新值，並顯示分類。此指數取值 0（極度恐慌）至 100（極度貪婪），可用來觀察市場情緒【762950707989567†L59-L79】。我們同時載入一張官方提供的即時圖片作為備用顯示。
2. **比特幣地址餘額折線圖** – 使用 BlockCypher 地址端點取得歷史交易，將每日的 `ref_balance` (交易後餘額) 轉為 BTC 並繪製折線圖。BlockCypher 的 API 最多可一次取得 2,000 筆交易，若交易數很多，可使用 `before` 參數分頁【963741525815197†L3496-L3504】。範例中顯示 8 個地址及第 3 至 8 個地址的餘額總和圖。
3. **即時價格與 RSI** – 透過 Binance 公共 API 取得每日 K 線資料計算 14 日 RSI。RSI 屬於動能振盪指標，通常 70 以上代表過熱、可能面臨回調，30 以下代表超賣、可能反彈【800268421240992†L375-L393】。此區域亦顯示即時價格並給出簡單建議。
4. **永續合約多空比** – 在進一步分析頁面中，調用 Binance 的 `globalLongShortAccountRatio` 端點，顯示多空倉位比率並提供簡短分析【754820992736042†L82-L106】。

## 部署到 GitHub Pages

1. 登入你的 GitHub 帳號，建立一個新的儲存庫。若想使用使用者頁面，可將儲存庫命名為 `你的帳號.github.io`，或者用其他名稱建立專案頁面。
2. 將本資料夾內的所有檔案（包含 `index.html`、`analysis.html`、`styles.css`、`script.js`、`taiwan.html`、`taiwan.js`、`taiwan_summary.js`、各 `.json` 資料檔、Python 腳本等）上傳至儲存庫的根目錄。**此版本已將所有預測檔案移至專案根目錄，不再使用 `data/` 資料夾。**
3. （建議）新增一個 `CNAME` 檔案，內容填入你在 Namecheap 購買的自訂網域，例如：

   ```
   example.com
   ```

4. 將檔案推送到 GitHub 之後，前往儲存庫的 **Settings → Pages**，在 **Source** 選擇 `main` 分支和 `/(root)` 資料夾。儲存後稍待片刻，GitHub 會自動建置你的網站。

5. 開啟 `https://你的帳號.github.io` 或你的儲存庫子頁面網址，即可看到儀表板。若您在根目錄加入了 `CNAME`，GitHub Pages 會自動使用該網域。

## Namecheap 網域設定

1. 登入 Namecheap，找到您的網域並進入 **Advanced DNS**。新增或編輯以下 DNS 記錄，使其指向 GitHub Pages：
   * **A 記錄**：將 `@` 指向 GitHub 的 IP 位址（例如 `185.199.108.153`、`185.199.109.153`、`185.199.110.153`、`185.199.111.153`，至少需設定一條）。
   * **CNAME 記錄**：將 `www` 或子域名指向 `你的帳號.github.io`。
2. 確保 GitHub 儲存庫的 `Settings → Pages` 中自訂網域填寫與 DNS 設定一致，並啟用 HTTPS（如有選項）。等待 DNS 生效後，輸入你的網域即可訪問網站。

## 自訂與更新資料

* **修改監控的比特幣地址**：在 `script.js` 中的 `addresses` 陣列加入或修改 `addr` 及 `label` 即可。網站會自動調用 BlockCypher API 重新繪製圖表。
* **新增加密貨幣**：在 `script.js` 中的 `coins` 陣列加上新的交易對（例如 `BNBUSDT`），程式會嘗試從 Binance API 取得資料並計算 RSI。
* **合約分析**：進階分析頁面只顯示 Binance 的多空比。OKX API 在部分地區可能無法存取；若需要，可參考 OKX 官方文件自行增添呼叫邏輯。
* **改良信號腳本**：本專案另附 <code>advanced_analysis.py</code>，實作一套可落地交易的多空比分析公式。您可以將自己的時間、開高低收、成交量與多空比資料整理為 CSV，導入該腳本計算綜合指標 <code>S</code> 與 <code>S^*</code>、進場價、止損點及建議部位大小。詳細範例和使用方法請參考 <code>analysis.html</code> 的說明。

## 台股預測儀表板

除了虛擬貨幣資訊外，本專案也提供一個台股預測模組，可分析台灣加權指數（TAIEX）、台積電（2330）和元大台灣50（0050）的漲跌機率與目標區間。

1. **資料來源與模型** – 使用 FinMind API 下載過去一年的日 K 線、成交量以及融資融券資料，計算報酬率、成交量比率與融資變化率等特徵。模型採用簡易的邏輯迴歸（可加入美股指數如 S&P 500 的前一日報酬率作為全球因子），預測隔日上漲機率【568328348583858†screenshot】。

2. **每日 08:30 更新** – Python 腳本 `fetch_and_predict_taiwan.py` 於每天台灣時間 08:30 執行，下載最新資料、重訓模型並輸出預測到 `latest_predictions_taiwan.json`（檔案位於專案根目錄）。該 JSON 包含每個標的的上漲機率、下跌機率、預測價格區間以及建議多單/空單進場點。

3. **開盤後即時更新** – 同一腳本可以於開盤後每 10 分鐘執行 `--mode intraday`，更新當日最新價格與漲跌幅，計算當前多空點位並寫入 `realtime_taiwan.json`（同樣位於專案根目錄）。前端頁面會自動讀取並刷新。

4. **前端介面** – 新增 `taiwan.html` 和 `taiwan.js` 兩個檔案：
   * `taiwan.html` 提供每日預測表格與即時價格表格，並說明模型假設與資料來源。
   * `taiwan.js` 在 `taiwan.html` 中載入，頁面載入時讀取 `latest_predictions_taiwan.json` 與 `realtime_taiwan.json`（根目錄檔案），填入表格並每 10 分鐘更新一次即時資料。
   * 在 `analysis.html` 中新增 `taiwan-summary.js` 及 `<section id="taiwan-summary">`，用於讀取當日 `latest_predictions_taiwan.json` 以摘要方式呈現台股預測，方便在進一步分析頁面快速查看。

5. **連結整合** – 在首頁 `index.html` 增加「台股預測儀表板」區塊，提供連結至 `taiwan.html`。這樣從虛擬貨幣儀表板即可點擊進入台股分析頁面。

### 執行腳本

首先註冊 FinMind 並取得 API Token，將其填入 `fetch_and_predict_taiwan.py`（例如將 `FINMIND_TOKEN` 環境變數設為您的 token）。安裝相依套件，例如 `numpy`、`pandas`、`requests`，以及若需要全球市場資料則安裝 `yfinance`。

每天可用 cron 或 GitHub Actions 執行：

```
# 早上 8:30 更新昨日預測
python fetch_and_predict_taiwan.py --mode daily

# 開盤後每 10 分鐘更新即時資料
python fetch_and_predict_taiwan.py --mode intraday
```

執行結果會在專案根目錄生成 `latest_predictions_taiwan.json` 和 `realtime_taiwan.json`，前端頁面將自動顯示最新資料。本版本不包含 `data` 資料夾，請確保 JSON 檔案直接位於專案根目錄。

### 說明與免責

本台股模組提供的預測僅為教育與研究用途，並不構成任何投資建議。模型僅利用簡單的線性（邏輯迴歸）方法與歷史資料，並嘗試納入美國市場因素，但無法保證準確性。任何金融交易請自行評估風險。

## 注意事項

* 本專案為前端靜態網站，所有資料由瀏覽器端即時抓取。若 API 無法在瀏覽器中跨域存取（CORS），您可能需要使用代理或在後端建置簡單的代理服務。
* 資料與分析僅供學術研究與學習參考，不構成任何投資建議。市場具有風險，請自行判斷。

## 資料來源引用

* Alternative.me 解釋恐懼貪婪指數的計算方法，指出指數從 0（極度恐慌）到 100（極度貪婪），並說明這些極端情況可能意味著買入機會或價格修正【762950707989567†L59-L79】。
* BlockCypher 的地址端點允許使用 `limit` 與 `before` 參數分頁，每次可最多取得 2,000 筆交易【963741525815197†L3496-L3504】。
* Relative Strength Index (RSI) 的原理是比較平均漲幅與平均跌幅；值超過 70 常視為過熱，低於 30 視為超賣【800268421240992†L375-L393】。
* Binance 提供的全球多空倉位比資料端點 `/futures/data/globalLongShortAccountRatio` 可查詢特定合約在不同週期的多空比率【754820992736042†L82-L106】。

祝您部署順利！