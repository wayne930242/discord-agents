import { useQuery } from "@tanstack/react-query";
import { botAPI, type Bot, type BotQueueMetrics, type BotQueueSnapshot } from "@/lib/api";

export interface BotQueueView {
  totalPending: number;
  channels: Array<{ channelId: string; pending: number }>;
  updatedAt?: string;
}

export const getBotQueueView = (
  bot: Bot,
  queueSnapshot: BotQueueSnapshot
): BotQueueView => {
  const key = `bot_${bot.id}`;
  const metrics: BotQueueMetrics | undefined = queueSnapshot[key];
  if (!metrics) {
    return { totalPending: 0, channels: [] };
  }

  const channels = Object.entries(metrics.channels)
    .map(([channelId, pending]) => ({ channelId, pending }))
    .sort((a, b) => b.pending - a.pending);

  return {
    totalPending: metrics.total_pending,
    channels,
    updatedAt: metrics.updated_at,
  };
};

export function useBotQueues() {
  return useQuery({
    queryKey: ["bot-queues"],
    queryFn: botAPI.getBotQueues,
    refetchInterval: 3000,
  });
}
