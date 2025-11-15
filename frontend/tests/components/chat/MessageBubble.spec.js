/**
 * MessageBubble 組件單元測試
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import MessageBubble from '@/components/chat/MessageBubble.vue'
import { NAvatar, NDropdown } from 'naive-ui'

describe('MessageBubble', () => {
  const mockMessage = {
    id: 'msg123',
    content: 'Hello World!',
    sent_at: '2025-11-15T10:00:00Z',
    is_read: false,
    sender_id: 'user123'
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('渲染測試', () => {
    it('應該正確渲染訊息內容', () => {
      const wrapper = mount(MessageBubble, {
        props: {
          message: mockMessage,
          isOwn: false
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      expect(wrapper.text()).toContain('Hello World!')
    })

    it('應該為自己的訊息添加正確的 CSS 類別', () => {
      const wrapper = mount(MessageBubble, {
        props: {
          message: mockMessage,
          isOwn: true
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      const bubble = wrapper.find('.message-bubble')
      expect(bubble.classes()).toContain('message-own')
    })

    it('應該為對方的訊息添加正確的 CSS 類別', () => {
      const wrapper = mount(MessageBubble, {
        props: {
          message: mockMessage,
          isOwn: false
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      const bubble = wrapper.find('.message-bubble')
      expect(bubble.classes()).toContain('message-other')
    })

    it('應該為自己的訊息使用藍色背景', () => {
      const wrapper = mount(MessageBubble, {
        props: {
          message: mockMessage,
          isOwn: true
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      const content = wrapper.find('.message-content')
      expect(content.classes()).toContain('bg-blue-500')
      expect(content.classes()).toContain('text-white')
    })

    it('應該為對方的訊息使用灰色背景', () => {
      const wrapper = mount(MessageBubble, {
        props: {
          message: mockMessage,
          isOwn: false
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      const content = wrapper.find('.message-content')
      expect(content.classes()).toContain('bg-gray-100')
      expect(content.classes()).toContain('text-gray-900')
    })
  })

  describe('頭像顯示', () => {
    it('應該在對方訊息顯示頭像', () => {
      const wrapper = mount(MessageBubble, {
        props: {
          message: mockMessage,
          isOwn: false,
          showAvatar: true,
          otherUserAvatar: 'https://example.com/avatar.jpg'
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      expect(wrapper.find('.message-avatar').exists()).toBe(true)
    })

    it('應該在自己的訊息不顯示頭像', () => {
      const wrapper = mount(MessageBubble, {
        props: {
          message: mockMessage,
          isOwn: true
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      expect(wrapper.find('.message-avatar').exists()).toBe(false)
    })

    it('應該在 showAvatar 為 false 時不顯示頭像', () => {
      const wrapper = mount(MessageBubble, {
        props: {
          message: mockMessage,
          isOwn: false,
          showAvatar: false
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      expect(wrapper.find('.message-avatar').exists()).toBe(false)
    })
  })

  describe('已讀狀態', () => {
    it('應該在已讀時顯示「✓✓ 已讀」', () => {
      const wrapper = mount(MessageBubble, {
        props: {
          message: { ...mockMessage, is_read: true },
          isOwn: true
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      expect(wrapper.text()).toContain('✓✓ 已讀')
    })

    it('應該在未讀時顯示「✓ 已送達」', () => {
      const wrapper = mount(MessageBubble, {
        props: {
          message: { ...mockMessage, is_read: false },
          isOwn: true
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      expect(wrapper.text()).toContain('✓ 已送達')
    })

    it('應該在對方訊息不顯示已讀狀態', () => {
      const wrapper = mount(MessageBubble, {
        props: {
          message: { ...mockMessage, is_read: true },
          isOwn: false
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      expect(wrapper.text()).not.toContain('✓✓')
      expect(wrapper.text()).not.toContain('已讀')
    })
  })

  describe('時間格式化', () => {
    it('應該顯示「剛剛」對於 1 分鐘內的訊息', () => {
      const now = new Date()
      const wrapper = mount(MessageBubble, {
        props: {
          message: {
            ...mockMessage,
            sent_at: new Date(now.getTime() - 30 * 1000).toISOString() // 30 秒前
          },
          isOwn: false
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      expect(wrapper.text()).toContain('剛剛')
    })

    it('應該顯示「X 分鐘前」對於 1 小時內的訊息', () => {
      const now = new Date()
      const wrapper = mount(MessageBubble, {
        props: {
          message: {
            ...mockMessage,
            sent_at: new Date(now.getTime() - 30 * 60 * 1000).toISOString() // 30 分鐘前
          },
          isOwn: false
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      expect(wrapper.text()).toMatch(/\d+ 分鐘前/)
    })

    it('應該顯示「X 小時前」對於 24 小時內的訊息', () => {
      const now = new Date()
      const wrapper = mount(MessageBubble, {
        props: {
          message: {
            ...mockMessage,
            sent_at: new Date(now.getTime() - 5 * 60 * 60 * 1000).toISOString() // 5 小時前
          },
          isOwn: false
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      expect(wrapper.text()).toMatch(/\d+ 小時前/)
    })

    it('應該顯示「X 天前」對於 7 天內的訊息', () => {
      const now = new Date()
      const wrapper = mount(MessageBubble, {
        props: {
          message: {
            ...mockMessage,
            sent_at: new Date(now.getTime() - 3 * 24 * 60 * 60 * 1000).toISOString() // 3 天前
          },
          isOwn: false
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      expect(wrapper.text()).toMatch(/\d+ 天前/)
    })

    it('應該為超過 7 天的訊息顯示日期', () => {
      const wrapper = mount(MessageBubble, {
        props: {
          message: {
            ...mockMessage,
            sent_at: '2025-01-01T10:00:00Z' // 很久以前
          },
          isOwn: false
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      // 應該包含月份或日期
      const text = wrapper.text()
      expect(text).toMatch(/\d+/)
    })

    it('應該處理缺少 sent_at 的情況', () => {
      const wrapper = mount(MessageBubble, {
        props: {
          message: {
            id: 'msg123',
            content: 'Test message',
            sent_at: null
          },
          isOwn: false
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      expect(wrapper.find('.message-time').text()).toBe('')
    })
  })

  describe('刪除訊息功能', () => {
    it('應該在右鍵點擊自己的訊息時顯示下拉選單', async () => {
      const wrapper = mount(MessageBubble, {
        props: {
          message: mockMessage,
          isOwn: true
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      const content = wrapper.find('.message-content')

      // 觸發右鍵點擊
      await content.trigger('contextmenu')

      // 檢查下拉選單是否顯示（透過 showDropdown ref）
      expect(wrapper.vm.showDropdown).toBe(true)
    })

    it('應該發射 delete 事件當選擇刪除選項', async () => {
      const wrapper = mount(MessageBubble, {
        props: {
          message: mockMessage,
          isOwn: true
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      // 調用 handleDropdownSelect 方法
      wrapper.vm.handleDropdownSelect('delete')

      // 檢查是否發射 delete 事件
      expect(wrapper.emitted('delete')).toBeTruthy()
      expect(wrapper.emitted('delete')[0]).toEqual(['msg123'])
    })

    it('應該在選擇後關閉下拉選單', async () => {
      const wrapper = mount(MessageBubble, {
        props: {
          message: mockMessage,
          isOwn: true
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      // 打開選單
      wrapper.vm.showDropdown = true

      // 選擇刪除
      wrapper.vm.handleDropdownSelect('delete')

      expect(wrapper.vm.showDropdown).toBe(false)
    })

    it('應該防止右鍵點擊的預設行為', async () => {
      const wrapper = mount(MessageBubble, {
        props: {
          message: mockMessage,
          isOwn: true
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      const content = wrapper.find('.message-content')
      const event = new Event('contextmenu')
      const preventDefaultSpy = vi.spyOn(event, 'preventDefault')

      // 調用 handleContextMenu
      wrapper.vm.handleContextMenu(event)

      expect(preventDefaultSpy).toHaveBeenCalled()
    })

    it('應該在對方訊息不顯示右鍵選單', () => {
      const wrapper = mount(MessageBubble, {
        props: {
          message: mockMessage,
          isOwn: false
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      // 對方訊息應該沒有 NDropdown 組件
      expect(wrapper.findComponent(NDropdown).exists()).toBe(false)
    })
  })

  describe('Props 驗證', () => {
    it('應該正確接收 message prop', () => {
      const wrapper = mount(MessageBubble, {
        props: {
          message: mockMessage,
          isOwn: false
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      expect(wrapper.props('message')).toEqual(mockMessage)
    })

    it('應該正確接收 isOwn prop', () => {
      const wrapper = mount(MessageBubble, {
        props: {
          message: mockMessage,
          isOwn: true
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      expect(wrapper.props('isOwn')).toBe(true)
    })

    it('應該有 isOwn 的預設值 false', () => {
      const wrapper = mount(MessageBubble, {
        props: {
          message: mockMessage
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      expect(wrapper.props('isOwn')).toBe(false)
    })

    it('應該正確接收 showAvatar prop', () => {
      const wrapper = mount(MessageBubble, {
        props: {
          message: mockMessage,
          isOwn: false,
          showAvatar: false
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      expect(wrapper.props('showAvatar')).toBe(false)
    })

    it('應該有 showAvatar 的預設值 true', () => {
      const wrapper = mount(MessageBubble, {
        props: {
          message: mockMessage,
          isOwn: false
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      expect(wrapper.props('showAvatar')).toBe(true)
    })

    it('應該正確接收 otherUserAvatar prop', () => {
      const avatarUrl = 'https://example.com/avatar.jpg'
      const wrapper = mount(MessageBubble, {
        props: {
          message: mockMessage,
          isOwn: false,
          otherUserAvatar: avatarUrl
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      expect(wrapper.props('otherUserAvatar')).toBe(avatarUrl)
    })
  })

  describe('Dropdown 選項', () => {
    it('應該有正確的 dropdown 選項', () => {
      const wrapper = mount(MessageBubble, {
        props: {
          message: mockMessage,
          isOwn: true
        },
        global: {
          components: { NAvatar, NDropdown }
        }
      })

      const options = wrapper.vm.dropdownOptions
      expect(options).toHaveLength(1)
      expect(options[0].label).toBe('刪除訊息')
      expect(options[0].key).toBe('delete')
    })
  })
})
