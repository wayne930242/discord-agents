import axios from "axios";

// API base URL - configurable via environment variables
// First try window.location origin (for production), then env var, then localhost
const getApiBaseUrl = () => {
  // If we're in production (not localhost), use current origin
  if (
    typeof window !== "undefined" &&
    !window.location.hostname.includes("localhost") &&
    !window.location.hostname.includes("127.0.0.1")
  ) {
    return `${window.location.protocol}//${window.location.host}/api/v1`;
  }
  // Otherwise use env var or localhost fallback
  return import.meta.env.VITE_API_BASE_URL || "http://localhost:8080/api/v1";
};

const API_BASE_URL = getApiBaseUrl();

// Debug logging
console.log("API_BASE_URL:", API_BASE_URL);
console.log(
  "window.location:",
  typeof window !== "undefined" ? window.location.href : "N/A"
);
console.log("VITE_API_BASE_URL:", import.meta.env.VITE_API_BASE_URL);

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add request interceptor to include auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Add response interceptor to handle token expiration
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If we get a 401 and haven't already tried to refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      // Try to re-authenticate using stored credentials
      const username = localStorage.getItem("username");
      const password = localStorage.getItem("password");

      if (username && password) {
        try {
          console.log("Token 已過期，正在自動重新登入...");
          const loginResponse = await authAPI.login(username, password);

          // Store new token
          localStorage.setItem("access_token", loginResponse.access_token);

          // Update the original request with new token
          originalRequest.headers.Authorization = `Bearer ${loginResponse.access_token}`;

          console.log("重新登入成功，繼續執行請求");
          // Retry the original request
          return api(originalRequest);
        } catch (loginError) {
          console.error("自動重新登入失敗:", loginError);
          // Show user-friendly message
          alert("登入已過期，請重新登入");
          // Clear stored credentials and redirect to login
          localStorage.removeItem("access_token");
          localStorage.removeItem("username");
          localStorage.removeItem("password");
          window.location.href = "/login";
          return Promise.reject(loginError);
        }
      } else {
        // No stored credentials, redirect to login
        console.log("未找到儲存的登入憑證，重新導向到登入頁面");
        localStorage.removeItem("access_token");
        window.location.href = "/login";
      }
    }

    return Promise.reject(error);
  }
);

// Types matching backend schemas
export interface Agent {
  id: number;
  name: string;
  description: string;
  role_instructions: string;
  tool_instructions: string;
  agent_model: string;
  tools: string[];
}

export interface Bot {
  id: number;
  token: string;
  error_message: string;
  command_prefix: string;
  dm_whitelist: string[];
  srv_whitelist: string[];
  use_function_map: Record<string, unknown>;
  agent_id?: number;
  agent?: Agent;
}

export interface BotCreate {
  token: string;
  error_message?: string;
  command_prefix?: string;
  dm_whitelist?: string[];
  srv_whitelist?: string[];
  use_function_map?: Record<string, unknown>;
  agent_id?: number;
}

export interface BotUpdate {
  token?: string;
  error_message?: string;
  command_prefix?: string;
  dm_whitelist?: string[];
  srv_whitelist?: string[];
  use_function_map?: Record<string, unknown>;
  agent_id?: number;
}

export interface BotQueueMetrics {
  total_pending: number;
  channels: Record<string, number>;
  updated_at: string | null;
  status?: string;
}

export type BotQueueSnapshot = Record<string, BotQueueMetrics>;

// Token Usage Types
export interface TokenUsage {
  id: number;
  agent_id: number;
  agent_name: string;
  model_name: string;
  year: number;
  month: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  input_cost: number;
  output_cost: number;
  total_cost: number;
  created_at: string;
  updated_at: string;
}

export interface UsageSummaryByAgent {
  agent_id: number;
  agent_name: string;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_input_cost: number;
  total_output_cost: number;
  total_cost: number;
}

export interface UsageSummaryByModel {
  model_name: string;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_input_cost: number;
  total_output_cost: number;
  total_cost: number;
}

export interface MonthlyTrend {
  year: number;
  month: number;
  month_year: string;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_input_cost: number;
  total_output_cost: number;
  total_cost: number;
}

export interface TotalCost {
  total_input_cost: number;
  total_output_cost: number;
  total_cost: number;
}

export interface ModelPricing {
  model_name: string;
  input_price_per_1M: number;
  output_price_per_1M: number;
  max_tokens?: number;
  context_window?: number;
  notes?: string;
}

// Auth API
export const authAPI = {
  async login(username: string, password: string) {
    // Use basic auth for login - don't use the main api instance to avoid interceptor loops
    const credentials = btoa(`${username}:${password}`);
    const response = await axios.post(
      `${API_BASE_URL}/auth/login`,
      {},
      {
        headers: {
          Authorization: `Basic ${credentials}`,
        },
      }
    );
    return response.data;
  },

  async me() {
    const response = await api.get("/auth/me");
    return response.data;
  },

  logout() {
    // Clear all stored authentication data
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
    localStorage.removeItem("password");
  },
};

