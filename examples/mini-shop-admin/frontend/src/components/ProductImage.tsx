import { useState } from 'react'

export function ProductImage({
  src,
  alt,
  className = 'product-image',
}: {
  src: string
  alt: string
  className?: string
}) {
  const [failed, setFailed] = useState(false)

  if (failed || !src) {
    return (
      <div className={`${className} image-placeholder`} role="img" aria-label={`${alt}图片无法加载`}>
        <span aria-hidden="true">▧</span>
      </div>
    )
  }

  return (
    <img
      className={className}
      src={src}
      alt={alt}
      onError={() => setFailed(true)}
    />
  )
}
