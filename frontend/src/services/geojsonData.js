import { getPois, getStudyRooms } from './api'

export const EMPTY_FEATURE_COLLECTION = {
  type: 'FeatureCollection',
  features: []
}

const datasetLoaders = {
  studyRooms: getStudyRooms,
  pois: getPois
}

export function textOrUnknown(value) {
  if (value === null || value === undefined || value === '') {
    return '未知'
  }

  if (Array.isArray(value)) {
    return value.length ? value.join('、') : '未知'
  }

  if (typeof value === 'boolean') {
    return value ? '是' : '否'
  }

  return String(value)
}

export function normalizeFeatureCollection(data) {
  if (!data || data.type !== 'FeatureCollection' || !Array.isArray(data.features)) {
    return EMPTY_FEATURE_COLLECTION
  }

  return data
}

export function getFeatureCoordinate(feature) {
  const coordinates = feature?.geometry?.coordinates

  if (
    feature?.geometry?.type !== 'Point' ||
    !Array.isArray(coordinates) ||
    coordinates.length < 2
  ) {
    return null
  }

  const [longitude, latitude] = coordinates
  if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) {
    return null
  }

  return { latitude, longitude }
}

async function loadDataset(key) {
  const loader = datasetLoaders[key]

  if (!loader) {
    return {
      data: EMPTY_FEATURE_COLLECTION,
      error: '未知数据集'
    }
  }

  try {
    const response = await loader()
    return {
      data: normalizeFeatureCollection(response.data),
      error: ''
    }
  } catch (error) {
    return {
      data: EMPTY_FEATURE_COLLECTION,
      error: '后端暂不可用，当前展示空数据/示例数据。'
    }
  }
}

export async function loadMapDatasets() {
  const [studyRooms, pois] = await Promise.all([
    loadDataset('studyRooms'),
    loadDataset('pois')
  ])

  return {
    studyRooms,
    pois
  }
}
