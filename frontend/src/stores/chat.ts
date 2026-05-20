import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  references?: Array<{
    content: string
    distance: number
    metadata?: Record<string, any>
  }>
  status?: 'pending' | 'processing' | 'completed' | 'failed'
  taskId?: string
}

export interface ChatSession {
  id: string
  title: string
  messages: Message[]
  createdAt: Date
}

export const useChatStore = defineStore('chat', () => {
  const sessions = ref<ChatSession[]>([])
  const currentSessionId = ref<string | null>(null)
  const isStreaming = ref(false)
  const settings = ref({
    useRag: true,
    topK: 3,
    temperature: 0.7
  })

  const currentSession = computed(() => {
    return sessions.value.find(s => s.id === currentSessionId.value) || null
  })

  const sortedSessions = computed(() => {
    return [...sessions.value].sort((a, b) =>
      new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    )
  })

  function createSession(): ChatSession {
    const session: ChatSession = {
      id: Date.now().toString(),
      title: '新对话',
      messages: [],
      createdAt: new Date()
    }
    console.log('[ChatStore] Creating session:', session)
    sessions.value.push(session)
    console.log('[ChatStore] Sessions after push:', sessions.value.length, 'sessions')
    console.log('[ChatStore] Sorted sessions:', sortedSessions.value.length, 'sorted sessions')
    currentSessionId.value = session.id
    console.log('[ChatStore] Current session ID:', currentSessionId.value)
    return session
  }

  function selectSession(sessionId: string) {
    currentSessionId.value = sessionId
  }

  function deleteSession(sessionId: string) {
    const index = sessions.value.findIndex(s => s.id === sessionId)
    if (index !== -1) {
      sessions.value.splice(index, 1)
      if (currentSessionId.value === sessionId) {
        currentSessionId.value = sessions.value[0]?.id || null
      }
    }
  }

  async function sendMessage(content: string): Promise<void> {
    console.log('[ChatStore] sendMessage called with:', content)
    if (!currentSession.value) {
      console.log('[ChatStore] No current session, creating new one')
      createSession()
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date()
    }
    currentSession.value!.messages.push(userMessage)

    if (currentSession.value!.title === '新对话') {
      currentSession.value!.title = content.substring(0, 20) + (content.length > 20 ? '...' : '')
    }

    isStreaming.value = true

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: content,
          session_id: currentSession.value!.id,
          use_rag: settings.value.useRag,
          top_k: settings.value.topK
        })
      })

      const data = await response.json()

      const assistantMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: data.answer,
        timestamp: new Date(),
        references: data.references || []
      }
      currentSession.value!.messages.push(assistantMessage)
    } catch (error) {
      const errorMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: '抱歉，我暂时无法回答您的问题。',
        timestamp: new Date()
      }
      currentSession.value!.messages.push(errorMessage)
    } finally {
      isStreaming.value = false
    }
  }

  async function sendMessageStream(content: string): Promise<void> {
    if (!currentSession.value) {
      createSession()
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date()
    }
    currentSession.value!.messages.push(userMessage)

    if (currentSession.value!.title === '新对话') {
      currentSession.value!.title = content.substring(0, 20) + (content.length > 20 ? '...' : '')
    }

    isStreaming.value = true

    const assistantMessage: Message = {
      id: Date.now().toString(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      references: []
    }
    currentSession.value!.messages.push(assistantMessage)

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: content,
          session_id: currentSession.value!.id,
          use_rag: settings.value.useRag,
          top_k: settings.value.topK
        })
      })

      if (!response.body) {
        assistantMessage.content = '抱歉，流式响应不可用。'
        return
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)

            if (data === '[DONE]') {
              break
            }

            try {
              const parsed = JSON.parse(data)

              if (parsed.type === 'references') {
                assistantMessage.references = parsed.data
              } else {
                assistantMessage.content += parsed
                currentSession.value!.messages = [...currentSession.value!.messages]
              }
            } catch {
              assistantMessage.content += data
              currentSession.value!.messages = [...currentSession.value!.messages]
            }
          }
        }
      }
    } catch (error) {
      assistantMessage.content = '抱歉，流式响应出错。'
    } finally {
      isStreaming.value = false
    }
  }

  function updateSettings(newSettings: Partial<typeof settings.value>) {
    settings.value = { ...settings.value, ...newSettings }
  }

  async function sendMessageAsync(content: string): Promise<void> {
    if (!currentSession.value) {
      createSession()
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date()
    }
    currentSession.value!.messages.push(userMessage)

    if (currentSession.value!.title === '新对话') {
      currentSession.value!.title = content.substring(0, 20) + (content.length > 20 ? '...' : '')
    }

    isStreaming.value = true

    const assistantMessage: Message = {
      id: Date.now().toString(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      references: [],
      status: 'processing'
    }
    currentSession.value!.messages.push(assistantMessage)

    try {
      const response = await fetch('/api/chat/async/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: content,
          session_id: currentSession.value!.id,
          use_rag: settings.value.useRag,
          top_k: settings.value.topK
        })
      })

      if (!response.body) {
        throw new Error('流式响应不可用')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6)

            if (!dataStr.trim()) continue

            try {
              const data = JSON.parse(dataStr)

              if (data.type === 'references') {
                assistantMessage.references = data.data || []
              } else if (data.type === 'chunk') {
                assistantMessage.content += data.data || ''
              } else if (data.type === 'done') {
                assistantMessage.status = 'completed'
                break
              } else if (data.type === 'error') {
                assistantMessage.content = `错误: ${data.data}`
                assistantMessage.status = 'failed'
                break
              }
            } catch (e) {
              assistantMessage.content += dataStr
            }

            currentSession.value!.messages = [...currentSession.value!.messages]
          }
        }
      }
    } catch (error) {
      assistantMessage.content = '抱歉，请求失败。'
      assistantMessage.status = 'failed'
    } finally {
      isStreaming.value = false
    }
  }

  return {
    sessions,
    currentSessionId,
    currentSession,
    sortedSessions,
    isStreaming,
    settings,
    createSession,
    selectSession,
    deleteSession,
    sendMessage,
    sendMessageStream,
    sendMessageAsync,
    updateSettings
  }
})
