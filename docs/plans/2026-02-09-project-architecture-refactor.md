# Discord Agents 專案重構 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在不改變既有對外 API 行為的前提下，完成後端分層解耦、錯誤處理一致化與前端 API 客戶端模組化，降低後續維護成本並提升可測試性。

**Architecture:** 重構採用「先測試、再抽象、最後收斂」策略。後端先抽出 bot orchestration gateway 與統一例外型別，讓 `api` 與 `services` 不直接依賴 Redis 細節；前端則把 `lib/api.ts` 拆成 base client + domain clients，並保留既有呼叫介面相容層。全程採用小步驟 TDD 與頻繁提交，確保每一步都可回滾。

**Tech Stack:** FastAPI, SQLAlchemy, Redis, pytest, React 19, TypeScript, axios, TanStack Query

---

## 前置規範（全任務適用）

- 先使用 `@test-driven-development`，每個功能改動都遵循 Red → Green → Refactor。
- 每完成 1 個任務後，使用 `@verification-before-completion` 執行最小驗證與回歸測試。
- 每個任務完成後建立一次小型 commit，commit message 需對應任務名稱。
- 避免一次觸碰過多模組；若任務依賴未完成，先加 TODO 與測試標記，不跳步實作。

### Task 1: 建立可重用測試基礎設施（移除重複 fixture）

**Files:**
- Create: `tests/conftest.py`
- Modify: `tests/test_fastapi.py`
- Modify: `tests/test_token_usage_api.py`
- Modify: `tests/test_fastapi_simple.py`

**Step 1: Write the failing test**

```python
# tests/test_fastapi_simple.py
# Remove local TestClient construction and rely on shared fixture `client`
def test_health_check(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_fastapi_simple.py::test_health_check -v`
Expected: FAIL with `fixture 'client' not found`

**Step 3: Write minimal implementation**

```python
# tests/conftest.py
@pytest.fixture(scope="function")
def client() -> Generator[TestClient, None, None]:
    ...

@pytest.fixture
def auth_headers() -> dict[str, str]:
    ...
```

將 `tests/test_fastapi.py`、`tests/test_token_usage_api.py` 既有重複的 `client` 與 `auth_headers` fixture 移除並改用共用 fixture。

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_fastapi_simple.py tests/test_fastapi.py tests/test_token_usage_api.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/conftest.py tests/test_fastapi.py tests/test_token_usage_api.py tests/test_fastapi_simple.py
git commit -m "test: centralize API test fixtures in conftest"
```

### Task 2: 抽離 Bot 狀態調度介面（隔離 service 對 Redis 的直接依賴）

**Files:**
- Create: `discord_agents/services/bot_runtime_gateway.py`
- Modify: `discord_agents/services/bot_service.py`
- Test: `tests/services/test_bot_service_runtime_gateway.py`

**Step 1: Write the failing test**

```python
# tests/services/test_bot_service_runtime_gateway.py
class FakeRuntimeGateway:
    def __init__(self) -> None:
        self.started: list[str] = []

    def request_start(self, bot_id: str, init_config: dict, setup_config: dict) -> None:
        self.started.append(bot_id)


def test_start_bot_uses_runtime_gateway(db_session: Session, bot_model: BotModel) -> None:
    gateway = FakeRuntimeGateway()
    ok = BotService.start_bot(db_session, bot_model.id, runtime_gateway=gateway)
    assert ok is True
    assert bot_model.bot_id() in gateway.started
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/services/test_bot_service_runtime_gateway.py::test_start_bot_uses_runtime_gateway -v`
Expected: FAIL with `unexpected keyword argument 'runtime_gateway'`

**Step 3: Write minimal implementation**

```python
# discord_agents/services/bot_runtime_gateway.py
class BotRuntimeGateway(Protocol):
    def request_start(self, bot_id: str, init_config: dict, setup_config: dict) -> None: ...
    def request_stop(self, bot_id: str) -> None: ...
    def request_restart(self, bot_id: str) -> None: ...

