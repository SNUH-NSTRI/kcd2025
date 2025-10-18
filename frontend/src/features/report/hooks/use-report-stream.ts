'use client';

import { useState, useCallback, useRef } from 'react';

export interface ReportStreamState {
  content: string;
  isStreaming: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface UseReportStreamReturn extends ReportStreamState {
  startStream: (nctId: string, medication: string) => void;
  stopStream: () => void;
  reset: () => void;
}

/**
 * Hook for consuming streaming report generation from backend SSE endpoint.
 *
 * Usage:
 * ```tsx
 * const { content, isStreaming, isLoading, startStream } = useReportStream();
 *
 * // Start streaming
 * startStream('NCT03389555', 'hydrocortisonenasucc');
 *
 * // Render content with ReactMarkdown
 * <ReactMarkdown>{content}</ReactMarkdown>
 * ```
 */
export function useReportStream(): UseReportStreamReturn {
  const [content, setContent] = useState<string>('');
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);

  const stopStream = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsStreaming(false);
    setIsLoading(false);
  }, []);

  const reset = useCallback(() => {
    stopStream();
    setContent('');
    setError(null);
  }, [stopStream]);

  const startStream = useCallback((nctId: string, medication: string) => {
    // Clean up any existing connection
    stopStream();

    // Reset state
    setContent('');
    setError(null);
    setIsLoading(true);

    // Construct SSE URL (backend endpoint)
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const streamUrl = `${apiUrl}/api/reports/stream`;

    // EventSource doesn't support POST, so we need to use fetch with ReadableStream
    // For SSE with POST, we use fetch instead of EventSource
    const fetchStream = async () => {
      try {
        const response = await fetch(streamUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ nct_id: nctId, medication }),
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        if (!response.body) {
          throw new Error('Response body is null');
        }

        setIsLoading(false);
        setIsStreaming(true);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            setIsStreaming(false);
            break;
          }

          // Decode chunk
          buffer += decoder.decode(value, { stream: true });

          // Process complete SSE messages
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6); // Remove 'data: ' prefix

              if (data === '[DONE]') {
                setIsStreaming(false);
                continue;
              }

              try {
                const parsed = JSON.parse(data);

                if (parsed.type === 'content') {
                  // Append content chunk to existing content
                  setContent((prev) => prev + parsed.data);
                } else if (parsed.type === 'status') {
                  console.log('[Stream Status]', parsed.message);
                } else if (parsed.type === 'error') {
                  setError(parsed.message);
                  setIsStreaming(false);
                }
              } catch (e) {
                console.error('Failed to parse SSE data:', e);
              }
            }
          }
        }
      } catch (err) {
        console.error('Stream error:', err);
        setError(err instanceof Error ? err.message : 'Stream failed');
        setIsStreaming(false);
        setIsLoading(false);
      }
    };

    fetchStream();
  }, [stopStream]);

  return {
    content,
    isStreaming,
    isLoading,
    error,
    startStream,
    stopStream,
    reset,
  };
}
