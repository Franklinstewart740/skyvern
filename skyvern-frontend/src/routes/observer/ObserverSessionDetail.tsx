import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface ObserverRecording {
  observer_recording_id: string;
  recording_type: string;
  url: string;
  timestamp: string;
  data: Record<string, unknown>;
  reasoning?: string;
}

export function ObserverSessionDetail() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [generating, setGenerating] = useState(false);

  const { data: session, isLoading } = useQuery({
    queryKey: ["observer-session", sessionId],
    queryFn: async () => {
      // Replace with actual API call
      return {
        observer_session_id: sessionId,
        title: "Observer Session",
        status: "recording",
        created_at: new Date().toISOString(),
      };
    },
  });

  const { data: recordings } = useQuery({
    queryKey: ["observer-recordings", sessionId],
    queryFn: async () => {
      // Replace with actual API call
      return [] as ObserverRecording[];
    },
  });

  const handleGenerateWorkflow = async () => {
    setGenerating(true);
    try {
      // API call to generate workflow
      console.log("Generating workflow from session:", sessionId);
    } catch (error) {
      console.error("Failed to generate workflow:", error);
    } finally {
      setGenerating(false);
    }
  };

  const handleCompleteSession = async () => {
    try {
      // API call to complete session
      console.log("Completing session:", sessionId);
    } catch (error) {
      console.error("Failed to complete session:", error);
    }
  };

  if (isLoading) {
    return <div className="container mx-auto p-6">Loading...</div>;
  }

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold">{session?.title}</h1>
            <p className="mt-1 text-gray-600">Session ID: {sessionId}</p>
          </div>
          <div className="flex gap-2">
            {session?.status === "recording" && (
              <Button onClick={handleCompleteSession}>
                Complete Recording
              </Button>
            )}
            {session?.status === "completed" && (
              <Button onClick={handleGenerateWorkflow} disabled={generating}>
                {generating ? "Generating..." : "Generate Workflow"}
              </Button>
            )}
          </div>
        </div>
        <Badge>{session?.status}</Badge>
      </div>

      <Tabs defaultValue="recordings" className="w-full">
        <TabsList>
          <TabsTrigger value="recordings">Recordings</TabsTrigger>
          <TabsTrigger value="workflow">Generated Workflow</TabsTrigger>
          <TabsTrigger value="diff">Diff View</TabsTrigger>
        </TabsList>

        <TabsContent value="recordings">
          <Card>
            <CardHeader>
              <CardTitle>Recorded Interactions</CardTitle>
              <CardDescription>
                {recordings?.length || 0} interactions recorded
              </CardDescription>
            </CardHeader>
            <CardContent>
              {recordings && recordings.length > 0 ? (
                <div className="space-y-4">
                  {recordings.map((recording, index) => (
                    <div
                      key={recording.observer_recording_id}
                      className="border-l-4 border-blue-500 py-2 pl-4"
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <span className="font-semibold">
                            {index + 1}. {recording.recording_type}
                          </span>
                          <p className="text-sm text-gray-600">
                            {recording.url}
                          </p>
                        </div>
                        <span className="text-xs text-gray-500">
                          {new Date(recording.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      {recording.reasoning && (
                        <p className="mt-2 text-sm text-gray-700">
                          {recording.reasoning}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-600">No recordings yet</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="workflow">
          <Card>
            <CardHeader>
              <CardTitle>Generated Workflow</CardTitle>
              <CardDescription>
                Review and edit the workflow generated from this session
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">
                Generate a workflow to see it here
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="diff">
          <Card>
            <CardHeader>
              <CardTitle>Diff View</CardTitle>
              <CardDescription>
                Compare recorded steps with generated workflow blocks
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">
                Generate a workflow to see the diff
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
