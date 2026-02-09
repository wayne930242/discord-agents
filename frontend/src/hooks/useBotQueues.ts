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
  return useBotQueuesWithOptions();
}

export function useBotQueuesWithOptions(options?: {
  topNChannels?: number;
  includeIdleBots?: boolean;
  refetchIntervalMs?: number;
}) {
  const topNChannels = options?.topNChannels ?? 10;
  const includeIdleBots = options?.includeIdleBots ?? false;
  return useQuery({
    queryKey: ["bot-queues", topNChannels, includeIdleBots],
    queryFn: () =>
      botAPI.getBotQueues({
        topNChannels,
        includeIdleBots,
      }),
    refetchInterval: options?.refetchIntervalMs ?? 3000,
  });
}
