import React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { botAPI, type Bot, type BotUpdate, type Agent } from "@/lib/api";

const botFormSchema = z.object({
  token: z.string().min(1, "Token 不能為空"),
  command_prefix: z.string().min(1, "指令前綴不能為空"),
  error_message: z.string(),
  agent_id: z.string().optional(),
});

type BotFormValues = z.infer<typeof botFormSchema>;

interface BotEditDialogProps {
  bot: Bot | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agents: Agent[];
  onEditAgent?: (agent: Agent) => void;
}

export function BotEditDialog({
  bot,
  open,
  onOpenChange,
  agents,
  onEditAgent,
}: BotEditDialogProps) {
  const queryClient = useQueryClient();

  const form = useForm<BotFormValues>({
    resolver: zodResolver(botFormSchema),
    defaultValues: {
      token: "",
      command_prefix: "!",
      error_message: "",
      agent_id: "none",
    },
  });

  // Reset form when bot changes
  React.useEffect(() => {
    if (bot) {
      form.reset({
        token: bot.token,
        command_prefix: bot.command_prefix,
        error_message: bot.error_message,
        agent_id: bot.agent_id?.toString() || "none",
      });
    }
  }, [bot, form]);

  const updateBotMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: BotUpdate }) =>
      botAPI.updateBot(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bots"] });
      onOpenChange(false);
    },
  });

  const onSubmit = async (data: BotFormValues) => {
    if (!bot) return;

    const updateData: BotUpdate = {
      token: data.token,
      command_prefix: data.command_prefix,
      error_message: data.error_message,
      agent_id:
        data.agent_id && data.agent_id !== "none"
          ? Number(data.agent_id)
          : undefined,
    };

    await updateBotMutation.mutateAsync({ id: bot.id, data: updateData });
  };

  if (!bot) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>編輯機器人 #{bot.id}</DialogTitle>
          <DialogDescription>修改機器人的配置設定</DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="token"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>機器人 Token</FormLabel>
                  <FormControl>
                    <Input
                      type="password"
                      placeholder="Discord Bot Token"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="command_prefix"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>指令前綴</FormLabel>
                  <FormControl>
                    <Input placeholder="!" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="error_message"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>錯誤訊息模板</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="當機器人遇到錯誤時顯示給用戶的訊息"
                      className="resize-none"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="agent_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>代理程式</FormLabel>
                  <div className="flex gap-2">
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="選擇代理程式" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="none">無代理程式</SelectItem>
                        {agents.map((agent) => (
                          <SelectItem
                            key={agent.id}
                            value={agent.id.toString()}
                          >
                            {agent.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {bot.agent && onEditAgent && (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => onEditAgent(bot.agent!)}
                      >
                        編輯
                      </Button>
                    )}
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                取消
              </Button>
              <Button type="submit" disabled={updateBotMutation.isPending}>
                {updateBotMutation.isPending ? "更新中..." : "更新機器人"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
