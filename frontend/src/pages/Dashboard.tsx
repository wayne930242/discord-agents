import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Bot, Activity, LogOut, DollarSign, TrendingUp } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { botAPI, authAPI, tokenUsageAPI, type Bot as BotType } from "@/lib/api";

export function Dashboard() {
  const navigate = useNavigate();

  // Fetch bots data for statistics
  const { data: bots = [], isLoading } = useQuery({
    queryKey: ["bots"],
    queryFn: botAPI.getBots,
  });

  // Fetch bot status
  const { data: botStatus = {} } = useQuery({
    queryKey: ["bot-status"],
    queryFn: botAPI.getBotStatus,
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  // Fetch token usage data
  const { data: totalCost } = useQuery({
    queryKey: ["total-cost"],
    queryFn: () => tokenUsageAPI.getTotalCost(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const { data: agentSummary = [] } = useQuery({
    queryKey: ["usage-summary-by-agent"],
    queryFn: () => tokenUsageAPI.getSummaryByAgent(),
    refetchInterval: 30000,
  });

  const handleLogout = () => {
    authAPI.logout();
    navigate("/login");
  };

  const getBotStatus = (bot: BotType): string => {
    const botId = `bot_${bot.id}`;
    return botStatus[botId] || "idle";
  };

  const isRunning = (bot: BotType): boolean => {
    const status = getBotStatus(bot);
    return status === "running" || status === "starting";
  };

  // Get bot usage summary from agent summary
  const getBotUsage = (bot: BotType) => {
    if (!bot.agent_id || !agentSummary) return null;
    return agentSummary.find((summary) => summary.agent_id === bot.agent_id);
  };

  // Calculate statistics using real bot status
  const activeBots = bots.filter(isRunning).length;
  const totalBots = bots.length;
  const offlineBots = totalBots - activeBots;

  return (
    <div className="container mx-auto p-6">
      <div className="mb-8 flex justify-between items-start">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">
            Discord Agents Dashboard
          </h1>
          <p className="text-muted-foreground mt-2">
            管理你的 Discord 機器人和代理程式
          </p>
        </div>
        <Button variant="outline" onClick={handleLogout}>
          <LogOut className="h-4 w-4 mr-2" />
          登出
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">活躍機器人</CardTitle>
            <Bot className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="text-2xl font-bold">載入中...</div>
            ) : (
              <>
                <div className="text-2xl font-bold text-green-600">
                  {activeBots}
                </div>
                <p className="text-xs text-muted-foreground">
                  總共 {totalBots} 個機器人
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">離線機器人</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="text-2xl font-bold">載入中...</div>
            ) : (
              <>
                <div className="text-2xl font-bold text-red-600">
                  {offlineBots}
                </div>
                <p className="text-xs text-muted-foreground">
                  {offlineBots > 0 ? "需要檢查錯誤" : "全部正常運作"}
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">總用量費用</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {totalCost ? (
              <>
                <div className="text-2xl font-bold text-blue-600">
                  ${totalCost.total_cost.toFixed(4)}
                </div>
                <p className="text-xs text-muted-foreground">
                  輸入: ${totalCost.total_input_cost.toFixed(4)} | 輸出: $
                  {totalCost.total_output_cost.toFixed(4)}
                </p>
              </>
            ) : (
              <>
                <div className="text-2xl font-bold">載入中...</div>
                <p className="text-xs text-muted-foreground">計算總費用中</p>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="mt-8">
        <Card>
          <CardHeader>
            <CardTitle>快速操作</CardTitle>
            <CardDescription>常用的管理功能</CardDescription>
          </CardHeader>
          <CardContent className="flex gap-4">
            <Button asChild>
              <Link to="/bots">管理機器人</Link>
            </Button>
            <Button variant="outline" asChild>
              <Link to="/usage">
                <TrendingUp className="h-4 w-4 mr-2" />
                用量分析
              </Link>
            </Button>
            <Button variant="outline" disabled>
              查看日誌 (開發中)
            </Button>
            <Button variant="outline" disabled>
              系統設定 (開發中)
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Bot list preview */}
      {!isLoading && bots.length > 0 && (
        <div className="mt-8">
          <Card>
            <CardHeader>
              <CardTitle>機器人概覽</CardTitle>
              <CardDescription>最近的機器人狀態</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {bots.slice(0, 5).map((bot) => {
                  const usage = getBotUsage(bot);
                  return (
                    <div
                      key={bot.id}
                      className="flex items-center justify-between p-3 border rounded"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">機器人 #{bot.id}</span>
                          <span className="text-sm text-muted-foreground">
                            前綴: {bot.command_prefix}
                          </span>
                        </div>
                        {usage && (
                          <div className="text-xs text-muted-foreground mt-1">
                            總 Tokens: {usage.total_tokens.toLocaleString()} |
                            費用: ${usage.total_cost.toFixed(4)}
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        {bot.agent && (
                          <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                            {bot.agent.name}
                          </span>
                        )}
                        {usage && (
                          <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded">
                            ${usage.total_cost.toFixed(4)}
                          </span>
                        )}
                        <span
                          className={`text-xs px-2 py-1 rounded ${
                            isRunning(bot)
                              ? "bg-green-100 text-green-800"
                              : "bg-red-100 text-red-800"
                          }`}
                        >
                          {isRunning(bot) ? "線上" : "離線"}
                        </span>
                      </div>
                    </div>
                  );
                })}
                {bots.length > 5 && (
                  <div className="text-center pt-2">
                    <Button variant="outline" size="sm" asChild>
                      <Link to="/bots">查看全部 {bots.length} 個機器人</Link>
                    </Button>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
