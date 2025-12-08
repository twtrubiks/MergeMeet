/**
 * 條件化日誌工具
 *
 * 生產環境自動禁用 debug/log 輸出，僅保留 error/warn
 * 避免敏感信息洩露到瀏覽器控制台
 */

const isDev = import.meta.env.DEV || import.meta.env.MODE === 'development'

/**
 * Logger 實例
 * 用法與 console 相同，但會根據環境條件化輸出
 *
 * @example
 * import { logger } from '@/utils/logger'
 * logger.log('一般訊息')      // 僅開發環境輸出
 * logger.debug('調試訊息')    // 僅開發環境輸出
 * logger.warn('警告訊息')     // 所有環境輸出
 * logger.error('錯誤訊息')    // 所有環境輸出
 */
export const logger = {
  /**
   * 一般日誌（僅開發環境）
   */
  log: (...args) => {
    if (isDev) {
      console.log(...args)
    }
  },

  /**
   * 調試日誌（僅開發環境）
   */
  debug: (...args) => {
    if (isDev) {
      console.debug(...args)
    }
  },

  /**
   * 信息日誌（僅開發環境）
   */
  info: (...args) => {
    if (isDev) {
      console.info(...args)
    }
  },

  /**
   * 警告日誌（所有環境，但不含敏感數據）
   */
  warn: (...args) => {
    console.warn(...args)
  },

  /**
   * 錯誤日誌（所有環境，但不含敏感數據）
   */
  error: (...args) => {
    console.error(...args)
  },

  /**
   * 群組日誌（僅開發環境）
   */
  group: (...args) => {
    if (isDev) {
      console.group(...args)
    }
  },

  /**
   * 結束群組（僅開發環境）
   */
  groupEnd: () => {
    if (isDev) {
      console.groupEnd()
    }
  },

  /**
   * 表格日誌（僅開發環境）
   */
  table: (...args) => {
    if (isDev) {
      console.table(...args)
    }
  }
}

export default logger
