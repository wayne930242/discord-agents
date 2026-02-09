import { useMemo, useState } from "react";
import { Layout } from "@/components/Layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useBotQueuesWithOptions } from "@/hooks/useBotQueues";

export function QueueMonitor() {
  const [statusFilter, setStatusFilter] = useState<"all" | "running" | "idle">("all");
  const [expandedBots, setExpandedBots] = useState<Record<string, boolean>>({});

  const { data: snapshot = {}, isLoading } = useBotQueuesWithOptions({
    includeIdleBots: true,
    topNChannels: 50,
    refetchIntervalMs: 3000,
  });

  const rows = useMemo(() => {
    return Object.entries(snapshot)
      .map(([botId, metrics]) => ({
        botId,
        totalPending: metrics.total_pending,
        status: metrics.status || "unknown",
        updatedAt: metrics.updated_at,
        channels: Object.entries(metrics.channels)
          .map(([channelId, pending]) => ({ channelId, pending }))
          .sort((a, b) => b.pending - a.pending),
      }))
      .sort((a, b) => b.totalPending - a.totalPending);
  }, [snapshot]);

  const totalPending = rows.reduce((acc, row) => acc + row.totalPending, 0);
  const filteredRows = rows.filter((row) => {
    if (statusFilter === "all") {
      return true;
    }
    return row.status === statusFilter;
  });

  const toggleExpand = (botId: string) => {
    setExpandedBots((prev) => ({ ...prev, [botId]: !prev[botId] }));
  };

  return (
    <Layout
      title="Queue 監控"
      subtitle="即時監控每個 Bot 與 Channel 的待處理佇列"
      showBackButton
      backTo="/dashboard"
    >
      <Card>
        <CardHeader>
          <CardTitle>Queue 概覽</CardTitle>
          <CardDescription>
            目前總待處理: {totalPending}，每 3 秒更新一次（顯示 {filteredRows.length}/{rows.length} 個 Bot）
          </CardDescription>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant={statusFilter === "all" ? "default" : "outline"}
              onClick={() => setStatusFilter("all")}
            >
              全部
            </Button>
            <Button
              size="sm"
              variant={statusFilter === "running" ? "default" : "outline"}
              onClick={() => setStatusFilter("running")}
            >
              running
            </Button>
            <Button
              size="sm"
              variant={statusFilter === "idle" ? "default" : "outline"}
              onClick={() => setStatusFilter("idle")}
            >
              idle
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-muted-foreground">載入中...</div>
          ) : filteredRows.length === 0 ? (
            <div className="text-muted-foreground">尚無可監控的 Bot 佇列資料。</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Bot</TableHead>
                  <TableHead>狀態</TableHead>
                  <TableHead>總待處理</TableHead>
                  <TableHead>Top Channels</TableHead>
                  <TableHead>更新時間</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredRows.map((row) => (
                  <TableRow key={row.botId}>
                    <TableCell className="font-medium">{row.botId}</TableCell>
                    <TableCell>
                      <Badge variant={row.status === "running" ? "default" : "secondary"}>
                        {row.status}
                      </Badge>
                    </TableCell>
                    <TableCell>{row.totalPending}</TableCell>
                    <TableCell className="text-xs">
                      {row.channels.length === 0 ? (
                        <span className="text-muted-foreground">無</span>
                      ) : (
                        <>
                          {(expandedBots[row.botId] ? row.channels : row.channels.slice(0, 5)).map((channel) => (
                            <div key={channel.channelId}>
                              #{channel.channelId}: {channel.pending}
                            </div>
                          ))}
                          {row.channels.length > 5 && (
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-6 px-1 mt-1 text-xs"
                              onClick={() => toggleExpand(row.botId)}
                            >
                              {expandedBots[row.botId] ? "收合" : `展開全部 (${row.channels.length})`}
                            </Button>
                          )}
                        </>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {row.updatedAt || "-"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </Layout>
  );
}