class RedisBotRuntimeGateway:
    def __init__(self, redis_client: BotRedisClient | None = None) -> None:
        self._redis_client = redis_client or BotRedisClient()
```

```python
# discord_agents/services/bot_service.py
@staticmethod
def start_bot(db: Session, bot_id: int, runtime_gateway: BotRuntimeGateway | None = None) -> bool:
    gateway = runtime_gateway or RedisBotRuntimeGateway()
    ...
    gateway.request_start(bot_id_str, init_config, setup_config)
```

同樣模式套用到 `create_bot`、`update_bot`、`delete_bot`、`stop_bot`、`start_all_bots`。

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/services/test_bot_service_runtime_gateway.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add discord_agents/services/bot_runtime_gateway.py discord_agents/services/bot_service.py tests/services/test_bot_service_runtime_gateway.py
git commit -m "refactor: decouple bot service from redis runtime"
```

### Task 3: 統一後端錯誤處理與 logging（移除 print 與裸露 exception 字串）

**Files:**
- Create: `discord_agents/core/exceptions.py`
- Modify: `discord_agents/services/bot_service.py`
- Modify: `discord_agents/api/bots.py`
- Modify: `discord_agents/api/token_usage.py`
- Test: `tests/api/test_error_handling_contract.py`

**Step 1: Write the failing test**

```python
# tests/api/test_error_handling_contract.py
def test_start_bot_returns_404_on_missing_bot(client: TestClient, auth: tuple[str, str]) -> None:
    response = client.post("/api/v1/bots/999999/start", auth=auth)
    assert response.status_code == 404
    assert response.json()["detail"] == "Bot not found"
```

```python
def test_token_usage_record_internal_error_is_sanitized(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    auth: tuple[str, str],
) -> None:
    monkeypatch.setattr(TokenUsageService, "record_token_usage", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("secret db error")))
    response = client.post("/api/v1/token-usage/record", json={...}, auth=auth)
    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to record token usage"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/api/test_error_handling_contract.py -v`
Expected: FAIL because current detail contains raw exception message

**Step 3: Write minimal implementation**

```python
# discord_agents/core/exceptions.py
class ResourceNotFoundError(Exception):
    pass

class RuntimeOperationError(Exception):
    pass
```

在 service 層丟出語義化 exception；在 API router 統一轉換為固定錯誤訊息，並以 `logger.exception(...)` 記錄細節；移除 `print(...)`。

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/api/test_error_handling_contract.py tests/test_fastapi.py tests/test_token_usage_api.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add discord_agents/core/exceptions.py discord_agents/services/bot_service.py discord_agents/api/bots.py discord_agents/api/token_usage.py tests/api/test_error_handling_contract.py
git commit -m "refactor: standardize api error handling and logging"
```

### Task 4: 拆分 Redis broker 的多重責任（狀態管理 vs session/history）

**Files:**
- Create: `discord_agents/scheduler/state_store.py`
- Create: `discord_agents/scheduler/history_store.py`
- Create: `discord_agents/scheduler/session_store.py`
- Modify: `discord_agents/scheduler/broker.py`
- Modify: `discord_agents/scheduler/worker.py`
- Test: `tests/scheduler/test_state_store.py`

**Step 1: Write the failing test**

```python
# tests/scheduler/test_state_store.py
def test_get_all_bots_returns_unique_ids(fake_redis: FakeRedis) -> None:
    store = BotStateStore(fake_redis)
    fake_redis.set("bot:bot_1:state", "running")
    fake_redis.set("bot:bot_1:init_config", "{}")
    fake_redis.set("bot:bot_2:state", "idle")
    assert sorted(store.get_all_bots()) == ["bot_1", "bot_2"]
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/scheduler/test_state_store.py::test_get_all_bots_returns_unique_ids -v`
Expected: FAIL with `NameError: BotStateStore`

**Step 3: Write minimal implementation**

```python
# discord_agents/scheduler/state_store.py
class BotStateStore:
    def __init__(self, redis_client: Redis, redlock: Redlock) -> None:
        ...

    def get_all_bots(self) -> list[str]:
        ...
