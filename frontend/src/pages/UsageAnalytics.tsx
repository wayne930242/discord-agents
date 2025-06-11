import { useState, useMemo } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import {
  TrendingUp,
  BarChart3,
  DollarSign,
  Calendar,
  Filter,
  RefreshCw,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { tokenUsageAPI, agentAPI } from "@/lib/api";
import { Layout } from "@/components/Layout";

interface TimeFilter {
  year?: number;
  month?: number;
}

export function UsageAnalytics() {
  const [timeFilter, setTimeFilter] = useState<TimeFilter>({});
  const [selectedAgent, setSelectedAgent] = useState<number | undefined>();
  const [selectedModel, setSelectedModel] = useState<string | undefined>();

  // Generate year and month options
  const currentYear = new Date().getFullYear();
  const years = Array.from({ length: 5 }, (_, i) => currentYear - i);
  const months = [
    { value: 1, label: "一月" },
    { value: 2, label: "二月" },
    { value: 3, label: "三月" },
    { value: 4, label: "四月" },
    { value: 5, label: "五月" },
    { value: 6, label: "六月" },
    { value: 7, label: "七月" },
    { value: 8, label: "八月" },
    { value: 9, label: "九月" },
    { value: 10, label: "十月" },
    { value: 11, label: "十一月" },
    { value: 12, label: "十二月" },
  ];

  // Fetch agents for filter dropdown
  const { data: agents = [] } = useQuery({
    queryKey: ["agents"],
    queryFn: agentAPI.getAgents,
  });

  // Fetch usage data based on filters
  const { data: allUsage = [], isLoading: usageLoading } = useQuery({
    queryKey: ["all-usage", timeFilter],
    queryFn: () =>
      tokenUsageAPI.getAllUsage({
        year: timeFilter.year,
        month: timeFilter.month,
      }),
    refetchInterval: 30000,
  });

  const { data: agentSummary = [], isLoading: summaryLoading } = useQuery({
    queryKey: ["usage-summary-by-agent", timeFilter],
    queryFn: () =>
      tokenUsageAPI.getSummaryByAgent({
        year: timeFilter.year,
        month: timeFilter.month,
      }),
    refetchInterval: 30000,
  });

  const { data: modelSummary = [], isLoading: modelLoading } = useQuery({
    queryKey: ["usage-summary-by-model", timeFilter],
    queryFn: () =>
      tokenUsageAPI.getSummaryByModel({
        year: timeFilter.year,
        month: timeFilter.month,
      }),
    refetchInterval: 30000,
  });

  const { data: monthlyTrend = [], isLoading: trendLoading } = useQuery({
    queryKey: ["monthly-trend", selectedAgent, selectedModel],
    queryFn: () =>
      tokenUsageAPI.getMonthlyTrend({
        agentId: selectedAgent,
        modelName: selectedModel,
        limit: 12,
      }),
    refetchInterval: 30000,
  });

  const { data: totalCost } = useQuery({
    queryKey: ["total-cost", timeFilter, selectedAgent],
    queryFn: () =>
      tokenUsageAPI.getTotalCost({
        agentId: selectedAgent,
        year: timeFilter.year,
        month: timeFilter.month,
      }),
    refetchInterval: 30000,
  });

  // Filter and process data based on selections
  const filteredUsage = useMemo(() => {
    let filtered = allUsage;

    if (selectedAgent) {
      filtered = filtered.filter((usage) => usage.agent_id === selectedAgent);
    }

    if (selectedModel) {
      filtered = filtered.filter((usage) => usage.model_name === selectedModel);
    }

    return filtered;
  }, [allUsage, selectedAgent, selectedModel]);

  const filteredAgentSummary = useMemo(() => {
    if (selectedAgent) {
      return agentSummary.filter(
        (summary) => summary.agent_id === selectedAgent
      );
    }
    return agentSummary;
  }, [agentSummary, selectedAgent]);

  const filteredModelSummary = useMemo(() => {
    if (selectedModel) {
      return modelSummary.filter(
        (summary) => summary.model_name === selectedModel
      );
    }
    return modelSummary;
  }, [modelSummary, selectedModel]);

  // Get unique models from usage data
  const availableModels = useMemo(() => {
    const models = new Set(allUsage.map((usage) => usage.model_name));
    return Array.from(models).sort();
  }, [allUsage]);

  const handleResetFilters = () => {
    setTimeFilter({});
    setSelectedAgent(undefined);
    setSelectedModel(undefined);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 4,
    }).format(amount);
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat("zh-TW").format(num);
  };

  const getTimeFilterDisplay = () => {
    if (timeFilter.year && timeFilter.month) {
      return `${timeFilter.year} 年 ${timeFilter.month} 月`;
    } else if (timeFilter.year) {
      return `${timeFilter.year} 年`;
    }
    return "全部時間";
  };

  const isLoading =
    usageLoading || summaryLoading || modelLoading || trendLoading;

  return (
    <Layout
      title="用量分析"
      subtitle="詳細的 AI 模型使用量和成本分析"
      showBackButton
      backTo="/dashboard"
      extraActions={
        <Button
          variant="outline"
          size="sm"
          onClick={() => window.location.reload()}
          disabled={isLoading}
        >
          {isLoading ? (
            <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4 mr-2" />
          )}
          重新整理
        </Button>
      }
    >
      {/* Filters */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="w-5 h-5" />
            篩選條件
          </CardTitle>
          <CardDescription>選擇時間範圍、代理或模型來篩選資料</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {/* Year Filter */}
            <div>
              <Label htmlFor="year">年份</Label>
              <Select
                value={timeFilter.year?.toString() || "all"}
                onValueChange={(value) =>
                  setTimeFilter((prev) => ({
                    ...prev,
                    year: value === "all" ? undefined : parseInt(value),
                  }))
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="選擇年份" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部年份</SelectItem>
                  {years.map((year) => (
                    <SelectItem key={year} value={year.toString()}>
                      {year}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Month Filter */}
            <div>
              <Label htmlFor="month">月份</Label>
              <Select
                value={timeFilter.month?.toString() || "all"}
                onValueChange={(value) =>
                  setTimeFilter((prev) => ({
                    ...prev,
                    month: value === "all" ? undefined : parseInt(value),
                  }))
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="選擇月份" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部月份</SelectItem>
                  {months.map((month) => (
                    <SelectItem
                      key={month.value}
                      value={month.value.toString()}
                    >
                      {month.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Agent Filter */}
            <div>
              <Label htmlFor="agent">代理</Label>
              <Select
                value={selectedAgent?.toString() || "all"}
                onValueChange={(value) =>
                  setSelectedAgent(
                    value === "all" ? undefined : parseInt(value)
                  )
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="選擇代理" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部代理</SelectItem>
                  {agents.map((agent) => (
                    <SelectItem key={agent.id} value={agent.id.toString()}>
                      {agent.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Model Filter */}
            <div>
              <Label htmlFor="model">模型</Label>
              <Select
                value={selectedModel || "all"}
                onValueChange={(value) =>
                  setSelectedModel(value === "all" ? undefined : value)
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="選擇模型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部模型</SelectItem>
                  {availableModels.map((model) => (
                    <SelectItem key={model} value={model}>
                      {model}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Reset Button */}
            <div className="flex items-end">
              <Button
                variant="outline"
                onClick={handleResetFilters}
                className="w-full"
              >
                重置篩選
              </Button>
            </div>
          </div>

          {/* Active Filters Display */}
          <div className="mt-4 flex items-center gap-2 flex-wrap">
            <span className="text-sm text-gray-600">當前篩選:</span>
            <Badge variant="secondary">
              <Calendar className="w-3 h-3 mr-1" />
              {getTimeFilterDisplay()}
            </Badge>
            {selectedAgent && (
              <Badge variant="secondary">
                代理: {agents.find((a) => a.id === selectedAgent)?.name}
              </Badge>
            )}
            {selectedModel && (
              <Badge variant="secondary">模型: {selectedModel}</Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">總成本</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {totalCost ? formatCurrency(totalCost.total_cost) : "$0.0000"}
            </div>
            <p className="text-xs text-muted-foreground">
              輸入:{" "}
              {totalCost
                ? formatCurrency(totalCost.total_input_cost)
                : "$0.0000"}{" "}
              | 輸出:{" "}
              {totalCost
                ? formatCurrency(totalCost.total_output_cost)
                : "$0.0000"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">總 Token 數</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatNumber(
                filteredUsage.reduce(
                  (sum, usage) => sum + usage.total_tokens,
                  0
                )
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              輸入:{" "}
              {formatNumber(
                filteredUsage.reduce(
                  (sum, usage) => sum + usage.input_tokens,
                  0
                )
              )}{" "}
              | 輸出:{" "}
              {formatNumber(
                filteredUsage.reduce(
                  (sum, usage) => sum + usage.output_tokens,
                  0
                )
              )}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">活躍代理</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {filteredAgentSummary.length}
            </div>
            <p className="text-xs text-muted-foreground">
              有使用記錄的代理數量
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">使用模型</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {filteredModelSummary.length}
            </div>
            <p className="text-xs text-muted-foreground">
              有使用記錄的模型數量
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Data Tables */}
      <Tabs defaultValue="agents" className="space-y-6">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="agents">按代理分組</TabsTrigger>
          <TabsTrigger value="models">按模型分組</TabsTrigger>
          <TabsTrigger value="detailed">詳細記錄</TabsTrigger>
        </TabsList>

        <TabsContent value="agents">
          <Card>
            <CardHeader>
              <CardTitle>代理使用統計</CardTitle>
              <CardDescription>
                每個代理的 Token 使用量和成本統計
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>代理名稱</TableHead>
                    <TableHead className="text-right">輸入 Token</TableHead>
                    <TableHead className="text-right">輸出 Token</TableHead>
                    <TableHead className="text-right">總 Token</TableHead>
                    <TableHead className="text-right">總成本</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredAgentSummary.map((agent) => (
                    <TableRow key={agent.agent_id}>
                      <TableCell className="font-medium">
                        {agent.agent_name}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatNumber(agent.total_input_tokens)}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatNumber(agent.total_output_tokens)}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatNumber(agent.total_tokens)}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatCurrency(agent.total_cost)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {filteredAgentSummary.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  沒有找到符合篩選條件的代理資料
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="models">
          <Card>
            <CardHeader>
              <CardTitle>模型使用統計</CardTitle>
              <CardDescription>
                每個模型的 Token 使用量和成本統計
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>模型名稱</TableHead>
                    <TableHead className="text-right">輸入 Token</TableHead>
                    <TableHead className="text-right">輸出 Token</TableHead>
                    <TableHead className="text-right">總 Token</TableHead>
                    <TableHead className="text-right">總成本</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredModelSummary.map((model) => (
                    <TableRow key={model.model_name}>
                      <TableCell className="font-medium">
                        {model.model_name}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatNumber(model.total_input_tokens)}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatNumber(model.total_output_tokens)}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatNumber(model.total_tokens)}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatCurrency(model.total_cost)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {filteredModelSummary.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  沒有找到符合篩選條件的模型資料
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="detailed">
          <Card>
            <CardHeader>
              <CardTitle>詳細使用記錄</CardTitle>
              <CardDescription>
                所有使用記錄的詳細列表 ({getTimeFilterDisplay()})
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>代理</TableHead>
                    <TableHead>模型</TableHead>
                    <TableHead>時間</TableHead>
                    <TableHead className="text-right">輸入 Token</TableHead>
                    <TableHead className="text-right">輸出 Token</TableHead>
                    <TableHead className="text-right">成本</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredUsage.map((usage) => (
                    <TableRow key={usage.id}>
                      <TableCell className="font-medium">
                        {usage.agent_name}
                      </TableCell>
                      <TableCell>{usage.model_name}</TableCell>
                      <TableCell>
                        {usage.year} 年 {usage.month} 月
                      </TableCell>
                      <TableCell className="text-right">
                        {formatNumber(usage.input_tokens)}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatNumber(usage.output_tokens)}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatCurrency(usage.total_cost)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {filteredUsage.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  沒有找到符合篩選條件的使用記錄
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Monthly Trend */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>月度趨勢</CardTitle>
          <CardDescription>過去 12 個月的使用量和成本趨勢</CardDescription>
        </CardHeader>
        <CardContent>
          {monthlyTrend.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>月份</TableHead>
                  <TableHead className="text-right">總 Token</TableHead>
                  <TableHead className="text-right">總成本</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {monthlyTrend.map((trend) => (
                  <TableRow key={trend.month_year}>
                    <TableCell>{trend.month_year}</TableCell>
                    <TableCell className="text-right">
                      {formatNumber(trend.total_tokens)}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatCurrency(trend.total_cost)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-center py-8 text-gray-500">暫無趨勢資料</div>
          )}
        </CardContent>
      </Card>
    </Layout>
  );
}
