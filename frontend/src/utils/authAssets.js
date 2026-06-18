export const AUTH_IMAGE_SOURCES = [
  '/auth/aria-showcase.webp',
  '/auth/aria-poster.webp',
  '/auth/aria-showcase-blur.webp'
]

let authImagesPreloaded = false

export function preloadAuthImages() {
  if (authImagesPreloaded || typeof window === 'undefined') return
  authImagesPreloaded = true

  // HTML preload 负责提前下载，这里补充 decode，避免切换认证页时才触发图片解码。
  AUTH_IMAGE_SOURCES.forEach((src) => {
    const image = new Image()
    image.src = src
    image.decoding = 'async'
    image.decode?.().catch(() => {
      // 图片预热失败不应阻断应用启动，真实 <img> 仍会按浏览器默认链路加载。
    })
  })
}