```

將 `broker.py` 改為 facade（向後相容），內部組合三個 store；`worker.py` 只依賴 state store 所需方法。

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/scheduler/test_state_store.py tests/test_clear_sessions.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add discord_agents/scheduler/state_store.py discord_agents/scheduler/history_store.py discord_agents/scheduler/session_store.py discord_agents/scheduler/broker.py discord_agents/scheduler/worker.py tests/scheduler/test_state_store.py
git commit -m "refactor: split broker responsibilities into focused stores"
```

### Task 5: 重構 FastAPI 啟動流程（可測試與可配置）

**Files:**
- Create: `discord_agents/app_factory.py`
- Modify: `discord_agents/fastapi_main.py`
- Modify: `discord_agents/core/migration.py`
- Test: `tests/test_app_factory.py`

**Step 1: Write the failing test**

```python
# tests/test_app_factory.py
def test_create_app_can_disable_side_effect_startup() -> None:
    app = create_app(run_migrations=False, start_bot_manager=False, auto_start_bots=False)
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_app_factory.py::test_create_app_can_disable_side_effect_startup -v`
Expected: FAIL with `ImportError: cannot import name 'create_app'`

**Step 3: Write minimal implementation**

```python
# discord_agents/app_factory.py
def create_app(
    *,
    run_migrations: bool = True,
    start_bot_manager: bool = True,
    auto_start_bots: bool = True,
) -> FastAPI:
    ...
```

`fastapi_main.py` 僅保留 `app = create_app()` 與 `__main__` 啟動邏輯。

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_app_factory.py tests/test_fastapi_simple.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add discord_agents/app_factory.py discord_agents/fastapi_main.py discord_agents/core/migration.py tests/test_app_factory.py
git commit -m "refactor: introduce app factory and controllable startup hooks"
```

### Task 6: 前端 API Client 模組化並保留相容介面

**Files:**
- Create: `frontend/src/lib/api/baseClient.ts`
- Create: `frontend/src/lib/api/authClient.ts`
- Create: `frontend/src/lib/api/botClient.ts`
- Create: `frontend/src/lib/api/agentClient.ts`
- Create: `frontend/src/lib/api/tokenUsageClient.ts`
- Create: `frontend/src/lib/api/index.ts`
- Modify: `frontend/src/lib/api.ts`
- Test: `frontend/src/lib/api/__tests__/baseClient.test.ts`

**Step 1: Write the failing test**

```typescript
// frontend/src/lib/api/__tests__/baseClient.test.ts
it("adds bearer token from localStorage", async () => {
  localStorage.setItem("access_token", "abc")
  const client = createApiClient("http://localhost:8080/api/v1")
  const req = await client.interceptors.request.handlers[0].fulfilled({ headers: {} })
  expect(req.headers.Authorization).toBe("Bearer abc")
})
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm test -- baseClient.test.ts`
Expected: FAIL because `createApiClient` does not exist

**Step 3: Write minimal implementation**

```typescript
// frontend/src/lib/api/baseClient.ts
export function createApiClient(baseURL: string) {
  const api = axios.create({ baseURL, headers: { "Content-Type": "application/json" } })
  ...
  return api
}
```

`frontend/src/lib/api.ts` 暫時改為 re-export 相容層，避免一次性修改所有 page/component import。

**Step 4: Run test to verify it passes**

Run: `cd frontend && pnpm test -- baseClient.test.ts && pnpm build`
Expected: PASS + Build success

**Step 5: Commit**

```bash
git add frontend/src/lib/api/baseClient.ts frontend/src/lib/api/authClient.ts frontend/src/lib/api/botClient.ts frontend/src/lib/api/agentClient.ts frontend/src/lib/api/tokenUsageClient.ts frontend/src/lib/api/index.ts frontend/src/lib/api.ts frontend/src/lib/api/__tests__/baseClient.test.ts
git commit -m "refactor: modularize frontend api clients with compatibility layer"
```

### Task 7: 清理型別與 schema 對齊（後端 Pydantic + 前端 TS）

**Files:**
- Modify: `discord_agents/schemas/bot.py`
- Modify: `discord_agents/schemas/token_usage.py`
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/types/api.ts`
- Test: `tests/test_fastapi.py`
- Test: `frontend/src/lib/api/__tests__/types-compile.test.ts`（或以 `tsc --noEmit` 驗證）

