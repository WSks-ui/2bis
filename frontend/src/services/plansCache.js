import api from '../api'

const PLANS_CACHE_MAX_AGE = 5 * 60 * 1000

let cachedPlans = null
let cachedAt = 0
let pendingPlansRequest = null

export function readCachedPlans() {
  return cachedPlans ? clonePlans(cachedPlans) : null
}

export async function fetchPlansConfig(options = {}) {
  const now = Date.now()
  if (!options.force && cachedPlans && now - cachedAt <= PLANS_CACHE_MAX_AGE) {
    return clonePlans(cachedPlans)
  }

  if (!options.force && pendingPlansRequest) {
    return pendingPlansRequest
  }

  pendingPlansRequest = api
    .get('/points/plans')
    .then((res) => {
      cachedPlans = res.data || {}
      cachedAt = Date.now()
      return clonePlans(cachedPlans)
    })
    .finally(() => {
      pendingPlansRequest = null
    })

  return pendingPlansRequest
}

export function warmPlansConfig() {
  return fetchPlansConfig().catch(() => null)
}

function clonePlans(data) {
  return {
    ...data,
    trial_pack: data.trial_pack ? { ...data.trial_pack } : data.trial_pack,
    subscription_plans: Array.isArray(data.subscription_plans)
      ? data.subscription_plans.map((plan) => ({ ...plan }))
      : data.subscription_plans,
    workflow_presets: Array.isArray(data.workflow_presets)
      ? data.workflow_presets.map((preset) => ({
          ...preset,
          costs: preset.costs ? { ...preset.costs } : preset.costs
        }))
      : data.workflow_presets,
    generation_options: cloneGenerationOptions(data.generation_options)
  }
}

function cloneGenerationOptions(options) {
  if (!options) return options
  return {
    ...options,
    qualities: Array.isArray(options.qualities)
      ? options.qualities.map((item) => ({ ...item }))
      : options.qualities,
    image_size_groups: Array.isArray(options.image_size_groups)
      ? options.image_size_groups.map((group) => ({
          ...group,
          sizes: Array.isArray(group.sizes) ? group.sizes.map((size) => ({ ...size })) : group.sizes
        }))
      : options.image_size_groups
  }
}
