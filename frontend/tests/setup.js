import { vi } from 'vitest'

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
}

global.localStorage = localStorageMock

// Mock WebSocket
class MockWebSocket {
  constructor(url) {
    this.url = url
    this.readyState = WebSocket.CONNECTING
    this.onopen = null
    this.onmessage = null
    this.onclose = null
    this.onerror = null
  }

  send = vi.fn()
  close = vi.fn()
  addEventListener = vi.fn()
  removeEventListener = vi.fn()
}

// WebSocket 常量
MockWebSocket.CONNECTING = 0
MockWebSocket.OPEN = 1
MockWebSocket.CLOSING = 2
MockWebSocket.CLOSED = 3

global.WebSocket = MockWebSocket

// Mock window.location
delete window.location
window.location = {
  protocol: 'http:',
  host: 'localhost:5173',
  href: 'http://localhost:5173/'
}

// Mock import.meta.env
global.import = {
  meta: {
    env: {
      VITE_API_BASE_URL: 'http://localhost:8000',
      VITE_WS_URL: 'localhost:8000'
    }
  }
}

// 減少測試噪音 - 保留 error 和 warn
const originalConsole = { ...console }
global.console = {
  ...originalConsole,
  log: vi.fn(),
  debug: vi.fn(),
  // 保留 error 和 warn 以便調試
  error: originalConsole.error,
  warn: originalConsole.warn
}
