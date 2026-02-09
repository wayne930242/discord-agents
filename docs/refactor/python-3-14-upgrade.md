# Python 3.14 升級與回滾指引

## 目標
- 專案執行版本鎖定為 `>=3.14,<3.15`。
- 建立最小 runtime guard，避免在低於 3.14 的環境誤跑。
- free-threaded（`--disable-gil`）僅為相容性驗證，非正式生產預設。

## 升級步驟（一次性）
1. 安裝 Python 3.14（例如 `pyenv install 3.14.2`）。
2. 切換專案版本（例如 `pyenv local 3.14.2`，或其他等效工具）。
3. 重新安裝依賴：`uv sync`。
4. 驗證 runtime guard：`uv run python -m pytest tests/runtime/test_python_runtime_guard.py -v`。

## free-threaded 驗證（選用）
1. 以 Python 3.14 free-threaded 變體建立環境（若平台可用）。
2. 執行最小測試集與關鍵流程，確認行為一致。
3. 若有相容性問題，先修正程式或第三方套件，不把 free-threaded 當成生產預設。

## 3.15-dev 與 free-threaded 驗證矩陣
- 主線支援版本仍為 `3.14.x`，`3.15` 僅做 pre-release 相容性追蹤。
- 建議以非阻斷方式執行：
  - `stable`: 必須通過（Python 3.14）
  - `3.15-dev`: 可失敗（觀察相依套件支援進度）
  - `3.14t`: 可失敗（觀察 free-threaded 相依狀態）
- 可使用 `scripts/runtime_matrix.sh` 一次執行上述矩陣。

## 回滾步驟
1. 將 `pyproject.toml` 的 `requires-python` 調回既有版本策略（例如 3.13）。
2. 將 `.python-version` 調回原版本（例如 3.13）。
3. 重新 `uv sync`，並執行對應版本測試確認可用。
4. 視需要暫時移除或調整 runtime guard 測試條件，避免阻擋舊版修補流程。
