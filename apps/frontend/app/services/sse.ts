export interface RawSseEvent {
  event: string
  data: string
}

export interface JsonSseEvent {
  event: string
  data: Record<string, unknown>
}

export interface OpenAIStreamCallbacks {
  onToken: (token: string) => void
  onDone: () => void
  onError: (error: Error) => void
}

function parseBlock(block: string): RawSseEvent | null {
  const eventMatch = block.match(/^event:\s*(.+)$/m)
  const dataLines = [...block.matchAll(/^data:\s*(.*)$/gm)].map((match) => match[1])
  if (dataLines.length === 0) return null

  return {
    event: eventMatch?.[1]?.trim() || 'message',
    data: dataLines.join('\n').trim(),
  }
}

export async function* readSseEvents(response: Response): AsyncGenerator<RawSseEvent> {
  if (!response.body) {
    throw new Error('No response body')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() || ''

    for (const block of blocks) {
      const event = parseBlock(block)
      if (event) yield event
    }
  }

  const trailing = parseBlock(buffer)
  if (trailing) yield trailing
}

export async function* readJsonSseEvents(response: Response): AsyncGenerator<JsonSseEvent> {
  for await (const { event, data } of readSseEvents(response)) {
    try {
      const parsed = JSON.parse(data)
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        yield { event, data: parsed as Record<string, unknown> }
      }
    } catch {
      console.error('Failed to parse SSE data:', data)
    }
  }
}

export async function consumeOpenAIStream(
  response: Response,
  callbacks: OpenAIStreamCallbacks,
): Promise<Response> {
  for await (const { data } of readSseEvents(response)) {
    if (data === '[DONE]') {
      callbacks.onDone()
      return response
    }

    try {
      const chunk = JSON.parse(data)
      const content = chunk.choices?.[0]?.delta?.content
      if (content) {
        callbacks.onToken(content)
      }
    } catch {
      // Skip malformed chunks.
    }
  }

  callbacks.onDone()
  return response
}
