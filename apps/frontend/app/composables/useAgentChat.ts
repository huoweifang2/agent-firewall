import { ref, reactive, computed } from 'vue'
import type { AgentMessage, AgentTrace, FirewallDecision } from '~/types/agent'
import { agentService } from '~/services/agentService'

export function useAgentChat() {
  const messages = ref<AgentMessage[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const config = reactive({
    agentId: null as string | null,
    role: 'customer' as string,
    policy: 'balanced' as string | null,
    model: '' as string,
  })

  const sessionId = ref(generateSessionId())

  const lastTrace = computed<AgentTrace | null>(() => {
    for (let i = messages.value.length - 1; i >= 0; i--) {
      const msg = messages.value[i]
      if (msg?.agent_trace) return msg.agent_trace
    }
    return null
  })

  const lastFirewallDecision = computed<FirewallDecision | null>(() => {
    for (let i = messages.value.length - 1; i >= 0; i--) {
      const msg = messages.value[i]
      if (msg?.firewall_decision) return msg.firewall_decision
    }
    return null
  })

  function generateSessionId(): string {
    return `agent-${crypto.randomUUID()}`
  }

  function addSystemMessage(content: string) {
    messages.value.push({
      id: crypto.randomUUID(),
      role: 'system',
      content,
      timestamp: new Date(),
    })
  }

  async function sendMessage(text: string) {
    error.value = null

    // Add user message
    messages.value.push({
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    })

    isLoading.value = true

    try {
      const stream = agentService.streamChat({
        message: text,
        agent_id: config.agentId,
        user_role: config.role,
        session_id: sessionId.value,
        model: config.model,
        ...(config.policy ? { policy: config.policy } : {}),
      })

      const msgId = crypto.randomUUID()
      messages.value.push({
        id: msgId,
        role: 'assistant',
        content: '',
        blocks: [],
        tools_called: [],
        timestamp: new Date(),
      })

      const assistantMsgIndex = messages.value.length - 1

      for await (const { event, data } of stream) {
        const msg = messages.value[assistantMsgIndex]
        
        switch (event) {
          case 'chunk':
            if (data.content) {
              msg.content += data.content
              if (!msg.blocks) msg.blocks = []
              
              if (msg.blocks.length > 0 && msg.blocks[msg.blocks.length - 1].type === 'text') {
                msg.blocks[msg.blocks.length - 1].content += data.content
              } else {
                msg.blocks.push({ type: 'text', content: data.content })
              }
            }
            break
            
          case 'tool_start':
            if (!msg.tools_called) msg.tools_called = []
            if (!msg.blocks) msg.blocks = []
            
            const newTool = {
              tool: data.name,
              args: data.kwargs || {},
              result_preview: '',
              allowed: true,
            }
            
            msg.tools_called.push(newTool)
            msg.blocks.push({ type: 'tool', tool: newTool })
            break
            
          case 'tool_end':
            if (msg.tools_called && msg.tools_called.length > 0) {
              const currentTool = msg.tools_called[msg.tools_called.length - 1]
              currentTool.result_preview = data.result
              currentTool.allowed = data.allowed
            }
            break
            
          case 'final':
            msg.agent_trace = data.agent_trace || data.trace
            msg.firewall_decision = data.firewall_decision
            msg.content = data.response || msg.content
            if (data.tools_called) {
              msg.tools_called = data.tools_called
            }
            break
        }
        
        // Trigger Vue reactivity
        messages.value.splice(assistantMsgIndex, 1, msg)
      }
    }
    catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to get response from agent'
      error.value = msg

      messages.value.push({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `⚠️ Error: ${msg}`,
        timestamp: new Date(),
      })
    }
    finally {
      isLoading.value = false
    }
  }

  function switchRole(newRole: string) {
    if (newRole === config.role) return
    config.role = newRole
    sessionId.value = generateSessionId()
    messages.value = []
    addSystemMessage(`Switched to **${newRole}** role`)
  }

  function newConversation() {
    sessionId.value = generateSessionId()
    messages.value = []
    error.value = null
    addSystemMessage('New conversation started')
  }

  return {
    messages,
    isLoading,
    error,
    config,
    sessionId,
    lastTrace,
    lastFirewallDecision,
    sendMessage,
    switchRole,
    newConversation,
  }
}
