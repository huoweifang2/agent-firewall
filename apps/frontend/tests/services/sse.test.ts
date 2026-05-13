import assert from 'node:assert/strict'
import test from 'node:test'

import { consumeOpenAIStream, readJsonSseEvents, readSseEvents } from '../../app/services/sse'

function sseResponse(chunks: string[]): Response {
  const encoder = new TextEncoder()

  return new Response(
    new ReadableStream<Uint8Array>({
      start(controller) {
        for (const chunk of chunks) {
          controller.enqueue(encoder.encode(chunk))
        }
        controller.close()
      },
    }),
    { headers: { 'content-type': 'text/event-stream' } },
  )
}

test('readSseEvents parses split chunks and trailing events', async () => {
  const response = sseResponse([
    'event: token\ndata: {"text":"hel',
    'lo"}\n\n',
    'data: first\ndata: second\n\n',
    'event: done\ndata: [DONE]',
  ])

  const events = []
  for await (const event of readSseEvents(response)) {
    events.push(event)
  }

  assert.deepEqual(events, [
    { event: 'token', data: '{"text":"hello"}' },
    { event: 'message', data: 'first\nsecond' },
    { event: 'done', data: '[DONE]' },
  ])
})

test('readJsonSseEvents yields object payloads and skips malformed chunks', async () => {
  const response = sseResponse([
    'event: delta\ndata: {"token":"a"}\n\n',
    'data: malformed\n\n',
    'event: done\ndata: {"ok":true}\n\n',
  ])
  const originalConsoleError = console.error
  const parseErrors: unknown[][] = []
  console.error = (...args: unknown[]) => {
    parseErrors.push(args)
  }

  const events = []
  try {
    for await (const event of readJsonSseEvents(response)) {
      events.push(event)
    }
  } finally {
    console.error = originalConsoleError
  }

  assert.deepEqual(events, [
    { event: 'delta', data: { token: 'a' } },
    { event: 'done', data: { ok: true } },
  ])
  assert.equal(parseErrors.length, 1)
})

test('consumeOpenAIStream forwards tokens and completes on done marker', async () => {
  const response = sseResponse([
    'data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n',
    'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n',
    'data: [DONE]\n\n',
  ])
  const tokens: string[] = []
  let doneCount = 0
  const errors: Error[] = []

  const returned = await consumeOpenAIStream(response, {
    onToken: (token) => tokens.push(token),
    onDone: () => {
      doneCount += 1
    },
    onError: (error) => errors.push(error),
  })

  assert.equal(returned, response)
  assert.deepEqual(tokens, ['Hel', 'lo'])
  assert.equal(doneCount, 1)
  assert.deepEqual(errors, [])
})
