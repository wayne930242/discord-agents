# FastAPI React Starter 建立計劃 (Updated - FastAPI-Users)

## 專案架構特色 (重新設計)
基於 discord-agents 專案的優秀架構，改用成熟框架：
- 🎯 **現代化技術棧**: React 19 + FastAPI + SQLAlchemy 2.0 + Alembic
- 🎨 **美觀 UI**: Tailwind CSS + Radix UI + shadcn/ui components
- 🔒 **成熟認證**: FastAPI-Users (支援 JWT + OAuth2 + 社交登入)
- 🤖 **通用 Agent 系統**: 抽象化的 Agent 概念 (不限於 Discord)
- ⚡ **簡化排程**: APScheduler + SQLAlchemy (移除 Redis 依賴)
- 🏗️ **清晰架構**: Domain-driven design + API 分層
- 🐳 **容器化**: Multi-stage Docker build
- 📦 **現代包管理**: pnpm + uv

## 架構變更重點

### Agent 概念重新設計
- **原本**: Discord Bot (discord.py, 特定於 Discord)
- **新設計**: 通用 Agent (可以是 API agent, webhook agent, scheduled agent 等)
- **服務抽象**: AgentService 替代 BotService
- **配置抽象**: Agent 配置不限於 Discord token

### FastAPI-Users 整合
- 完整用戶管理系統
- 多種認證後端支援
- 社交媒體登入
- 郵件驗證系統
- 密碼重置功能

### 簡化基礎設施
- **移除 Redis**: 使用 APScheduler + SQLAlchemy 實現任務排程
- **內建速率限制**: 使用 slowapi 實現 API 速率限制
- **減少外部依賴**: 更容易部署和維護
- **保持性能**: 對大多數使用場景仍然足夠

## TODO 任務清單 (修正版)

### Phase 1: FastAPI-Users 整合 🔐
- [ ] 安裝和配置 FastAPI-Users
- [ ] 建立 User model (繼承 FastAPI-Users)
- [ ] 設定認證後端 (JWT + Cookie)
- [ ] 建立認證路由
- [ ] 整合前端認證流程

### Phase 2: 通用 Agent 系統設計 🤖
- [ ] 重新設計 Agent models (移除 Discord 特定欄位)
- [ ] 建立 AgentType enum (API, Webhook, Scheduled, etc.)
- [ ] 重新設計 Agent configuration system
- [ ] 建立抽象 AgentService
- [ ] 設計 Agent lifecycle management

### Phase 3: 前端框架整合 🎨
- [ ] 整合 FastAPI-Users 前端認證
- [ ] 建立通用 Agent 管理 UI
- [ ] 重新設計 Dashboard (移除 Discord 特定元素)
- [ ] 建立 Agent 類型選擇器
- [ ] 實作 Agent 配置表單

### Phase 4: 架構簡化與重構 🛠️
- [ ] 移除 Redis 和相關依賴
- [ ] 實作 APScheduler 為基礎的任務系統
- [ ] 建立 SQLAlchemy 基礎的狀態管理
- [ ] 整合 slowapi 速率限制
- [ ] 重構 broker 系統為簡化版本
- [ ] 移除 Discord 特定 cogs

### Phase 5: 範例 Agent 實作 📚
- [ ] 建立 HTTP API Agent 範例
- [ ] 建立 Scheduled Task Agent 範例
- [ ] 建立 Webhook Agent 範例
- [ ] 文件化 Agent 開發指南
- [ ] 建立 Agent plugin template

### Phase 6: 部署與優化 🐳
- [ ] 更新 Docker 配置 (移除 Redis)
- [ ] 移除 Discord 特定環境變數
- [ ] 建立通用環境變數模板
- [ ] 優化依賴關係
- [ ] 建立部署文檔

### Phase 7: 文件與範例 📖
- [ ] 建立新的 README
- [ ] 撰寫 Agent 開發指南
- [ ] 建立多種 Agent 範例
- [ ] 建立部署指南
- [ ] 建立最佳實踐文檔

### Phase 8: 最終優化 🚀
- [ ] 效能優化
- [ ] 安全性檢查
- [ ] 最終測試
- [ ] 版本發布準備

## 新的專案結構概念

```
app/
├── agents/                 # Agent 系統
│   ├── models/            # Agent models
│   ├── services/          # Agent services
│   ├── types/             # Agent types & interfaces
│   ├── executors/         # Agent execution engines
│   ├── scheduler/         # APScheduler 基礎任務排程
│   └── plugins/           # Agent plugins
├── auth/                  # FastAPI-Users 認證
├── api/                   # API routes
├── core/                  # 核心配置
└── schemas/               # Pydantic schemas

frontend/
├── components/            # React components
│   ├── auth/             # 認證相關
│   ├── agents/           # Agent 管理
│   └── common/           # 通用組件
├── pages/                # 頁面
└── hooks/                # React hooks
```

## 簡化架構的優勢

1. **部署簡單**: 只需要 PostgreSQL，不需要 Redis
2. **成本低**: 減少一個服務的運維成本
3. **維護容易**: 更少的外部依賴，更少的故障點
4. **適合小型團隊**: 大多數情況下性能已經足夠
5. **擴展性**: 如需要高性能，後續仍可加入 Redis

## 預估工作量
約需 3-4 天完成，這是一個較大的重構工作。

## 目標倉庫
git@github.com:wayne930242/fastapi-react-starter.git
