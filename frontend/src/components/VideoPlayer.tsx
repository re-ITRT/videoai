import { useRef, useState } from 'react'

interface VideoPlayerProps {
  url?: string | null
  poster?: string | null
  aspectRatio?: '16:9' | '9:16' | '1:1'
}

const aspectRatioMap: Record<string, string> = {
  '16:9': '56.25%',
  '9:16': '177.78%',
  '1:1': '100%',
}

export default function VideoPlayer({ url, poster, aspectRatio = '16:9' }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [error, setError] = useState(false)

  if (!url) {
    return (
      <div
        style={{
          width: '100%',
          paddingBottom: aspectRatioMap[aspectRatio] || '56.25%',
          position: 'relative',
          background: '#f5f5f5',
          borderRadius: 8,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#999',
            fontSize: 16,
          }}
        >
          暂无视频
        </div>
      </div>
    )
  }

  return (
    <div
      style={{
        width: '100%',
        paddingBottom: aspectRatioMap[aspectRatio] || '56.25%',
        position: 'relative',
        borderRadius: 8,
        overflow: 'hidden',
        background: '#000',
      }}
    >
      {error ? (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#ff4d4f',
            fontSize: 16,
          }}
        >
          视频加载失败
        </div>
      ) : (
        <video
          ref={videoRef}
          src={url}
          poster={poster || undefined}
          controls
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            objectFit: 'contain',
          }}
          onError={() => setError(true)}
        />
      )}
    </div>
  )
}
