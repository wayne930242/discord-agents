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
import { Badge } from "@/components/ui/badge";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { agentAPI, type Agent } from "@/lib/api";
import { X } from "lucide-react";

const agentFormSchema = z.object({
  name: z.string().min(1, "名稱不能為空"),
  description: z.string().min(1, "描述不能為空"),
  role_instructions: z.string().min(1, "角色指令不能為空"),
  tool_instructions: z.string().min(1, "工具指令不能為空"),
  agent_model: z.string().min(1, "模型不能為空"),
  tools: z.array(z.string()),
});

type AgentFormValues = z.infer<typeof agentFormSchema>;

interface AgentEditDialogProps {
  agent: Agent | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const availableModels = [
  "gemini-2.5-flash-preview-04-17",
  "gpt-4",
  "gpt-3.5-turbo",
  "claude-3-sonnet",
];

const availableTools = [
  "search",
  "life_env",
  "rpg_dice",
  "content_extractor",
  "summarizer",
  "math",
  "notes",
];

export function AgentEditDialog({
  agent,
  open,
  onOpenChange,
}: AgentEditDialogProps) {
  const queryClient = useQueryClient();

  const form = useForm<AgentFormValues>({
    resolver: zodResolver(agentFormSchema),
    defaultValues: {
      name: agent?.name || "",
      description: agent?.description || "",
      role_instructions: agent?.role_instructions || "",
      tool_instructions: agent?.tool_instructions || "",
      agent_model: agent?.agent_model || "gemini-2.5-flash-preview-04-17",
      tools: agent?.tools || [],
    },
  });

  // Reset form when agent changes
  React.useEffect(() => {
    if (agent) {
      form.reset({
        name: agent.name,
        description: agent.description,
        role_instructions: agent.role_instructions,
        tool_instructions: agent.tool_instructions,
        agent_model: agent.agent_model,
        tools: agent.tools,
      });
    }
  }, [agent, form]);

  const updateAgentMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Agent> }) =>
      agentAPI.updateAgent(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bots"] });
      queryClient.invalidateQueries({ queryKey: ["agents"] });
      onOpenChange(false);
    },
  });

  const onSubmit = async (data: AgentFormValues) => {
    if (!agent) return;
    await updateAgentMutation.mutateAsync({ id: agent.id, data });
  };

  const addTool = (tool: string) => {
    const currentTools = form.getValues("tools");
    if (!currentTools.includes(tool)) {
      form.setValue("tools", [...currentTools, tool]);
    }
  };

  const removeTool = (tool: string) => {
    const currentTools = form.getValues("tools");
    form.setValue(
      "tools",
      currentTools.filter((t) => t !== tool)
    );
  };

  if (!agent) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>編輯代理程式 - {agent.name}</DialogTitle>
          <DialogDescription>修改代理程式的配置和指令</DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>名稱</FormLabel>
                  <FormControl>
                    <Input placeholder="代理程式名稱" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>描述</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="代理程式的簡短描述"
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
              name="agent_model"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>AI 模型</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    defaultValue={field.value}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="選擇 AI 模型" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {availableModels.map((model) => (
                        <SelectItem key={model} value={model}>
                          {model}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="role_instructions"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>角色指令</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="描述代理程式的角色和行為..."
                      className="resize-none h-20"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="tool_instructions"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>工具指令</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="描述如何使用可用的工具..."
                      className="resize-none h-20"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="tools"
              render={() => (
                <FormItem>
                  <FormLabel>可用工具</FormLabel>
                  <div className="space-y-2">
                    <div className="flex flex-wrap gap-2">
                      {form.watch("tools").map((tool) => (
                        <Badge
                          key={tool}
                          variant="default"
                          className="flex items-center gap-1"
                        >
                          {tool}
                          <X
                            className="h-3 w-3 cursor-pointer"
                            onClick={() => removeTool(tool)}
                          />
                        </Badge>
                      ))}
                    </div>
                    <Select onValueChange={addTool}>
                      <SelectTrigger>
                        <SelectValue placeholder="添加工具..." />
                      </SelectTrigger>
                      <SelectContent>
                        {availableTools
                          .filter((tool) => !form.watch("tools").includes(tool))
                          .map((tool) => (
                            <SelectItem key={tool} value={tool}>
                              {tool}
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                取消
              </Button>
              <Button type="submit" disabled={updateAgentMutation.isPending}>
                {updateAgentMutation.isPending ? "更新中..." : "更新代理程式"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