**Step 1: Write the failing test**

```bash
cd frontend && pnpm exec tsc --noEmit
```

針對 `use_function_map`、`tools`、可選欄位 nullability 新增型別約束，先讓型別檢查失敗以暴露不一致。

**Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm exec tsc --noEmit`
Expected: FAIL with mismatched API field types

**Step 3: Write minimal implementation**

```typescript
// frontend/src/lib/types/api.ts
export interface BotDto {
  id: number
  token: string
  use_function_map: Record<string, boolean>
  ...
}
```

後端 schema 明確限制 `use_function_map: dict[str, bool]`（若現況允許 mixed values，先增加轉換層避免 breaking change）。

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_fastapi.py -q && cd frontend && pnpm exec tsc --noEmit`
Expected: PASS

**Step 5: Commit**

```bash
git add discord_agents/schemas/bot.py discord_agents/schemas/token_usage.py frontend/src/lib/types/api.ts frontend/src/lib/api.ts
git commit -m "refactor: align backend schemas and frontend api types"
```

### Task 8: 文件、驗證矩陣與回滾手冊

**Files:**
- Modify: `README.md`
- Create: `docs/refactor/runtime-gateway.md`
- Create: `docs/refactor/frontend-api-modules.md`
- Create: `docs/refactor/rollback.md`

**Step 1: Write the failing test**

```bash
# 以文件一致性檢查作為失敗前置（若專案無 markdown lint，可先用最小 grep 驗證）
rg "BotRedisClient" README.md docs/refactor || true
```

Expected: Missing new architecture docs / stale references

**Step 2: Run test to verify it fails**

Run: `rg "app_factory|runtime gateway|api modules" README.md docs/refactor`
Expected: FAIL (no matches before doc updates)

**Step 3: Write minimal implementation**

補上：
- 新架構圖（service → runtime gateway → Redis）
- 啟動流程與測試模式開關
- 前端 API 模組遷移指引
- 回滾指令（按任務粒度）

**Step 4: Run test to verify it passes**

Run: `rg "app_factory|runtime gateway|api modules" README.md docs/refactor`
Expected: PASS (all keywords found)

**Step 5: Commit**

```bash
git add README.md docs/refactor/runtime-gateway.md docs/refactor/frontend-api-modules.md docs/refactor/rollback.md
git commit -m "docs: add refactor architecture and rollback guides"
```

### Task 9: 模型版本升級與相容策略（你提到的重點）

**Files:**
- Modify: `discord_agents/domain/agent.py`
- Modify: `discord_agents/core/config.py`
- Modify: `discord_agents/domain/tool_def/search_tool.py`
- Modify: `discord_agents/domain/tool_def/life_env_tool.py`
- Modify: `discord_agents/domain/tool_def/math_tool.py`
- Modify: `discord_agents/domain/tool_def/summarizer_tool.py`
- Modify: `discord_agents/domain/tool_def/content_extractor_tool.py`
- Modify: `tests/test_fastapi.py`
- Modify: `tests/test_token_usage_api.py`
- Modify: `frontend/src/components/AgentEditDialog.tsx`
- Modify: `frontend/src/lib/api.ts`
- Create: `docs/refactor/model-lifecycle-policy.md`

**Step 1: Write the failing test**

```python
# tests/test_fastapi.py
def test_get_available_tools_and_models_returns_supported_models(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    username, password = _decode_basic_auth(auth_headers)
    response = client.get("/api/v1/bots/tools/", auth=(username, password))
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert len(data["models"]) > 0
    # No deprecated hard-coded preview-only default in top recommendation slot
    assert data["models"][0] != "gemini-2.5-flash-preview-05-20"
```

