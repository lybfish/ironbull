/**
 * 字典相关接口（供生成器/业务页面统一复用）
 */
import axios from 'axios'

/**
 * 根据字典 code 获取字典项列表
 * @param {string} code
 * @returns {Promise<import('axios').AxiosResponse<any>>}
 */
export function getDictByCode(code) {
  return axios.get('/dictdata/getDictByCode', { params: { code } })
}


