import { useState } from "react";
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

interface ObserverSession {
  observer_session_id: string;
  title: string;
  status: "recording" | "completed" | "processing" | "failed";
  created_at: string;
  completed_at?: string;
}

export function ObserverSessionsPage() {
  const [creating, setCreating] = useState(false);

  const { data: sessions, isLoading } = useQuery({
    queryKey: ["observer-sessions"],
    queryFn: async () => {
      // Replace with actual API call
      return {
        sessions: [] as ObserverSession[],
        total: 0,
      };
    },
  });

  const handleCreateSession = async () => {
    setCreating(true);
    try {
      // API call to create session
      console.log("Creating observer session...");
    } catch (error) {
      console.error("Failed to create session:", error);
    } finally {
      setCreating(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "recording":
        return "bg-blue-500";
      case "completed":
        return "bg-green-500";
      case "processing":
        return "bg-yellow-500";
      case "failed":
        return "bg-red-500";
      default:
        return "bg-gray-500";
    }
  };

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Observer Sessions</h1>
          <p className="mt-2 text-gray-600">
            Record browser interactions and convert them into workflows
          </p>
        </div>
        <Button onClick={handleCreateSession} disabled={creating}>
          {creating ? "Creating..." : "New Session"}
        </Button>
      </div>

      {isLoading ? (
        <div className="py-12 text-center">Loading sessions...</div>
      ) : sessions?.sessions.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>No Sessions Yet</CardTitle>
            <CardDescription>
              Create your first observer session to start recording browser
              interactions
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={handleCreateSession} disabled={creating}>
              Create First Session
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {sessions?.sessions.map((session) => (
            <Card
              key={session.observer_session_id}
              className="cursor-pointer transition-shadow hover:shadow-lg"
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <CardTitle className="text-lg">{session.title}</CardTitle>
                  <Badge className={getStatusColor(session.status)}>
                    {session.status}
                  </Badge>
                </div>
                <CardDescription>
                  Created: {new Date(session.created_at).toLocaleString()}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">
                    {session.observer_session_id}
                  </span>
                  {session.status === "completed" && (
                    <Button size="sm" variant="outline">
                      Generate Workflow
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