```python
# tests/test_token_usage_api.py
def test_get_specific_model_pricing_supports_current_default_model(...) -> None:
    model_name = settings.agent_model
    response = client.get(
        f"/api/v1/token-usage/models/{model_name}/pricing",
        headers=auth_headers,
    )
    assert response.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_fastapi.py::test_get_available_tools_and_models_returns_supported_models tests/test_token_usage_api.py::test_get_specific_model_pricing_supports_current_default_model -v`
Expected: FAIL because current default/model list still uses old pinned preview model

**Step 3: Write minimal implementation**

```python
# discord_agents/domain/agent.py
class LLMs:
    MODEL_ALIASES = {
        # backward compatibility for existing DB values
        "gemini-2.5-flash-preview-05-20": "gemini-2.5-flash",
        "gemini-2.5-flash-preview": "gemini-2.5-flash",
        "gemini-2.5-pro-preview": "gemini-2.5-pro",
    }

    llm_list = [
        {"model": "gemini-2.5-flash", ...},
        {"model": "gemini-2.5-pro", ...},
        ...
    ]

    @staticmethod
    def normalize_model_name(model_name: str) -> str:
        return LLMs.MODEL_ALIASES.get(model_name, model_name)
```

`get_pricing`、`get_restrictions`、`find_model_type` 先 normalize 再查表，確保舊資料可用。  
`discord_agents/core/config.py` 的 `agent_model` 預設值改成穩定名稱（非 preview pin）。  
工具檔案中的固定模型常數改為單一來源常數或共用 helper，避免散落硬編碼。  
前端顯示模型清單時，若遇到舊名稱，顯示「已棄用 / 自動對映」標籤。

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_fastapi.py tests/test_token_usage_api.py -q`
Expected: PASS

Run: `cd frontend && pnpm exec tsc --noEmit && pnpm build`
Expected: PASS

**Step 5: Commit**

```bash
git add discord_agents/domain/agent.py discord_agents/core/config.py discord_agents/domain/tool_def/search_tool.py discord_agents/domain/tool_def/life_env_tool.py discord_agents/domain/tool_def/math_tool.py discord_agents/domain/tool_def/summarizer_tool.py discord_agents/domain/tool_def/content_extractor_tool.py tests/test_fastapi.py tests/test_token_usage_api.py frontend/src/components/AgentEditDialog.tsx frontend/src/lib/api.ts docs/refactor/model-lifecycle-policy.md
git commit -m "refactor: update model catalog with backward-compatible aliases"
```

### Task 10: Python 升級到 3.14 並加入 free-threaded 相容驗證

**Files:**
- Modify: `pyproject.toml`
- Modify: `.python-version`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Create: `tests/runtime/test_python_runtime_guard.py`
- Create: `docs/refactor/python-3-14-upgrade.md`

**Step 1: Write the failing test**

```python
# tests/runtime/test_python_runtime_guard.py
import sys

def test_runtime_is_python_314_or_newer() -> None:
    assert sys.version_info >= (3, 14)
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/runtime/test_python_runtime_guard.py -v`
Expected: FAIL on environments still using <3.14

**Step 3: Write minimal implementation**

```toml
# pyproject.toml
requires-python = ">=3.14,<3.15"
```

```text
# .python-version
3.14
```

README / AGENTS 增加：
- 升級到 Python 3.14 的 one-shot 指令
- free-threaded build 為「可選相容驗證」，不是預設強制

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/runtime/test_python_runtime_guard.py -v`
Expected: PASS on upgraded runtime

**Step 5: Commit**

```bash
git add pyproject.toml .python-version README.md AGENTS.md tests/runtime/test_python_runtime_guard.py docs/refactor/python-3-14-upgrade.md
git commit -m "chore: upgrade runtime target to python 3.14 with free-threaded readiness notes"
```

### Task 11: 單一 Bot 實例 + Channel 分流多 Queue 並行調度

**Files:**
- Create: `discord_agents/scheduler/channel_queue_router.py`
- Create: `discord_agents/scheduler/channel_worker_pool.py`
- Modify: `discord_agents/cogs/base_cog.py`
- Modify: `discord_agents/domain/bot.py`
- Modify: `discord_agents/scheduler/worker.py`
- Modify: `discord_agents/scheduler/tasks.py`
- Test: `tests/scheduler/test_channel_queue_router.py`
- Test: `tests/scheduler/test_channel_worker_pool.py`
- Test: `tests/test_e2e.py`
- Create: `docs/refactor/single-instance-multi-queue.md`

