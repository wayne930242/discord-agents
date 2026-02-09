import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import { Plus, Settings, Play, Trash2, Square } from "lucide-react";

import {
  botAPI,
  agentAPI,
  type Bot,
  type BotCreate,
  type Agent,
} from "@/lib/api";
import { getBotQueueView, useBotQueues } from "@/hooks/useBotQueues";
import { BotQueueCell } from "@/components/BotQueueCell";
import { BotEditDialog } from "@/components/BotEditDialog";
import { AgentEditDialog } from "@/components/AgentEditDialog";
import { Layout } from "@/components/Layout";

export function BotManagement() {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingBot, setEditingBot] = useState<Bot | null>(null);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [newBot, setNewBot] = useState<Partial<BotCreate>>({
    token: "",
    command_prefix: "!",
    error_message: "",
    dm_whitelist: [],
    srv_whitelist: [],
    use_function_map: {},
  });

  const queryClient = useQueryClient();

  // Fetch bots data
  const {
    data: bots = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: ["bots"],
    queryFn: botAPI.getBots,
  });

  // Fetch agents data for dropdown
  const { data: agents = [] } = useQuery({
    queryKey: ["agents"],
    queryFn: agentAPI.getAgents,
  });

  // Fetch bot status
  const { data: botStatus = {} } = useQuery({
    queryKey: ["bot-status"],
    queryFn: botAPI.getBotStatus,
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  // Fetch per-bot per-channel queue metrics
  const { data: botQueues = {} } = useBotQueues();

  // Create bot mutation
  const createBotMutation = useMutation({
    mutationFn: botAPI.createBot,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bots"] });
      queryClient.invalidateQueries({ queryKey: ["bot-status"] });
      queryClient.invalidateQueries({ queryKey: ["bot-queues"] });
      setShowCreateForm(false);
      setNewBot({
        token: "",
        command_prefix: "!",
        error_message: "",
        dm_whitelist: [],
        srv_whitelist: [],
        use_function_map: {},
      });
    },
  });

  // Start bot mutation
  const startBotMutation = useMutation({
    mutationFn: botAPI.startBot,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bots"] });
      queryClient.invalidateQueries({ queryKey: ["bot-status"] });
      queryClient.invalidateQueries({ queryKey: ["bot-queues"] });
    },
  });

  // Stop bot mutation
  const stopBotMutation = useMutation({
    mutationFn: botAPI.stopBot,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bots"] });
      queryClient.invalidateQueries({ queryKey: ["bot-status"] });
      queryClient.invalidateQueries({ queryKey: ["bot-queues"] });
    },
  });

  // Delete bot mutation
  const deleteBotMutation = useMutation({
    mutationFn: botAPI.deleteBot,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bots"] });
      queryClient.invalidateQueries({ queryKey: ["bot-status"] });
      queryClient.invalidateQueries({ queryKey: ["bot-queues"] });
    },
  });

  const getBotStatus = (bot: Bot): string => {
    const botId = `bot_${bot.id}`;
    return botStatus[botId] || "idle";
  };

  const isRunning = (bot: Bot): boolean => {
    const status = getBotStatus(bot);
    return status === "running" || status === "starting";
  };

  const getStatusBadge = (bot: Bot) => {
    const status = getBotStatus(bot);

    switch (status) {
      case "running":
        return <Badge className="bg-green-100 text-green-800">運行中</Badge>;
      case "starting":
        return <Badge className="bg-yellow-100 text-yellow-800">啟動中</Badge>;
      case "stopping":
        return <Badge className="bg-orange-100 text-orange-800">停止中</Badge>;
      case "should_start":
        return <Badge className="bg-blue-100 text-blue-800">等待啟動</Badge>;
      case "should_stop":
        return <Badge className="bg-red-100 text-red-800">等待停止</Badge>;
      case "idle":
      default:
        return <Badge variant="secondary">離線</Badge>;
    }
  };

  const toggleBotStatus = async (bot: Bot) => {
    if (isRunning(bot)) {
      await stopBotMutation.mutateAsync(bot.id);
    } else {
      await startBotMutation.mutateAsync(bot.id);
    }
  };

  const deleteBot = async (id: number) => {
    if (window.confirm("確定要刪除這個機器人嗎？")) {
      await deleteBotMutation.mutateAsync(id);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newBot.token) {
      alert("請輸入機器人 Token");
      return;
    }
    await createBotMutation.mutateAsync(newBot as BotCreate);
  };

  const openBotEditor = (bot: Bot) => {
    setEditingBot(bot);
  };

  if (isLoading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex justify-center items-center h-64">
          <div className="text-lg">載入中...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex justify-center items-center h-64">
          <div className="text-lg text-red-600">載入資料時發生錯誤</div>
        </div>
      </div>
    );
  }

  return (
    <Layout
      title="機器人管理"
      subtitle="管理你的 Discord 機器人配置和狀態"
      showBackButton
      backTo="/dashboard"
      extraActions={
        <Button onClick={() => setShowCreateForm(!showCreateForm)}>
          <Plus className="h-4 w-4 mr-2" />
          新增機器人
        </Button>
      }
    >
      {showCreateForm && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>新增機器人</CardTitle>
            <CardDescription>配置一個新的 Discord 機器人</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="botToken">機器人 Token *</Label>
                <Input
                  id="botToken"
                  type="password"
                  placeholder="輸入 Discord Bot Token"
                  value={newBot.token || ""}
                  onChange={(e) =>
                    setNewBot({ ...newBot, token: e.target.value })
                  }
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="commandPrefix">指令前綴</Label>
                  <Input
                    id="commandPrefix"
                    placeholder="!"
                    value={newBot.command_prefix || "!"}
                    onChange={(e) =>
                      setNewBot({ ...newBot, command_prefix: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="agent">代理人</Label>
                  <select
                    id="agent"
                    className="w-full p-2 border border-input rounded-md bg-background"
                    value={newBot.agent_id || ""}
                    onChange={(e) =>
                      setNewBot({
                        ...newBot,
                        agent_id: e.target.value
                          ? Number(e.target.value)
                          : undefined,
                      })
                    }
                  >
                    <option value="">選擇代理人 (可選)</option>
                    {agents.map((agent) => (
                      <option key={agent.id} value={agent.id}>
                        {agent.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex gap-2">
                <Button type="submit" disabled={createBotMutation.isPending}>
                  {createBotMutation.isPending ? "創建中..." : "創建機器人"}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setShowCreateForm(false)}
                >
                  取消
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>機器人列表</CardTitle>
          <CardDescription>
            目前配置的所有機器人 ({bots.length} 個)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {bots.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              還沒有任何機器人，點擊上方的「新增機器人」按鈕來創建第一個機器人。
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>狀態</TableHead>
                  <TableHead>指令前綴</TableHead>
                  <TableHead>代理人</TableHead>
                  <TableHead>Queue</TableHead>
                  <TableHead>Token</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {bots.map((bot) => {
                  const queueView = getBotQueueView(bot, botQueues);
                  return (
                    <TableRow key={bot.id}>
                    <TableCell className="font-medium">#{bot.id}</TableCell>
                    <TableCell>{getStatusBadge(bot)}</TableCell>
                    <TableCell>{bot.command_prefix}</TableCell>
                    <TableCell>{bot.agent?.name || "無"}</TableCell>
                    <TableCell><BotQueueCell queueView={queueView} /></TableCell>
                    <TableCell className="font-mono text-sm">
                      {bot.token.substring(0, 20)}...
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => toggleBotStatus(bot)}
                          disabled={
                            startBotMutation.isPending ||
                            stopBotMutation.isPending
                          }
                          title={isRunning(bot) ? "停止機器人" : "啟動機器人"}
                        >
                          {isRunning(bot) ? (
                            <Square className="h-4 w-4" />
                          ) : (
                            <Play className="h-4 w-4" />
                          )}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => openBotEditor(bot)}
                        >
                          <Settings className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => deleteBot(bot.id)}
                          disabled={deleteBotMutation.isPending}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Edit Dialogs */}
      <BotEditDialog
        bot={editingBot}
        open={!!editingBot}
        onOpenChange={(open) => !open && setEditingBot(null)}
        agents={agents}
        onEditAgent={(agent) => {
          setEditingBot(null);
          setEditingAgent(agent);
        }}
      />

      <AgentEditDialog
        agent={editingAgent}
        open={!!editingAgent}
        onOpenChange={(open) => !open && setEditingAgent(null)}
      />
    </Layout>
  );
}
