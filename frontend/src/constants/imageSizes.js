export const IMAGE_SIZE_GROUPS = [
  {
    ratio: '21:9',
    name: '超宽银幕',
    sizes: [
      { label: '影院高清', value: '3584x1536' },
      { label: '超宽标准', value: '2688x1152' },
      { label: '超宽轻量', value: '1792x768' },
    ],
  },
  {
    ratio: '16:9',
    name: '横版宽屏',
    sizes: [
      { label: '4K 宽屏', value: '3840x2160' },
      { label: '高清宽屏', value: '2560x1440' },
      { label: '标准宽屏', value: '1920x1080' },
      { label: '轻量宽屏', value: '1344x768' },
    ],
  },
  {
    ratio: '3:2',
    name: '相机横幅',
    sizes: [
      { label: '高清横幅', value: '3456x2304' },
      { label: '标准横幅', value: '2304x1536' },
      { label: '轻量横幅', value: '1728x1152' },
    ],
  },
  {
    ratio: '4:3',
    name: '经典横图',
    sizes: [
      { label: '高清横图', value: '3072x2304' },
      { label: '标准横图', value: '2048x1536' },
      { label: '轻量横图', value: '1536x1152' },
      { label: '平台轻量', value: '1152x896' },
    ],
  },
  {
    ratio: '1:1',
    name: '方图',
    sizes: [
      { label: '高清方图', value: '2048x2048' },
      { label: '标准方图', value: '1536x1536' },
      { label: '轻量方图', value: '1024x1024' },
    ],
  },
  {
    ratio: '3:4',
    name: '经典竖图',
    sizes: [
      { label: '高清竖图', value: '2304x3072' },
      { label: '平台竖图', value: '1792x2304' },
      { label: '标准竖图', value: '1536x2048' },
      { label: '轻量竖图', value: '1152x1536' },
      { label: '平台轻量', value: '896x1152' },
    ],
  },
  {
    ratio: '2:3',
    name: '海报竖图',
    sizes: [
      { label: '高清海报', value: '2304x3456' },
      { label: '标准海报', value: '1536x2304' },
      { label: '轻量海报', value: '1152x1728' },
    ],
  },
  {
    ratio: '9:16',
    name: '移动竖屏',
    sizes: [
      { label: '4K 竖屏', value: '2160x3840' },
      { label: '高清竖屏', value: '1440x2560' },
      { label: '标准竖屏', value: '1080x1920' },
      { label: '轻量竖屏', value: '720x1280' },
    ],
  },
]

export function formatImageSize(value) {
  return value.replace('x', '×')
}

export function formatImageSizeTier(value) {
  const [width, height] = value.split('x').map(Number)
  const longSide = Math.max(width || 0, height || 0)
  const shortSide = Math.min(width || 0, height || 0)
  // 只隐藏具体像素，不改变实际提交值；按常见图像档位把 2048 级别归为 2k。
  if (longSide >= 3000) return '4k'
  if (longSide >= 2048 || shortSide >= 1536) return '2k'
  return '1k'
}

export function imageMegapixels(value) {
  const [width, height] = value.split('x').map(Number)
  if (!width || !height) return ''
  return `${((width * height) / 1000000).toFixed(1)}MP`
}
