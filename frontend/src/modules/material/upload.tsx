import { useState } from 'react'
import { Card, Button, Upload, message, Tag, Progress, List, Space } from 'antd'
import { InboxOutlined } from '@ant-design/icons'
import { uploadMaterial } from '../../utils/api'
import type { UploadFile } from 'antd'

export default function MaterialUpload() {
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState({ current: 0, total: 0 })
  const [results, setResults] = useState<{ name: string; status: 'ok' | 'fail'; msg: string }[]>([])

  const detectType = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase() || ''
    if (['mp3', 'wav', 'm4a', 'ogg', 'flac', 'aac'].includes(ext)) return 'audio'
    if (['mp4', 'webm', 'mov', 'avi', 'mkv'].includes(ext)) return 'video'
    return 'image'
  }

  const uploadAll = async () => {
    if (fileList.length === 0) return message.warning('请选择文件')
    setUploading(true)
    setResults([])
    const files = fileList.map(f => (f as any).originFileObj || f)

    for (let i = 0; i < files.length; i++) {
      const f = files[i]
      setProgress({ current: i + 1, total: files.length })
      const autoType = detectType(f.name || '')
      const fd = new FormData()
      fd.append('material_type', autoType)
      fd.append('input_type', autoType)
      fd.append('category', '其他')
      fd.append('name', f.name?.replace(/\.[^.]+$/, '') || '未命名')
      fd.append('file', f)

      try {
        await uploadMaterial(fd)
        setResults(prev => [...prev, { name: f.name || '', status: 'ok', msg: '上传成功' }])
      } catch (e: any) {
        const detail = e?.response?.data?.detail || e?.message || '上传失败'
        setResults(prev => [...prev, { name: f.name || '', status: 'fail', msg: typeof detail === 'string' ? detail : '上传失败' }])
      }
    }

    setUploading(false)
    const okCount = results.filter(r => r.status === 'ok').length + 1
    const failCount = results.filter(r => r.status === 'fail').length
    const totalOk = okCount > 0 ? okCount : 0
    if (totalOk > 0) message.success(`${totalOk} 个文件上传成功`)
    if (failCount > 0) message.error(`${failCount} 个文件上传失败`)
  }

  const typeIcons: Record<string, string> = { audio: '🎵 BGM', video: '🎬 视频', image: '🖼️ 图片' }

  return (
    <Card title="上传素材（批量）">
      <Upload.Dragger
        multiple
        fileList={fileList}
        beforeUpload={(f) => { setFileList(prev => [...prev, f]); return false }}
        onRemove={(f) => setFileList(prev => prev.filter(x => x.uid !== f.uid))}
        showUploadList={false}
        accept="image/*,video/*,audio/*">
        <p className="ant-upload-drag-icon"><InboxOutlined /></p>
        <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
        <p className="ant-upload-hint">支持批量选择，自动检测类型，文件名作为素材名称</p>
      </Upload.Dragger>

      {fileList.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>
            已选 {fileList.length} 个文件
          </div>
          <List size="small" dataSource={fileList} renderItem={(f) => {
            const type = detectType(f.name || '')
            return (
              <List.Item>
                <Space>
                  <Tag color={type === 'audio' ? 'purple' : type === 'video' ? 'blue' : 'green'}>
                    {typeIcons[type] || type}
                  </Tag>
                  <span>{f.name}</span>
                  <Tag color="default">→ {f.name?.replace(/\.[^.]+$/, '')}</Tag>
                </Space>
              </List.Item>
            )
          }} />
        </div>
      )}

      {uploading && (
        <div style={{ marginTop: 12 }}>
          <Progress percent={Math.round(progress.current / progress.total * 100)}
            format={() => `${progress.current}/${progress.total}`} />
        </div>
      )}

      {results.length > 0 && (
        <div style={{ marginTop: 12, maxHeight: 200, overflow: 'auto' }}>
          <List size="small" dataSource={results} renderItem={(r) => (
            <List.Item>
              <Space>
                <Tag color={r.status === 'ok' ? 'green' : 'red'}>{r.status === 'ok' ? '✓' : '✗'}</Tag>
                <span style={{ fontSize: 12 }}>{r.name}</span>
                <span style={{ fontSize: 11, color: '#999' }}>{r.msg}</span>
              </Space>
            </List.Item>
          )} />
        </div>
      )}

      <div style={{ marginTop: 16, textAlign: 'center' }}>
        <Button type="primary" onClick={uploadAll} loading={uploading}
          disabled={fileList.length === 0}
          icon={<InboxOutlined />} size="large">
          {uploading ? `正在上传 ${progress.current}/${progress.total}` : `上传 ${fileList.length} 个文件`}
        </Button>
        {!uploading && fileList.length > 0 && (
          <Button style={{ marginLeft: 8 }} onClick={() => { setFileList([]); setResults([]) }}>
            清空列表
          </Button>
        )}
      </div>
    </Card>
  )
}
