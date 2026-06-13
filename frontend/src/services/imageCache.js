const FULL_IMAGE_CACHE_LIMIT = 10
const fullImageCache = new Map()
const thumbnailPreloadCache = new Set()

export function preloadThumbnails(records = []) {
  records.forEach((record) => {
    const url = record.thumbnail_url || record.image_url
    if (!url || thumbnailPreloadCache.has(url)) return
    thumbnailPreloadCache.add(url)
    const image = new Image()
    image.decoding = 'async'
    image.loading = 'eager'
    image.src = url
  })
}

export function warmFullImage(record) {
  const url = record?.image_url
  if (!url) return Promise.resolve('')

  const cached = fullImageCache.get(url)
  if (cached) {
    fullImageCache.delete(url)
    fullImageCache.set(url, cached)
    return cached.promise
  }

  const image = new Image()
  image.decoding = 'async'
  const promise = new Promise((resolve, reject) => {
    image.onload = () => resolve(url)
    image.onerror = () => {
      fullImageCache.delete(url)
      reject(new Error('Image preload failed'))
    }
  })

  fullImageCache.set(url, { image, promise })
  trimFullImageCache()
  image.src = url
  return promise
}

export function getCachedFullImageUrl(record) {
  const url = record?.image_url
  if (!url || !fullImageCache.has(url)) return ''
  const entry = fullImageCache.get(url)
  fullImageCache.delete(url)
  fullImageCache.set(url, entry)
  return url
}

export function removeCachedImage(record) {
  const fullUrl = record?.image_url
  if (fullUrl) fullImageCache.delete(fullUrl)
  const thumbUrl = record?.thumbnail_url
  if (thumbUrl) thumbnailPreloadCache.delete(thumbUrl)
}

function trimFullImageCache() {
  while (fullImageCache.size > FULL_IMAGE_CACHE_LIMIT) {
    const oldestKey = fullImageCache.keys().next().value
    fullImageCache.delete(oldestKey)
  }
}
