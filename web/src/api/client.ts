const API_BASE = '/api';

export async function fetchSSE(
  url: string,
  body: Record<string, unknown>,
  handlers: {
    onMessage?: (data: { content: string }) => void;
    onUICommand?: (data: { module: string; action: string; data: Record<string, unknown> }) => void;
    onProgress?: (data: { step: string; detail: string }) => void;
    onUsage?: (data: { provider: string; model: string; usage: { input_tokens?: number; output_tokens?: number; total_tokens?: number } }) => void;
    onToolCall?: (data: { tool: string; args: Record<string, unknown> }) => void;
    onError?: (data: { message: string }) => void;
    onDone?: () => void;
  },
  signal?: AbortSignal,
) {
  const response = await fetch(`${API_BASE}${url}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    let currentEvent = '';
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith('data: ')) {
        const rawData = line.slice(6);
        try {
          const data = JSON.parse(rawData);
          switch (currentEvent) {
            case 'message':
              handlers.onMessage?.(data);
              break;
            case 'ui_command':
              handlers.onUICommand?.(data);
              break;
            case 'progress':
              handlers.onProgress?.(data);
              break;
            case 'usage':
              handlers.onUsage?.(data);
              break;
            case 'tool_call':
              handlers.onToolCall?.(data);
              break;
            case 'error':
              handlers.onError?.(data);
              break;
            case 'done':
              handlers.onDone?.();
              break;
          }
        } catch {
          // skip malformed JSON
        }
        currentEvent = '';
      }
    }
  }
}

export async function fetchJSON<T>(url: string): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

export async function putJSON<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

export async function postJSON<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

export async function deleteJSON<T>(url: string): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, { method: 'DELETE' });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}
