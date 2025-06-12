import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useQuery } from "@tanstack/react-query";
import { Plus, Edit, Bot, Settings, DollarSign } from "lucide-react";
import { agentAPI, type Agent } from "@/lib/api";
import { AgentEditDialog } from "@/components/AgentEditDialog";
import { Layout } from "@/components/Layout";

export function AgentManagement() {
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  // Fetch agents
  const { data: agents = [], isLoading } = useQuery({
    queryKey: ["agents"],
    queryFn: agentAPI.getAgents,
  });

  const handleCreateAgent = () => {
    setSelectedAgent(null);
    setIsDialogOpen(true);
  };

  const handleEditAgent = (agent: Agent) => {
    setSelectedAgent(agent);
    setIsDialogOpen(true);
  };

  return (
    <Layout
      title="Agent 管理"
      subtitle="創建和管理 AI Agent 配置"
      showBackButton
      backTo="/dashboard"
      extraActions={
        <Button onClick={handleCreateAgent}>
          <Plus className="h-4 w-4 mr-2" />
          創建 Agent
        </Button>
      }
    >
      <div className="grid gap-6 md:grid-cols-3 mb-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">總 Agents</CardTitle>
            <Bot className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{agents.length}</div>
            <p className="text-xs text-muted-foreground">已配置的 AI Agents</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">使用中</CardTitle>
            <Settings className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {agents.length}
            </div>
            <p className="text-xs text-muted-foreground">正在被機器人使用</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">模型分佈</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {new Set(agents.map((a) => a.agent_model)).size}
            </div>
            <p className="text-xs text-muted-foreground">不同的 AI 模型</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Agents 列表</CardTitle>
          <CardDescription>管理您的 AI Agent 配置</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8">載入中...</div>
          ) : agents.length === 0 ? (
            <div className="text-center py-8">
              <Bot className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium">還沒有 Agents</h3>
              <p className="text-muted-foreground mb-4">
                創建您的第一個 AI Agent 來開始使用
              </p>
              <Button onClick={handleCreateAgent}>
                <Plus className="h-4 w-4 mr-2" />
                創建 Agent
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>名稱</TableHead>
                    <TableHead>描述</TableHead>
                    <TableHead>模型</TableHead>
                    <TableHead>工具</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {agents.map((agent) => (
                    <TableRow key={agent.id}>
                      <TableCell className="font-medium">
                        {agent.name}
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate">
                        {agent.description}
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">{agent.agent_model}</Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {agent.tools.slice(0, 3).map((tool) => (
                            <Badge
                              key={tool}
                              variant="outline"
                              className="text-xs"
                            >
                              {tool}
                            </Badge>
                          ))}
                          {agent.tools.length > 3 && (
                            <Badge variant="outline" className="text-xs">
                              +{agent.tools.length - 3}
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleEditAgent(agent)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <AgentEditDialog
        agent={selectedAgent}
        open={isDialogOpen}
        onOpenChange={setIsDialogOpen}
      />
    </Layout>
  );
}