// Bot API
export const botAPI = {
  async getBots(): Promise<Bot[]> {
    const response = await api.get("/bots/");
    return response.data;
  },

  async getBot(botId: number): Promise<Bot> {
    const response = await api.get(`/bots/${botId}`);
    return response.data;
  },

  async createBot(bot: BotCreate): Promise<Bot> {
    const response = await api.post("/bots/", bot);
    return response.data;
  },

  async updateBot(botId: number, bot: BotUpdate): Promise<Bot> {
    const response = await api.put(`/bots/${botId}`, bot);
    return response.data;
  },

  async deleteBot(botId: number): Promise<{ message: string }> {
    const response = await api.delete(`/bots/${botId}`);
    return response.data;
  },

  async startBot(botId: number): Promise<{ message: string }> {
    const response = await api.post(`/bots/${botId}/start`);
    return response.data;
  },

  async stopBot(botId: number): Promise<{ message: string }> {
    const response = await api.post(`/bots/${botId}/stop`);
    return response.data;
  },

  async startAllBots(): Promise<{ started: number; failed: number }> {
    const response = await api.post("/bots/start-all");
    return response.data;
  },

  async getBotStatus(): Promise<Record<string, string>> {
    const response = await api.get("/bots/status");
    return response.data;
  },

  async getBotQueues(params?: {
    topNChannels?: number;
    includeIdleBots?: boolean;
  }): Promise<BotQueueSnapshot> {
    const queryParams = new URLSearchParams();
    if (params?.topNChannels) {
      queryParams.append("top_n_channels", params.topNChannels.toString());
    }
    if (params?.includeIdleBots) {
      queryParams.append("include_idle_bots", "true");
    }

    const url = queryParams.toString()
      ? `/bots/queues?${queryParams}`
      : "/bots/queues";
    const response = await api.get(url);
    return response.data;
  },
};

// Agent API
export const agentAPI = {
  async getAgents(): Promise<Agent[]> {
    const response = await api.get("/bots/agents/");
    return response.data;
  },

  async createAgent(agent: Omit<Agent, "id">): Promise<Agent> {
    const response = await api.post("/bots/agents/", agent);
    return response.data;
  },

  async updateAgent(agentId: number, agent: Partial<Agent>): Promise<Agent> {
    const response = await api.put(`/bots/agents/${agentId}`, agent);
    return response.data;
  },

  async getAvailableToolsAndModels(): Promise<{
    tools: string[];
    models: string[];
  }> {
    const response = await api.get("/bots/tools/");
    return response.data;
  },
};

// Token Usage API
export const tokenUsageAPI = {
  async getAllUsage(params?: {
    year?: number;
    month?: number;
  }): Promise<TokenUsage[]> {
    const queryParams = new URLSearchParams();
    if (params?.year) queryParams.append("year", params.year.toString());
    if (params?.month) queryParams.append("month", params.month.toString());

    const url = queryParams.toString()
      ? `/token-usage/all?${queryParams}`
      : "/token-usage/all";
    const response = await api.get(url);
    return response.data;
  },

  async getAgentUsage(
    agentId: number,
    params?: { year?: number; month?: number }
  ): Promise<TokenUsage[]> {
    const queryParams = new URLSearchParams();
    if (params?.year) queryParams.append("year", params.year.toString());
    if (params?.month) queryParams.append("month", params.month.toString());

    const url = queryParams.toString()
      ? `/token-usage/agent/${agentId}?${queryParams}`
      : `/token-usage/agent/${agentId}`;
    const response = await api.get(url);
    return response.data;
  },

  async getSummaryByAgent(params?: {
    year?: number;
    month?: number;
  }): Promise<UsageSummaryByAgent[]> {
    const queryParams = new URLSearchParams();
    if (params?.year) queryParams.append("year", params.year.toString());
    if (params?.month) queryParams.append("month", params.month.toString());

    const url = queryParams.toString()
      ? `/token-usage/summary/by-agent?${queryParams}`
      : "/token-usage/summary/by-agent";
    const response = await api.get(url);
    return response.data;
  },

  async getSummaryByModel(params?: {
    year?: number;
    month?: number;
  }): Promise<UsageSummaryByModel[]> {
    const queryParams = new URLSearchParams();
    if (params?.year) queryParams.append("year", params.year.toString());
    if (params?.month) queryParams.append("month", params.month.toString());

    const url = queryParams.toString()
      ? `/token-usage/summary/by-model?${queryParams}`
      : "/token-usage/summary/by-model";
    const response = await api.get(url);
    return response.data;
  },

  async getMonthlyTrend(params?: {
    agentId?: number;
    modelName?: string;
    limit?: number;
  }): Promise<MonthlyTrend[]> {
    const queryParams = new URLSearchParams();
    if (params?.agentId)
      queryParams.append("agent_id", params.agentId.toString());
    if (params?.modelName) queryParams.append("model_name", params.modelName);
    if (params?.limit) queryParams.append("limit", params.limit.toString());

    const url = queryParams.toString()
      ? `/token-usage/trend/monthly?${queryParams}`
      : "/token-usage/trend/monthly";
    const response = await api.get(url);
    return response.data;
  },

  async getTotalCost(params?: {
    agentId?: number;
    year?: number;
    month?: number;
  }): Promise<TotalCost> {
    const queryParams = new URLSearchParams();
    if (params?.agentId)
      queryParams.append("agent_id", params.agentId.toString());
    if (params?.year) queryParams.append("year", params.year.toString());
    if (params?.month) queryParams.append("month", params.month.toString());

    const url = queryParams.toString()
      ? `/token-usage/cost/total?${queryParams}`
      : "/token-usage/cost/total";
    const response = await api.get(url);
    return response.data;
  },

  async getModelPricing(): Promise<{ models: ModelPricing[] }> {
    const response = await api.get("/token-usage/models/pricing");
    return response.data;
  },

  async getModelPricingByName(modelName: string): Promise<ModelPricing> {
    const response = await api.get(
      `/token-usage/models/${encodeURIComponent(modelName)}/pricing`
    );
    return response.data;
  },
};

export default api;
