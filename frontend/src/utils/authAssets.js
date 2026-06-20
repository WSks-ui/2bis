export const AUTH_FALLBACK_SCENES = [
  {
    id: 'aria-showcase',
    image: '/auth/aria-showcase.webp',
    poster: '/auth/aria-poster.webp',
    preview: '/auth/aria-showcase-blur.webp',
    label: '2Bis current showcase'
  }
]

export const AUTH_SHOWCASE_MANIFEST_URL = '/auth/showcase/manifest.json'
export const AUTH_IMAGE_SOURCES = collectImageSources(AUTH_FALLBACK_SCENES)

const preloadedSources = new Set()
let authScenesPromise = null

function normalizeScene(scene, index) {
  if (typeof scene === 'string') {
    return {
      id: `scene-${index + 1}`,
      image: scene,
      label: `Auth scene ${index + 1}`
    }
  }

  if (!scene || typeof scene !== 'object') return null

  const image = scene.image || scene.src
  if (!image || typeof image !== 'string') return null

  return {
    id: scene.id || `scene-${index + 1}`,
    image,
    poster: scene.poster || '',
    preview: scene.preview || scene.blur || '',
    label: scene.label || `Auth scene ${index + 1}`
  }
}

function uniqueScenes(scenes) {
  const seen = new Set()

  return scenes.filter((scene) => {
    if (!scene?.image || seen.has(scene.image)) return false
    seen.add(scene.image)
    return true
  })
}

function collectImageSources(scenes) {
  return uniqueScenes(scenes)
    .flatMap((scene) => [scene.preview, scene.image, scene.poster])
    .filter(Boolean)
}

async function readManifestScenes() {
  const response = await fetch(AUTH_SHOWCASE_MANIFEST_URL, { cache: 'no-cache' })
  if (!response.ok) return []

  const payload = await response.json()
  const rawScenes = Array.isArray(payload) ? payload : payload.scenes || payload.images || []

  return rawScenes
    .map((scene, index) => normalizeScene(scene, index))
    .filter(Boolean)
}

export function getAuthShowcaseScenes() {
  if (typeof window === 'undefined' || typeof fetch === 'undefined') {
    return Promise.resolve(AUTH_FALLBACK_SCENES)
  }

  if (!authScenesPromise) {
    authScenesPromise = readManifestScenes()
      .then((manifestScenes) => {
        // manifest 里的图片优先，默认图兜底；新增图片只影响场景清单，不需要改认证页布局。
        const scenes = uniqueScenes([...manifestScenes, ...AUTH_FALLBACK_SCENES])
        return scenes.length ? scenes : AUTH_FALLBACK_SCENES
      })
      .catch((error) => {
        console.warn('[auth-assets] showcase manifest skipped', error)
        return AUTH_FALLBACK_SCENES
      })
  }

  return authScenesPromise
}

export function preloadAuthImages(scenes = AUTH_FALLBACK_SCENES) {
  if (typeof window === 'undefined') return

  collectImageSources([...AUTH_FALLBACK_SCENES, ...scenes]).forEach((src) => {
    if (preloadedSources.has(src)) return
    preloadedSources.add(src)

    const image = new Image()
    image.src = src
    image.decoding = 'async'
    image.decode?.().catch(() => {
      // 图片预热失败不应阻断应用启动，真实 <img> 仍会按浏览器默认链路加载。
    })
  })
}
