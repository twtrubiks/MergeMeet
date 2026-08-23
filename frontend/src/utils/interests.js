/**
 * 興趣顯示工具
 */

/**
 * 依「共同興趣優先」排序並標記興趣標籤
 *
 * 共同興趣（配對理由）排到最前面並標記 common，其餘依原順序補後，總數封頂。
 * 後端只在探索候選人與配對列表回傳 common_interests，其他來源缺欄位時
 * 退化成單純的興趣列表（全部 common: false），不會出錯。
 *
 * @param {{ interests?: string[], common_interests?: string[] }} user
 * @param {number} limit - 最多回傳幾個
 * @returns {{ name: string, common: boolean }[]}
 */
export function displayInterests(user, limit) {
  const common = new Set(user?.common_interests || [])
  const interests = user?.interests || []
  return [...interests.filter((i) => common.has(i)), ...interests.filter((i) => !common.has(i))]
    .slice(0, limit)
    .map((name) => ({ name, common: common.has(name) }))
}