**Step 1: Write the failing test**

```python
# tests/scheduler/test_channel_queue_router.py
@pytest.mark.asyncio
async def test_same_channel_messages_are_processed_in_order() -> None:
    router = ChannelQueueRouter(max_workers_per_channel=1, max_channels=100)
    processed: list[str] = []

    async def handler(item: str) -> None:
        processed.append(item)

    await router.enqueue("channel-1", "a", handler)
    await router.enqueue("channel-1", "b", handler)
    await router.drain()

    assert processed == ["a", "b"]
```

```python
@pytest.mark.asyncio
async def test_different_channels_can_process_concurrently() -> None:
    router = ChannelQueueRouter(max_workers_per_channel=1, max_channels=100)
    ...
    # assert elapsed < serial execution threshold
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/scheduler/test_channel_queue_router.py -v`
Expected: FAIL with `ImportError/NameError: ChannelQueueRouter`

**Step 3: Write minimal implementation**

```python
# discord_agents/scheduler/channel_queue_router.py
class ChannelQueueRouter:
    def __init__(self, max_workers_per_channel: int, max_channels: int) -> None:
        self._queues: dict[str, asyncio.Queue[QueueItem]] = {}
        ...

    async def enqueue(self, channel_id: str, payload: T, handler: Handler[T]) -> None:
        ...
```

在 `base_cog.py` 中，將原本直接處理訊息的流程改為：
1. 以 `channel_id` 路由進對應 queue  
2. 保證同一 channel 內序列化  
3. 不同 channel 可並行  
4. bot 仍維持單一實例（不建立多個 bot instance）

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/scheduler/test_channel_queue_router.py tests/scheduler/test_channel_worker_pool.py tests/test_e2e.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add discord_agents/scheduler/channel_queue_router.py discord_agents/scheduler/channel_worker_pool.py discord_agents/cogs/base_cog.py discord_agents/domain/bot.py discord_agents/scheduler/worker.py discord_agents/scheduler/tasks.py tests/scheduler/test_channel_queue_router.py tests/scheduler/test_channel_worker_pool.py tests/test_e2e.py docs/refactor/single-instance-multi-queue.md
git commit -m "feat: add single-instance channel-based multi-queue processing"
```

## 全域驗證（全部任務完成後）

1. Backend tests

```bash
python -m pytest tests/ -v
```

2. Frontend typecheck + build

```bash
cd frontend
pnpm exec tsc --noEmit
pnpm build
```

3. 模型映射驗證

```bash
python -m pytest tests/test_fastapi.py::test_get_available_tools_and_models_returns_supported_models tests/test_token_usage_api.py::test_get_specific_model_pricing_supports_current_default_model -q
```

4. Smoke run（可選，但建議）

```bash
python start_dev.py
# 新終端
cd frontend && pnpm dev
```

預期結果：
- API 文件可開啟：`/api/docs`
- 登入、Bot CRUD、Start/Stop、Token Usage 頁面功能正常
- 日誌無 `print` 與未處理 traceback 外洩至 API response
- 舊模型名稱在資料庫仍可正常啟動，且會被自動映射到新模型名稱

## 風險與回滾策略

- 風險 1：Redis state 行為改動造成 bot lifecycle 競態。
  - 緩解：Task 2 與 Task 4 皆先補單元測試，保留 `broker.py` facade 相容層。
- 風險 2：前端 API 拆分導致 import 斷裂。
  - 緩解：Task 6 保留 `frontend/src/lib/api.ts` 相容 re-export。
- 風險 3：啟動流程重構影響本地開發。
  - 緩解：Task 5 保持 `fastapi_main.py` 對外入口不變，只內聚工廠建立邏輯。

回滾原則：若任務驗證失敗，僅回退該任務 commit，不跨任務回滾。
