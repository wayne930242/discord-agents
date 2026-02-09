# 單實例 Bot + 多 Queue（Channel 分流）設計

## 目標
- 每個 Bot 只維持一個實例。
- 同一個 Channel 的訊息必須保持順序處理。
- 不同 Channel 的訊息可以並行處理，避免互相阻塞。

## 實作摘要
- 新增 `discord_agents/scheduler/channel_queue_router.py`。
- `AgentCog.on_message` 不再直接執行 agent 流程，而是依 `channel_id` 入列。
- Router 會為每個 `channel_id` 建立一個 queue + worker：
  - 同 channel：單 worker 保序
  - 跨 channel：多 worker 並行

## 目前保證
- 不會新增額外 bot instance。
- Channel 粒度隔離：熱門頻道不會完全拖垮其他頻道。
- 可透過 `wait_channel_idle` / `wait_all_idle` 在測試與關閉流程中等待排空。

## 風險與後續
- 若單一 channel 訊息過量，仍可能形成該 channel 的背壓。
- 後續可加上：
  - 每個 channel 的背壓指標與告警
  - queue 深度超限的降級策略（丟棄、延遲、重試）
  - 管理命令查看 pending queue 指標
