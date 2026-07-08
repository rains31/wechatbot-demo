import api from './client'

export interface WechatBindInitiateResponse {
  binding_id: number
  qr_url: string
  status: string
}

export interface WechatBindStatusResponse {
  binding_id: number
  status: string
  qr_url: string | null
  wechat_nickname: string | null
  has_context: boolean
}

export interface WechatBindingInfo {
  id: number
  user_id: number
  status: string
  qr_url: string | null
  account_id: string | null
  wechat_user_id: string | null
  wechat_nickname: string | null
  created_at: string
}

export interface WechatSendTestResponse {
  success: bool
  message: string
}

export const wechatApi = {
  initiateBind: async () => {
    const response = await api.post<WechatBindInitiateResponse>('/api/wechat/bind')
    return response.data
  },

  getBindStatus: async (bindingId: number) => {
    const response = await api.get<WechatBindStatusResponse>(`/api/wechat/bind/${bindingId}/status`)
    return response.data
  },

  getCurrentBindStatus: async () => {
    const response = await api.get<WechatBindingInfo | null>('/api/wechat/bind/status')
    return response.data
  },

  unbind: async () => {
    const response = await api.delete('/api/wechat/bind')
    return response.data
  },

  sendTest: async (messageText: string) => {
    const response = await api.post<WechatSendTestResponse>('/api/wechat/send-test', {
      message: messageText
    })
    return response.data
  }
}
