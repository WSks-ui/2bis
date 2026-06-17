import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

const SAMPLE_SIZE = 32
const MAX_SAMPLE_ATTEMPTS = 24
const SAMPLE_RETRY_DELAY = 80

let cachedPalette = null
let cachedPaletteSource = ''

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function rgbToHsl(red, green, blue) {
  const r = red / 255
  const g = green / 255
  const b = blue / 255
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  const lightness = (max + min) / 2
  const delta = max - min

  if (delta === 0) {
    return { hue: 210, saturation: 0, lightness }
  }

  const saturation = delta / (1 - Math.abs(2 * lightness - 1))
  let hue = 0

  if (max === r) {
    hue = ((g - b) / delta) % 6
  } else if (max === g) {
    hue = (b - r) / delta + 2
  } else {
    hue = (r - g) / delta + 4
  }

  return {
    hue: Math.round(hue * 60 < 0 ? hue * 60 + 360 : hue * 60),
    saturation,
    lightness
  }
}

function hslToRgb(hue, saturation, lightness) {
  const chroma = (1 - Math.abs(2 * lightness - 1)) * saturation
  const x = chroma * (1 - Math.abs(((hue / 60) % 2) - 1))
  const m = lightness - chroma / 2
  let r = 0
  let g = 0
  let b = 0

  if (hue < 60) {
    r = chroma
    g = x
  } else if (hue < 120) {
    r = x
    g = chroma
  } else if (hue < 180) {
    g = chroma
    b = x
  } else if (hue < 240) {
    g = x
    b = chroma
  } else if (hue < 300) {
    r = x
    b = chroma
  } else {
    r = chroma
    b = x
  }

  return {
    red: Math.round((r + m) * 255),
    green: Math.round((g + m) * 255),
    blue: Math.round((b + m) * 255)
  }
}

function buildPalette(red, green, blue) {
  const hsl = rgbToHsl(red, green, blue)
  const hue = hsl.hue
  const saturation = clamp(hsl.saturation * 0.86 + 0.18, 0.28, 0.62)
  const accent = hslToRgb(hue, clamp(hsl.saturation * 1.05 + 0.18, 0.38, 0.74), 0.43)
  const warmHue = (hue + 28) % 360
  const warm = hslToRgb(warmHue, clamp(saturation * 0.82, 0.16, 0.42), 0.72)

  return {
    '--auth-accent-rgb': `${accent.red} ${accent.green} ${accent.blue}`,
    '--auth-warm-rgb': `${warm.red} ${warm.green} ${warm.blue}`,
    '--auth-panel-bg-start': `hsl(${hue}deg ${Math.round(saturation * 46)}% 99%)`,
    '--auth-panel-bg-mid': `hsl(${hue}deg ${Math.round(saturation * 52)}% 96%)`,
    '--auth-panel-bg-end': `hsl(${warmHue}deg ${Math.round(saturation * 40)}% 93%)`,
    '--auth-card-bg': `rgba(255, 255, 255, 0.82)`,
    '--auth-control-bg': `hsl(${hue}deg ${Math.round(saturation * 34)}% 94%)`,
    '--auth-control-bg-strong': `hsl(${hue}deg ${Math.round(saturation * 30)}% 91%)`,
    '--auth-panel-line': `rgb(${accent.red} ${accent.green} ${accent.blue} / 0.16)`,
    '--auth-panel-shadow': `rgb(${accent.red} ${accent.green} ${accent.blue} / 0.12)`
  }
}

// 首屏 fallback 使用当前展示图的离线均值，避免图片采样完成前出现默认蓝色割裂。
const DEFAULT_AUTH_PALETTE = buildPalette(30, 43, 33)

function readAverageColor(image) {
  const canvas = document.createElement('canvas')
  canvas.width = SAMPLE_SIZE
  canvas.height = SAMPLE_SIZE
  const context = canvas.getContext('2d', { willReadFrequently: true })

  if (!context) return null

  context.drawImage(image, 0, 0, SAMPLE_SIZE, SAMPLE_SIZE)
  const { data } = context.getImageData(0, 0, SAMPLE_SIZE, SAMPLE_SIZE)
  let totalWeight = 0
  let red = 0
  let green = 0
  let blue = 0

  for (let index = 0; index < data.length; index += 4) {
    const alpha = data[index + 3] / 255
    if (alpha < 0.2) continue

    const r = data[index]
    const g = data[index + 1]
    const b = data[index + 2]
    const max = Math.max(r, g, b)
    const min = Math.min(r, g, b)
    const luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
    const saturation = max === 0 ? 0 : (max - min) / max
    // 过滤纯黑阴影和极亮高光，让主题色更接近图片的环境色，而不是被局部噪声带偏。
    const luminanceWeight = luminance < 0.08 ? 0.2 : luminance > 0.88 ? 0.35 : 0.72 + luminance * 0.5
    const colorWeight = alpha * luminanceWeight * (0.58 + saturation * 1.35)

    red += r * colorWeight
    green += g * colorWeight
    blue += b * colorWeight
    totalWeight += colorWeight
  }

  if (!totalWeight) return null

  return {
    red: Math.round(red / totalWeight),
    green: Math.round(green / totalWeight),
    blue: Math.round(blue / totalWeight)
  }
}

