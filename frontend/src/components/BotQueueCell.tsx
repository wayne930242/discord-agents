import type { BotQueueView } from "@/hooks/useBotQueues";

interface BotQueueCellProps {
  queueView: BotQueueView;
}

export function BotQueueCell({ queueView }: BotQueueCellProps) {
  const topChannels = queueView.channels.slice(0, 2);

  return (
    <div className="text-xs">
      <div className="font-medium">Pending: {queueView.totalPending}</div>
      {topChannels.length > 0 ? (
        <div className="text-muted-foreground">
          {topChannels.map((item) => (
            <div key={item.channelId}>
              #{item.channelId}: {item.pending}
            </div>
          ))}
        </div>
      ) : (
        <div className="text-muted-foreground">無待處理</div>
      )}
    </div>
  );
}
