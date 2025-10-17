import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getClient } from "@/api/AxiosClient";

type BenchmarkSummary = {
  provider: string;
  model_name: string | null;
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
  success_rate: number;
  avg_latency_ms: number | null;
  total_input_tokens: number | null;
  total_output_tokens: number | null;
  total_cost: number | null;
  avg_cost: number | null;
};

async function fetchBenchmarkSummaries(): Promise<BenchmarkSummary[]> {
  const client = await getClient(null);
  const response = await client.get<BenchmarkSummary[]>("/v1/benchmarks/summaries");
  return response.data;
}

function BenchmarksPage() {
  const { data: summaries, isLoading, error } = useQuery({
    queryKey: ["benchmarks", "summaries"],
    queryFn: fetchBenchmarkSummaries,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  if (isLoading) {
    return (
      <div className="p-8">
        <h1 className="text-3xl font-bold mb-8">LLM Benchmarks</h1>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-32" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-4 w-full mb-2" />
                <Skeleton className="h-4 w-3/4" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <h1 className="text-3xl font-bold mb-8">LLM Benchmarks</h1>
        <Card>
          <CardContent className="pt-6">
            <p className="text-red-500">Failed to load benchmarks: {String(error)}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">LLM Benchmarks</h1>
        <p className="text-muted-foreground mt-2">
          Performance metrics and cost comparison across LLM providers
        </p>
      </div>

      {!summaries || summaries.length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <p className="text-muted-foreground">
              No benchmark data available. Run some tasks to see benchmarking metrics.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {summaries.map((summary) => (
            <Card key={summary.provider}>
              <CardHeader>
                <CardTitle className="text-xl">{summary.provider}</CardTitle>
                {summary.model_name && (
                  <CardDescription>{summary.model_name}</CardDescription>
                )}
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="text-sm text-muted-foreground">Success Rate</div>
                  <div className="text-2xl font-bold">
                    {summary.success_rate.toFixed(1)}%
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {summary.successful_calls} / {summary.total_calls} calls
                  </div>
                </div>

                {summary.avg_latency_ms && (
                  <div>
                    <div className="text-sm text-muted-foreground">
                      Avg Latency
                    </div>
                    <div className="text-2xl font-bold">
                      {Math.round(summary.avg_latency_ms)}ms
                    </div>
                  </div>
                )}

                {summary.total_cost !== null && summary.total_cost > 0 && (
                  <div>
                    <div className="text-sm text-muted-foreground">
                      Total Cost
                    </div>
                    <div className="text-2xl font-bold">
                      ${summary.total_cost.toFixed(4)}
                    </div>
                    {summary.avg_cost && (
                      <div className="text-xs text-muted-foreground">
                        ${summary.avg_cost.toFixed(6)} per call
                      </div>
                    )}
                  </div>
                )}

                {summary.total_input_tokens && (
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Input Tokens</span>
                    <span className="font-medium">
                      {summary.total_input_tokens.toLocaleString()}
                    </span>
                  </div>
                )}

                {summary.total_output_tokens && (
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Output Tokens</span>
                    <span className="font-medium">
                      {summary.total_output_tokens.toLocaleString()}
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <div className="mt-8">
        <Card>
          <CardHeader>
            <CardTitle>About Benchmarking</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>
              This dashboard shows real-time performance metrics for all LLM calls made by Skyvern.
            </p>
            <p>
              Metrics are automatically captured for every LLM interaction and aggregated by provider.
            </p>
            <p>
              Use the evaluation/llm_benchmarking_runner.py script to run standardized benchmarks across providers.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export { BenchmarksPage };