function applyPalette(palette, source = 'image') {
  cachedPalette = palette
  cachedPaletteSource = source

  const targets = [
    document.documentElement,
    document.querySelector('.auth-switch-host')
  ].filter(Boolean)

  Object.entries(palette).forEach(([name, value]) => {
    targets.forEach((target) => {
      target.style.setProperty(name, value)
    })
  })

  targets.forEach((target) => {
    target.setAttribute('data-auth-theme-source', source)
    target.setAttribute('data-auth-theme-accent', palette['--auth-accent-rgb'])
  })
}

export function useAdaptiveAuthTheme(options = {}) {
  const showcaseImageRef = ref(null)
  const imageSelector = options.imageSelector || '.auth-page-login .showcase-image'
  let removeLoadListener = null
  let retryTimer = 0
  let sampleTaskTimer = 0
  let sampleAttempts = 0
  let observer = null

  function resolveShowcaseImage() {
    return showcaseImageRef.value || document.querySelector(imageSelector)
  }

  function clearRetryTimer() {
    if (!retryTimer) return
    window.clearTimeout(retryTimer)
    retryTimer = 0
  }

  function clearSampleTaskTimer() {
    if (!sampleTaskTimer) return
    window.clearTimeout(sampleTaskTimer)
    sampleTaskTimer = 0
  }

  function removeImageListener() {
    removeLoadListener?.()
    removeLoadListener = null
  }

  function stopObserver() {
    observer?.disconnect()
    observer = null
  }

  function queueImageSample(callback) {
    clearSampleTaskTimer()
    sampleTaskTimer = window.setTimeout(() => {
      sampleTaskTimer = 0
      callback()
    }, 0)
  }

  function sampleImageTheme(image = resolveShowcaseImage()) {
    if (!image || !image.naturalWidth || !image.naturalHeight) return false

    try {
      const color = readAverageColor(image)
      if (color) {
        applyPalette(buildPalette(color.red, color.green, color.blue), 'image')
        stopObserver()
        clearRetryTimer()
        return true
      }
    } catch (error) {
      // 如果未来展示图切到跨域资源，canvas 可能被浏览器拦截；此时保留 fallback，页面仍可用。
      console.warn('[auth-theme] image palette sampling skipped', error)
    }

    return false
  }

  function scheduleSample() {
    clearRetryTimer()
    sampleAttempts += 1

    if (sampleAttempts > MAX_SAMPLE_ATTEMPTS) {
      return
    }

    retryTimer = window.setTimeout(() => {
      retryTimer = 0
      prepareImageSampling()
    }, SAMPLE_RETRY_DELAY)
  }

  function prepareImageSampling() {
    const image = resolveShowcaseImage()

    if (!image) {
      scheduleSample()
      return
    }

    if (image.complete && image.naturalWidth) {
      queueImageSample(() => {
        if (!sampleImageTheme(image)) {
          scheduleSample()
        }
      })
      return
    }

    removeImageListener()
    const handleLoad = () => {
      queueImageSample(() => {
        if (!sampleImageTheme(image)) {
          scheduleSample()
        }
      })
    }

    image.addEventListener('load', handleLoad, { once: true })
    removeLoadListener = () => image.removeEventListener('load', handleLoad)
    // 缓存图片可能在监听绑定前后快速完成，额外保留短重试可覆盖 load 事件竞态。
    scheduleSample()
  }

  function observeShowcaseImage() {
    if (typeof MutationObserver === 'undefined') return

    stopObserver()
    observer = new MutationObserver(() => {
      sampleAttempts = 0
      prepareImageSampling()
    })

    observer.observe(document.body, {
      childList: true,
      subtree: true
    })
  }

  onMounted(() => {
    if (cachedPalette && cachedPaletteSource === 'image') {
      // 注册页直开时先复用最近一次真实取色结果，随后等待图片完成后再校准。
      applyPalette(cachedPalette, cachedPaletteSource)
    } else {
      applyPalette(DEFAULT_AUTH_PALETTE, 'fallback')
    }

    nextTick(() => {
      observeShowcaseImage()
      queueImageSample(prepareImageSampling)
    })
  })

  onBeforeUnmount(() => {
    clearRetryTimer()
    clearSampleTaskTimer()
    removeImageListener()
    stopObserver()
  })

  return {
    showcaseImageRef
  }
}
