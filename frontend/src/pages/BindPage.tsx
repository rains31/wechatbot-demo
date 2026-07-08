import React, { useState, useEffect } from 'react'
import { Card, Button, message, Space, Typography, Tag, Divider, Modal, Select, Input } from 'antd'
import { WechatOutlined, SendOutlined, CheckCircleOutlined, UserOutlined, PlusOutlined } from '@ant-design/icons'
import { wechatApi, WechatBindingInfo } from '../api/wechat'

const { Title, Text } = Typography

const BindPage: React.FC = () => {
  const [users, setUsers] = useState<string[]>(['1', '2', '3'])
  const [currentUserId, setCurrentUserId] = useState<string>('1')
  const [newUserId, setNewUserId] = useState<string>('')
  
  const [wechatInfo, setWechatInfo] = useState<WechatBindingInfo | null>(null)
  const [wechatBindingId, setWechatBindingId] = useState<number | null>(null)
  const [qrUrl, setQrUrl] = useState<string | null>(null)
  const [wechatStatus, setWechatStatus] = useState<string | null>(null)
  const [wechatModalVisible, setWechatModalVisible] = useState(false)
  const [wechatLoading, setWechatLoading] = useState(false)
  const [wechatPollTimer, setWechatPollTimer] = useState<any>(null)

  const loadWechatStatus = async () => {
    try {
      const data = await wechatApi.getCurrentBindStatus()
      setWechatInfo(data)
      setWechatStatus(data ? data.status : null)
    } catch {
      setWechatInfo(null)
      setWechatStatus(null)
    }
  }

  // 初始化或切换用户时
  useEffect(() => {
    localStorage.setItem('current_user_id', currentUserId)
    loadWechatStatus()
    // 切换用户时清空之前未完成的弹窗和轮询
    if (wechatPollTimer) {
      clearInterval(wechatPollTimer)
      setWechatPollTimer(null)
    }
    setWechatModalVisible(false)
  }, [currentUserId])

  const handleAddUser = () => {
    if (!newUserId.trim()) {
      return message.warning('请输入有效的模拟用户 ID')
    }
    if (users.includes(newUserId.trim())) {
      return message.warning('该模拟用户已存在')
    }
    setUsers([...users, newUserId.trim()])
    setCurrentUserId(newUserId.trim())
    setNewUserId('')
    message.success(`成功切换至新增模拟用户: ${newUserId.trim()}`)
  }

  const handleStartBind = async () => {
    try {
      setWechatLoading(true)
      const data = await wechatApi.initiateBind()
      setWechatBindingId(data.binding_id)
      setQrUrl(data.qr_url)
      setWechatStatus(data.status)
      setWechatModalVisible(true)

      const timer = setInterval(async () => {
        try {
          const status = await wechatApi.getBindStatus(data.binding_id)
          setQrUrl(status.qr_url)
          setWechatStatus(status.status)

          if (status.status === 'bound') {
            if (status.has_context) {
              clearInterval(timer)
              message.success('微信绑定成功！')
              setWechatModalVisible(false)
              loadWechatStatus()
            }
          } else if (status.status === 'expired' || status.status === 'failed') {
            clearInterval(timer)
            message.warning('扫码已过期或失败，请重新绑定')
          }
        } catch {
          // 继续轮询
        }
      }, 2000)
      setWechatPollTimer(timer)
    } catch (error: any) {
      message.error(error.response?.data?.detail || '发起绑定失败')
    } finally {
      setWechatLoading(false)
    }
  }

  const handleUnbind = async () => {
    Modal.confirm({
      title: '确认解绑微信?',
      content: '解绑后将无法通过微信接收系统通知。',
      okType: 'danger',
      onOk: async () => {
        try {
          await wechatApi.unbind()
          message.success('微信解绑成功')
          loadWechatStatus()
        } catch (error) {
          message.error('解绑失败')
        }
      }
    })
  }

  const handleSendTest = async () => {
    try {
      setWechatLoading(true)
      await wechatApi.sendTest('这是一条来自 Wechatbot-Demo 的测试消息 🚀')
      message.success('测试消息发送成功！请查看微信通知。')
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || '发送失败'
      if (errorMsg.includes('请先给机器人发送一条消息') || errorMsg.includes('打招呼')) {
        Modal.warning({
          title: '需要进行打招呼确认',
          content: (
            <div style={{ padding: '10px 0' }}>
              <p>为了启用通知推送，您需要主动激活微信会话。</p>
              <p style={{ fontWeight: 'bold', color: '#fa8c16' }}>请先给微信机器人发送一条消息（如 "你好"），之后即可正常接收通知。</p>
            </div>
          ),
          okText: '我知道了',
        })
      } else {
        message.error(errorMsg)
      }
    } finally {
      setWechatLoading(false)
    }
  }

  const handleCloseWechatModal = () => {
    setWechatModalVisible(false)
    if (wechatPollTimer) {
      clearInterval(wechatPollTimer)
      setWechatPollTimer(null)
    }
  }

  return (
    <div style={{ maxWidth: 600, margin: '50px auto', padding: '0 20px' }}>
      <Card 
        title={<Space><UserOutlined />多用户模拟控制</Space>} 
        style={{ marginBottom: 20 }}
      >
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
          <div>
            <span style={{ marginRight: 8 }}>当前模拟用户:</span>
            <Select
              value={currentUserId}
              onChange={(val) => setCurrentUserId(val)}
              style={{ width: 120 }}
              options={users.map(u => ({ label: `User ${u}`, value: u }))}
            />
          </div>
          
          <Divider type="vertical" style={{ height: 32 }} />

          <Space.Compact style={{ flex: 1, minWidth: 200 }}>
            <Input 
              placeholder="新增模拟用户ID (如 4)" 
              value={newUserId}
              onChange={(e) => setNewUserId(e.target.value)}
              onPressEnter={handleAddUser}
            />
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAddUser}>增加用户</Button>
          </Space.Compact>
        </div>
      </Card>

      <Card title={<Space><WechatOutlined />微信消息通知绑定 (模拟 User {currentUserId})</Space>}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <Text strong>绑定微信通知</Text>
          {wechatInfo ? (
            <Space>
              <Button icon={<SendOutlined />} onClick={handleSendTest} loading={wechatLoading}>发送测试</Button>
              <Button danger onClick={handleUnbind}>解绑</Button>
            </Space>
          ) : (
            <Button type="primary" icon={<WechatOutlined />} onClick={handleStartBind} loading={wechatLoading}>绑定微信</Button>
          )}
        </div>
        
        {wechatInfo ? (
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <Tag color="green">已绑定</Tag>
              <Text>{wechatInfo.wechat_nickname ? `微信昵称: ${wechatInfo.wechat_nickname}` : '微信已绑定'}</Text>
            </div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              绑定时间: {new Date(wechatInfo.created_at).toLocaleString()}
            </Text>
          </Space>
        ) : (
          <Text type="secondary">尚未绑定微信，绑定后可通过微信接收系统通知</Text>
        )}
      </Card>

      <Modal
        title="绑定微信"
        open={wechatModalVisible}
        onCancel={handleCloseWechatModal}
        footer={null}
        destroyOnClose
      >
        <div style={{ textAlign: 'center', padding: '20px 0' }}>
          {wechatStatus === 'pending' || wechatStatus === 'scanned' ? (
            <>
              {qrUrl ? (
                <>
                  <p style={{ marginBottom: 16 }}>请使用微信扫描下方二维码：</p>
                  <img
                    src={`https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(qrUrl)}`}
                    alt="微信二维码"
                    style={{ width: 250, height: 250, marginBottom: 16 }}
                  />
                </>
              ) : (
                <p style={{ marginBottom: 16 }}>正在生成二维码，请稍候…</p>
              )}
              {wechatStatus === 'scanned' && (
                <Tag color="blue" style={{ marginBottom: 16, fontSize: 14, padding: '4px 12px' }}>
                  已扫码，请在手机微信上确认登录
                </Tag>
              )}
              {wechatStatus === 'pending' && (
                <div style={{ color: 'rgba(0, 0, 0, 0.45)', marginTop: 8 }}>
                  二维码有效期为 2 分钟，过期后自动刷新
                </div>
              )}
            </>
          ) : wechatStatus === 'bound' ? (
            <div style={{ padding: '10px 0' }}>
              <CheckCircleOutlined style={{ fontSize: 64, color: '#52c41a', marginBottom: 20 }} />
              <div style={{ fontSize: 18, fontWeight: 'bold', marginBottom: 12 }}>已成功扫描并授权</div>
              <div style={{ color: '#fa8c16', fontSize: 14, fontWeight: 'bold', padding: '0 20px' }}>
                请在 AI Bot 对话框发送任意内容进行绑定确认
              </div>
            </div>
          ) : wechatStatus === 'expired' ? (
            <>
              <p>二维码已过期</p>
              <Button type="primary" onClick={handleStartBind} loading={wechatLoading}>重新绑定</Button>
            </>
          ) : (
            <p>状态: {wechatStatus}</p>
          )}
        </div>
      </Modal>
    </div>
  )
}

export default BindPage
