/**
 * Agent Swarm Tab for Task Detail Page
 *
 * Displays multi-agent coordination messages for the current task.
 */

import { AgentSwarmVisualization } from "@/components/AgentSwarmVisualization";
import { useParams } from "react-router-dom";

function AgentSwarmTab() {
  const { taskId } = useParams();

  if (!taskId) {
    return (
      <div className="flex items-center justify-center p-8">
        <p className="text-muted-foreground">Task ID not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg border bg-card p-6">
        <h2 className="mb-2 text-xl font-semibold">Multi-Agent Coordination</h2>
        <p className="mb-4 text-sm text-muted-foreground">
          View real-time communications between the planner, executor, and
          validator agents during task execution.
        </p>
        <div className="text-xs text-muted-foreground">
          💡 Enable multi-agent swarm with{" "}
          <code className="rounded bg-muted px-1 py-0.5">
            ENABLE_MULTI_AGENT_SWARM=true
          </code>
        </div>
      </div>

      <AgentSwarmVisualization
        taskId={taskId}
        autoRefresh={true}
        refreshInterval={2000}
        className="w-full"
      />
    </div>
  );
}

export { AgentSwarmTab };
