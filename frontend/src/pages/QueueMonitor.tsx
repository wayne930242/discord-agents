import { useMemo } from "react";
import { Layout } from "@/components/Layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { useBotQueuesWithOptions } from "@/hooks/useBotQueues";

export function QueueMonitor() {
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
            目前總待處理: {totalPending}，每 3 秒更新一次
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-muted-foreground">載入中...</div>
          ) : rows.length === 0 ? (
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
                {rows.map((row) => (
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
                        row.channels.slice(0, 5).map((channel) => (
                          <div key={channel.channelId}>
                            #{channel.channelId}: {channel.pending}
                          </div>
                        ))
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
