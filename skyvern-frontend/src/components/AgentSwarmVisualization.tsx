/**
 * Agent Swarm Visualization Component
 *
 * Displays real-time agent communications and coordination for multi-agent tasks.
 */

import { useCallback, useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./ui/card";
import { Badge } from "./ui/badge";
import { ScrollArea } from "./ui/scroll-area";
import { Separator } from "./ui/separator";
import { cn } from "@/util/utils";

interface AgentMessage {
  message_id: string;
  timestamp: string;
  sender_role: string;
  sender_id: string;
  recipient_role?: string;
  recipient_id?: string;
  message_type: string;
  content: Record<string, unknown>;
  task_id?: string;
  step_id?: string;
  priority: number;
}

interface AgentSwarmVisualizationProps {
  taskId: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
  className?: string;
}

const roleColors: Record<string, string> = {
  planner: "bg-blue-500",
  executor: "bg-green-500",
  validator: "bg-yellow-500",
  coordinator: "bg-purple-500",
};

const messageTypeColors: Record<string, string> = {
  thought: "bg-slate-500",
  plan: "bg-blue-500",
  action_proposal: "bg-orange-500",
  action_approval: "bg-green-500",
  action_rejection: "bg-red-500",
  validation_request: "bg-yellow-500",
  validation_result: "bg-teal-500",
  critique: "bg-pink-500",
  error: "bg-red-600",
};

export function AgentSwarmVisualization({
  taskId,
  autoRefresh = true,
  refreshInterval = 2000,
  className,
}: AgentSwarmVisualizationProps) {
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMessages = useCallback(async () => {
    try {
      const response = await fetch(
        `/api/v1/agent-swarm/tasks/${taskId}/messages`,
        {
          headers: {
            "Content-Type": "application/json",
          },
        },
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch messages: ${response.statusText}`);
      }

      const data = await response.json();
      setMessages(data.messages || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      console.error("Error fetching agent messages:", err);
    } finally {
      setIsLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    void fetchMessages();

    if (autoRefresh) {
      const interval = setInterval(() => {
        void fetchMessages();
      }, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [taskId, autoRefresh, refreshInterval, fetchMessages]);

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Agent Swarm Communications</CardTitle>
          <CardDescription>Loading agent messages...</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Agent Swarm Communications</CardTitle>
          <CardDescription className="text-destructive">
            Error: {error}
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Agent Swarm Communications</CardTitle>
        <CardDescription>
          Real-time coordination between planner, executor, and validator agents
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-96">
          {messages.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground">
              No agent communications yet
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message) => (
                <MessageCard key={message.message_id} message={message} />
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

interface MessageCardProps {
  message: AgentMessage;
}

function MessageCard({ message }: MessageCardProps) {
  const roleColor = roleColors[message.sender_role] || "bg-gray-500";
  const typeColor = messageTypeColors[message.message_type] || "bg-gray-500";

  const formatContent = (content: Record<string, unknown>) => {
    // Handle different message content types
    if ("thought" in content) {
      return (
        <div>
          <p className="text-sm">{String(content.thought)}</p>
          {typeof content.confidence === "number" && (
            <p className="mt-1 text-xs text-muted-foreground">
              Confidence: {Number(content.confidence) * 100}%
            </p>
          )}
        </div>
      );
    }

    if ("plan_description" in content) {
      return (
        <div>
          <p className="text-sm">{String(content.plan_description)}</p>
          {typeof content.risk_level === "string" && (
            <Badge
              variant="outline"
              className={cn(
                "mt-1",
                content.risk_level === "high" && "border-red-500 text-red-500",
                content.risk_level === "medium" &&
                  "border-yellow-500 text-yellow-500",
                content.risk_level === "low" &&
                  "border-green-500 text-green-500",
              )}
            >
              Risk: {String(content.risk_level)}
            </Badge>
          )}
        </div>
      );
    }

    if ("action_type" in content) {
      return (
        <div>
          <p className="text-sm">Action: {String(content.action_type)}</p>
          {typeof content.rationale === "string" && (
            <p className="mt-1 text-xs text-muted-foreground">
              {String(content.rationale)}
            </p>
          )}
        </div>
      );
    }

    if ("approved" in content) {
      const approved =
        typeof content.approved === "boolean" ? content.approved : false;
      const approverReasoning =
        typeof content.approver_reasoning === "string"
          ? content.approver_reasoning
          : null;

      return (
        <div>
          <Badge variant={approved ? "default" : "destructive"}>
            {approved ? "Approved" : "Rejected"}
          </Badge>
          {approverReasoning && (
            <p className="mt-1 text-xs text-muted-foreground">
              {approverReasoning}
            </p>
          )}
        </div>
      );
    }

    if ("valid" in content) {
      const isValid =
        typeof content.valid === "boolean" ? content.valid : false;

      return (
        <div>
          <Badge variant={isValid ? "default" : "secondary"}>
            {isValid ? "Valid" : "Invalid"}
          </Badge>
          {Array.isArray(content.findings) && content.findings.length > 0 && (
            <ul className="mt-1 list-inside list-disc text-xs text-muted-foreground">
              {content.findings.map((finding, idx) => (
                <li key={idx}>{String(finding)}</li>
              ))}
            </ul>
          )}
        </div>
      );
    }

    if ("success" in content) {
      const isSuccess =
        typeof content.success === "boolean" ? content.success : false;
      const errorMessage =
        typeof content.error_message === "string"
          ? content.error_message
          : null;

      return (
        <div>
          <Badge variant={isSuccess ? "default" : "destructive"}>
            {isSuccess ? "Success" : "Failed"}
          </Badge>
          {errorMessage && (
            <p className="mt-1 text-xs text-destructive">{errorMessage}</p>
          )}
        </div>
      );
    }

    // Default: show JSON
    return (
      <pre className="overflow-x-auto text-xs">
        {JSON.stringify(content, null, 2)}
      </pre>
    );
  };

  return (
    <div className="rounded-lg border p-4">
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <Badge className={roleColor}>{message.sender_role}</Badge>
          <Badge variant="outline" className={typeColor}>
            {message.message_type}
          </Badge>
          {message.priority > 5 && (
            <Badge variant="destructive">High Priority</Badge>
          )}
        </div>
        <span className="text-xs text-muted-foreground">
          {new Date(message.timestamp).toLocaleTimeString()}
        </span>
      </div>

      <Separator className="my-2" />

      <div>{formatContent(message.content)}</div>

      {message.recipient_role && (
        <div className="mt-2 text-xs text-muted-foreground">
          → to: {message.recipient_role}
        </div>
      )}
    </div>
  );
}
