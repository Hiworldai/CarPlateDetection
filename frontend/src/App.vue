<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { api, login, logout, mediaUrl, recognitionParams } from './api/client'

const LOCAL_RECORDS_KEY = 'car-plate-guest-records'

const imageFile = ref(null)
const videoFile = ref(null)
const imagePreview = ref('')
const latestRecords = ref([])
const records = ref([])
const total = ref(0)
const page = ref(1)
const perPage = ref(10)
const loading = ref(false)
const cameraRunning = ref(false)
const cameraUploading = ref(false)
const cameraMessage = ref('')
const imageMessage = ref('')
const videoMessage = ref('')
const exportMessage = ref('')
const authMessage = ref('')
const currentJob = ref(null)
const pollTimer = ref(null)
const cameraTimer = ref(null)
const videoRef = ref(null)
const canvasRef = ref(null)
const streamRef = ref(null)
const previewBuildId = ref(0)
const uploadOverlay = reactive({
  visible: false,
  title: '',
  message: '',
  fileName: '',
  fileSize: '',
  sentPercent: 0,
  gameX: 50,
  gameY: 50,
  score: 0
})

const LARGE_FILE_BYTES = 2 * 1024 * 1024
const IMAGE_UPLOAD_MAX_SIDE = 1920
const IMAGE_PREVIEW_MAX_SIDE = 900
const IMAGE_UPLOAD_QUALITY = 0.86
const IMAGE_PREVIEW_QUALITY = 0.72

const auth = reactive({
  checked: false,
  authenticated: false,
  username: '',
  storage_mode: 'local'
})

const loginForm = reactive({
  username: '',
  password: ''
})

const filters = reactive({
  plate_text: '',
  source_type: '',
  start_time: '',
  end_time: ''
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / perPage.value)))
const isGuestMode = computed(() => !auth.authenticated)
const modeLabel = computed(() => (auth.authenticated ? '登录模式' : '游客模式'))

const recordDateFormatter = new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false
})

function hasTimezone(value) {
  return /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)
}

function parseRecordDate(value) {
  if (!value) return null
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value
  const raw = String(value).trim()
  if (!raw) return null
  const inputDateTime = raw.replace(/\//g, '-').replace(/\s+/, 'T')
  const normalized =
    /^\d{4}-\d{2}-\d{2}T/.test(inputDateTime) && !hasTimezone(inputDateTime) ? `${inputDateTime}Z` : inputDateTime
  const date = new Date(normalized)
  return Number.isNaN(date.getTime()) ? null : date
}

function parseFilterDate(value) {
  if (!value) return null
  const raw = String(value).trim()
  if (!raw) return null
  const normalized = raw.replace(/\//g, '-').replace(/\s+/, 'T')
  const date = new Date(normalized)
  return Number.isNaN(date.getTime()) ? null : date
}

function normalizeRecordTimestamp(value) {
  return (parseRecordDate(value) || new Date()).toISOString()
}

function formatRecordDate(value) {
  const date = parseRecordDate(value)
  return date ? recordDateFormatter.format(date) : '-'
}

function formatFilterDate(value) {
  if (!value) return '年/月/日 --:--'
  const [datePart, timePart = ''] = value.split('T')
  return `${datePart.replaceAll('-', '/')} ${timePart}`.trim()
}

function openDatePicker(event) {
  event.currentTarget.showPicker?.()
}

function formatFileSize(bytes = 0) {
  if (!bytes) return '0 KB'
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function showUploadOverlay(file, message) {
  uploadOverlay.visible = true
  uploadOverlay.title = file?.size > LARGE_FILE_BYTES ? '文件较大，正在传输请稍等' : '正在检测，请稍等'
  uploadOverlay.message = message
  uploadOverlay.fileName = file?.name || '待检测文件'
  uploadOverlay.fileSize = formatFileSize(file?.size || 0)
  uploadOverlay.sentPercent = 0
}

function updateUploadProgress(event) {
  if (!event?.total) return
  uploadOverlay.sentPercent = Math.min(98, Math.round((event.loaded / event.total) * 100))
}

function hideUploadOverlay() {
  uploadOverlay.sentPercent = 100
  window.setTimeout(() => {
    uploadOverlay.visible = false
  }, 220)
}

function moveUploadGame(event) {
  const rect = event.currentTarget.getBoundingClientRect()
  uploadOverlay.gameX = Math.max(6, Math.min(94, ((event.clientX - rect.left) / rect.width) * 100))
  uploadOverlay.gameY = Math.max(10, Math.min(90, ((event.clientY - rect.top) / rect.height) * 100))
}

function scoreUploadGame() {
  uploadOverlay.score += 1
}

function revokeImagePreview() {
  if (imagePreview.value) {
    URL.revokeObjectURL(imagePreview.value)
    imagePreview.value = ''
  }
}

function imageToBlob(file, maxSide, quality) {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file)
    const image = new Image()
    image.onload = () => {
      const ratio = Math.min(1, maxSide / Math.max(image.naturalWidth || 1, image.naturalHeight || 1))
      const width = Math.max(1, Math.round((image.naturalWidth || 1) * ratio))
      const height = Math.max(1, Math.round((image.naturalHeight || 1) * ratio))
      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      canvas.getContext('2d', { alpha: false }).drawImage(image, 0, 0, width, height)
      canvas.toBlob(
        (blob) => {
          URL.revokeObjectURL(url)
          resolve(blob)
        },
        'image/jpeg',
        quality
      )
    }
    image.onerror = () => {
      URL.revokeObjectURL(url)
      resolve(null)
    }
    image.src = url
  })
}

async function buildPreview(file) {
  const buildId = previewBuildId.value + 1
  previewBuildId.value = buildId
  revokeImagePreview()
  if (!file) return

  const previewBlob = await imageToBlob(file, IMAGE_PREVIEW_MAX_SIDE, IMAGE_PREVIEW_QUALITY)
  if (buildId !== previewBuildId.value) return
  imagePreview.value = URL.createObjectURL(previewBlob || file)
}

async function prepareImageForUpload(file) {
  if (!file || !file.type?.startsWith('image/')) return file
  const optimizedBlob = await imageToBlob(file, IMAGE_UPLOAD_MAX_SIDE, IMAGE_UPLOAD_QUALITY)
  if (!optimizedBlob || optimizedBlob.size >= file.size) return file
  const baseName = file.name.replace(/\.[^.]+$/, '')
  return new File([optimizedBlob], `${baseName}-optimized.jpg`, {
    type: 'image/jpeg',
    lastModified: Date.now()
  })
}

function normalizeRecord(raw) {
  const recognizedAt = normalizeRecordTimestamp(raw.recognized_at)
  return {
    id: raw.id ?? null,
    plate_text: raw.plate_text,
    det_score: Number(raw.det_score ?? 0),
    rec_score: Number(raw.rec_score ?? 0),
    source_type: raw.source_type ?? 'image',
    source_filename: raw.source_filename ?? '',
    plate_image_path: raw.plate_image_path ?? '',
    frame_image_path: raw.frame_image_path ?? '',
    bbox_json: raw.bbox_json ?? '',
    recognized_at: recognizedAt,
    created_at: normalizeRecordTimestamp(raw.created_at ?? recognizedAt)
  }
}

function loadGuestRecords() {
  try {
    const raw = localStorage.getItem(LOCAL_RECORDS_KEY)
    return raw ? JSON.parse(raw).map(normalizeRecord) : []
  } catch {
    return []
  }
}

function saveGuestRecords(items) {
  localStorage.setItem(LOCAL_RECORDS_KEY, JSON.stringify(items))
}

function appendGuestRecords(items) {
  const merged = [...items.map(normalizeRecord), ...loadGuestRecords()]
  saveGuestRecords(merged)
  latestRecords.value = items.map(normalizeRecord)
  refreshGuestRecords()
}

function applyGuestFilters(items) {
  return items.filter((item) => {
    if (filters.plate_text && !item.plate_text.includes(filters.plate_text.trim().toUpperCase())) return false
    if (filters.source_type && item.source_type !== filters.source_type) return false
    const recognizedAt = parseRecordDate(item.recognized_at)
    if (!recognizedAt) return false
    const startTime = parseFilterDate(filters.start_time)
    const endTime = parseFilterDate(filters.end_time)
    if (startTime && recognizedAt < startTime) return false
    if (endTime && recognizedAt > endTime) return false
    return true
  })
}

function refreshGuestRecords(targetPage = page.value) {
  const filtered = applyGuestFilters(loadGuestRecords())
  total.value = filtered.length
  page.value = Math.min(targetPage, Math.max(1, Math.ceil(Math.max(filtered.length, 1) / perPage.value)))
  const start = (page.value - 1) * perPage.value
  records.value = filtered.slice(start, start + perPage.value)
}

function setImageFile(event) {
  const [file] = event.target.files || []
  imageFile.value = file || null
  latestRecords.value = []
  imageMessage.value = ''

  buildPreview(file)
}

function setVideoFile(event) {
  const [file] = event.target.files || []
  videoFile.value = file || null
  videoMessage.value = ''
}

function applyGuestAuthState(message = '') {
  auth.authenticated = false
  auth.username = ''
  auth.storage_mode = 'local'
  auth.checked = true
  authMessage.value = message
}

async function initializeGuestMode() {
  try {
    await logout()
  } catch {
    // Ignore stale-session cleanup failures and continue locally as guest.
  } finally {
    applyGuestAuthState('进入页面默认使用游客模式，登录后才会切换到服务器模式。')
  }
}

async function submitLogin() {
  authMessage.value = ''
  try {
    const state = await login(loginForm)
    auth.authenticated = state.authenticated
    auth.username = state.username || ''
    auth.storage_mode = state.storage_mode
    loginForm.password = ''
    authMessage.value = '登录成功，识别结果将保存到服务器。'
    await fetchRecords(1)
  } catch (error) {
    authMessage.value = error.response?.data?.detail || '登录失败'
  }
}

async function submitLogout() {
  await logout()
  applyGuestAuthState('已切换到游客模式，结果只保存在当前浏览器。')
  currentJob.value = null
  refreshGuestRecords(1)
}

async function recognizeImage(file = imageFile.value, sourceType = 'image') {
  if (!file) {
    imageMessage.value = '请选择图片'
    return
  }

  const shouldShowOverlay = sourceType !== 'camera'
  loading.value = true
  try {
    if (shouldShowOverlay) {
      showUploadOverlay(file, '正在压缩图片并上传到识别服务。你可以移动鼠标接住小车牌，等一下就好。')
    }
    const uploadFile = sourceType === 'camera' ? file : await prepareImageForUpload(file)
    const formData = new FormData()
    formData.append('file', uploadFile)
    formData.append('source_type', sourceType)

    const response = await api.post('/recognitions/image', formData, {
      onUploadProgress: shouldShowOverlay ? updateUploadProgress : undefined
    })
    const resultRecords = (response.data.records || []).map(normalizeRecord)
    latestRecords.value = resultRecords
    imageMessage.value = response.data.message || '识别完成'
    if (response.data.persisted) {
      await fetchRecords()
    } else if (resultRecords.length) {
      appendGuestRecords(resultRecords)
    } else {
      refreshGuestRecords()
    }
  } catch (error) {
    imageMessage.value = error.response?.data?.detail || '识别失败'
  } finally {
    loading.value = false
    if (shouldShowOverlay) hideUploadOverlay()
  }
}

async function uploadVideo() {
  if (!videoFile.value) {
    videoMessage.value = '请选择视频'
    return
  }

  loading.value = true
  try {
    showUploadOverlay(videoFile.value, '视频会先上传，再进入后台逐帧识别。传输完成后可以看进度条。')
    const formData = new FormData()
    formData.append('file', videoFile.value)

    const response = await api.post('/recognitions/video', formData, {
      onUploadProgress: updateUploadProgress
    })
    currentJob.value = {
      job_id: response.data.job_id,
      status: response.data.status,
      progress: 0,
      persisted: response.data.persisted
    }
    videoMessage.value = response.data.persisted ? '视频任务已创建，结果将保存到服务器。' : '游客视频任务已创建，结果完成后保存在当前浏览器。'
    startPollingJob(response.data.job_id, response.data.persisted)
  } catch (error) {
    videoMessage.value = error.response?.data?.detail || '视频上传失败'
  } finally {
    loading.value = false
    hideUploadOverlay()
  }
}

function startPollingJob(jobId, persisted) {
  stopPollingJob()
  pollTimer.value = window.setInterval(async () => {
    try {
      const response = await api.get(`/jobs/${jobId}`)
      currentJob.value = response.data
      if (['completed', 'failed'].includes(response.data.status)) {
        stopPollingJob()
        if (response.data.status === 'completed') {
          videoMessage.value = '视频识别完成'
          if (persisted) {
            await fetchRecords()
          } else if (response.data.records?.length) {
            appendGuestRecords(response.data.records)
          } else {
            refreshGuestRecords()
          }
        } else {
          videoMessage.value = response.data.error_message || '视频识别失败'
        }
      }
    } catch (error) {
      stopPollingJob()
      videoMessage.value = error.response?.data?.detail || '无法获取任务进度'
    }
  }, 1500)
}

function stopPollingJob() {
  if (pollTimer.value) {
    window.clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

async function startCamera() {
  cameraMessage.value = ''
  if (!navigator.mediaDevices?.getUserMedia) {
    cameraMessage.value = '当前浏览器不支持摄像头'
    return
  }

  try {
    streamRef.value = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
    videoRef.value.srcObject = streamRef.value
    await videoRef.value.play()
    cameraRunning.value = true
    cameraMessage.value = isGuestMode.value ? '游客摄像头识别中，结果只保存在当前浏览器。' : '登录模式摄像头识别中，结果会保存到服务器。'
    cameraTimer.value = window.setInterval(captureCameraFrame, 1000)
  } catch {
    cameraMessage.value = '无法打开摄像头，请检查浏览器权限'
  }
}

function stopCamera() {
  if (cameraTimer.value) {
    window.clearInterval(cameraTimer.value)
    cameraTimer.value = null
  }
  if (streamRef.value) {
    streamRef.value.getTracks().forEach((track) => track.stop())
    streamRef.value = null
  }
  if (videoRef.value) videoRef.value.srcObject = null
  cameraRunning.value = false
  cameraMessage.value = '摄像头已停止'
}

async function captureCameraFrame() {
  if (!videoRef.value || !canvasRef.value || !cameraRunning.value || cameraUploading.value) return

  const video = videoRef.value
  const canvas = canvasRef.value
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  const context = canvas.getContext('2d')
  context.drawImage(video, 0, 0, canvas.width, canvas.height)

  canvas.toBlob(async (blob) => {
    if (!blob || !cameraRunning.value) return
    const file = new File([blob], `camera-${Date.now()}.jpg`, { type: 'image/jpeg' })
    cameraUploading.value = true
    await recognizeImage(file, 'camera')
    cameraUploading.value = false
  }, 'image/jpeg', 0.88)
}

async function fetchRecords(targetPage = page.value) {
  page.value = targetPage
  exportMessage.value = ''
  if (isGuestMode.value) {
    refreshGuestRecords(targetPage)
    return
  }
  try {
    const response = await api.get('/recognitions', {
      params: recognitionParams(filters, page.value, perPage.value)
    })
    records.value = response.data.items || []
    total.value = response.data.total || 0
  } catch (error) {
    exportMessage.value = error.response?.data?.detail || '列表加载失败'
  }
}

function resetFilters() {
  filters.plate_text = ''
  filters.source_type = ''
  filters.start_time = ''
  filters.end_time = ''
  fetchRecords(1)
}

function exportGuestCsv() {
  const rows = applyGuestFilters(loadGuestRecords())
  if (!rows.length) {
    exportMessage.value = '当前没有可导出的游客记录'
    return
  }

  const headers = ['识别时间', '车牌号', '检测置信度', 'OCR置信度', '来源', '源文件']
  const lines = [
    headers.join(','),
    ...rows.map((item) =>
      [
        `"${formatRecordDate(item.recognized_at)}"`,
        `"${item.plate_text}"`,
        item.det_score,
        item.rec_score,
        `"${item.source_type}"`,
        `"${item.source_filename || ''}"`
      ].join(',')
    )
  ]
  const blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `guest-recognitions-${Date.now()}.csv`
  link.click()
  URL.revokeObjectURL(url)
  exportMessage.value = '游客记录已导出到当前浏览器'
}

async function exportRecords() {
  exportMessage.value = ''
  if (isGuestMode.value) {
    exportGuestCsv()
    return
  }

  try {
    const response = await api.get('/recognitions/export', {
      params: recognitionParams(filters, 1, perPage.value),
      responseType: 'blob'
    })
    const url = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.download = `plate-recognitions-${Date.now()}.xlsx`
    link.click()
    URL.revokeObjectURL(url)
    exportMessage.value = '服务器记录导出完成'
  } catch (error) {
    exportMessage.value = error.response?.data?.detail || '导出失败'
  }
}

watch(
  () => auth.authenticated,
  async () => {
    latestRecords.value = []
    await fetchRecords(1)
  }
)

onMounted(async () => {
  await initializeGuestMode()
  await fetchRecords(1)
})

onBeforeUnmount(() => {
  stopPollingJob()
  stopCamera()
  revokeImagePreview()
})
</script>

<template>
  <main class="workspace">
    <section class="topbar">
      <div>
        <p class="eyebrow">Car Plate Recognition</p>
        <h1>车牌识别工作台</h1>
        <p class="mode-text">当前模式：{{ modeLabel }}</p>
      </div>
      <div class="auth-panel">
        <template v-if="auth.checked && auth.authenticated">
          <div class="auth-summary">
            <span>已登录：{{ auth.username }}</span>
            <button class="ghost-button" type="button" @click="submitLogout">切换到游客模式</button>
          </div>
        </template>
        <template v-else>
          <div class="login-grid">
            <input v-model="loginForm.username" placeholder="账号" />
            <input v-model="loginForm.password" type="password" placeholder="密码" />
            <button type="button" @click="submitLogin">登录</button>
          </div>
        </template>
        <p class="status-text">{{ authMessage || (isGuestMode ? '游客模式下数据只保存在当前浏览器。' : '登录模式下结果将保存到服务器。') }}</p>
      </div>
    </section>

    <section class="capture-grid">
      <div class="tool-panel">
        <h2>图片识别</h2>
        <input type="file" accept="image/*" @change="setImageFile" />
        <img v-if="imagePreview" class="preview-image" :src="imagePreview" alt="待识别图片预览" />
        <button type="button" :disabled="loading || !imageFile" @click="recognizeImage()">开始识别</button>
        <p class="status-text">{{ imageMessage }}</p>
      </div>

      <div class="tool-panel">
        <h2>视频识别</h2>
        <input type="file" accept="video/*" @change="setVideoFile" />
        <button type="button" :disabled="loading || !videoFile" @click="uploadVideo">上传视频</button>
        <div v-if="currentJob" class="progress-row">
          <span>{{ currentJob.status }}</span>
          <progress :value="currentJob.progress" max="100"></progress>
          <span>{{ Number(currentJob.progress || 0).toFixed(1) }}%</span>
        </div>
        <p class="status-text">{{ videoMessage }}</p>
      </div>

      <div class="tool-panel camera-panel">
        <h2>摄像头识别</h2>
        <video ref="videoRef" class="camera-view" muted playsinline></video>
        <canvas ref="canvasRef" hidden></canvas>
        <div class="button-row">
          <button type="button" :disabled="cameraRunning" @click="startCamera">开始</button>
          <button class="danger-button" type="button" :disabled="!cameraRunning" @click="stopCamera">停止</button>
        </div>
        <p class="status-text">{{ cameraMessage }}</p>
      </div>
    </section>

    <section class="latest-section" v-if="latestRecords.length">
      <h2>最新识别</h2>
      <div class="latest-grid">
        <article v-for="(record, index) in latestRecords" :key="record.id || `${record.plate_text}-${index}`" class="result-card">
          <img v-if="record.frame_image_path" :src="mediaUrl(record.frame_image_path)" alt="识别标注图" />
          <div>
            <strong>{{ record.plate_text }}</strong>
            <span>检测 {{ Number(record.det_score).toFixed(2) }}</span>
            <span>OCR {{ Number(record.rec_score).toFixed(2) }}</span>
            <span>{{ isGuestMode ? '游客本地记录' : '服务器记录' }}</span>
          </div>
        </article>
      </div>
    </section>

    <section class="records-section">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Records</p>
          <h2>{{ isGuestMode ? '游客本地记录' : '服务器识别记录' }}</h2>
        </div>
        <button type="button" @click="exportRecords">{{ isGuestMode ? '导出本地 CSV' : '导出服务器 Excel' }}</button>
      </div>

      <form class="filters" @submit.prevent="fetchRecords(1)">
        <input v-model="filters.plate_text" placeholder="车牌号" />
        <select v-model="filters.source_type">
          <option value="">全部来源</option>
          <option value="image">图片</option>
          <option value="video">视频</option>
          <option value="camera">摄像头</option>
        </select>
        <label class="date-filter-field" :class="{ 'is-empty': !filters.start_time }" data-placeholder="开始时间（可选）">
          <span>开始时间</span>
          <strong>{{ filters.start_time ? formatFilterDate(filters.start_time) : '年/月/日 --:--' }}</strong>
          <input
            v-model="filters.start_time"
            type="datetime-local"
            aria-label="开始时间"
            @focus="openDatePicker"
            @click="openDatePicker"
          />
        </label>
        <label class="date-filter-field" :class="{ 'is-empty': !filters.end_time }" data-placeholder="结束时间（可选）">
          <span>结束时间</span>
          <strong>{{ filters.end_time ? formatFilterDate(filters.end_time) : '年/月/日 --:--' }}</strong>
          <input
            v-model="filters.end_time"
            type="datetime-local"
            aria-label="结束时间"
            @focus="openDatePicker"
            @click="openDatePicker"
          />
        </label>
        <button type="submit">筛选</button>
        <button class="ghost-button" type="button" @click="resetFilters">重置</button>
      </form>
      <p class="status-text">{{ exportMessage }}</p>

      <div class="records-table">
        <table>
          <thead>
            <tr>
              <th>车牌号</th>
              <th>来源</th>
              <th>检测</th>
              <th>OCR</th>
              <th>识别时间</th>
              <th>截图</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(record, index) in records" :key="record.id || `${record.plate_text}-${index}`">
              <td>{{ record.plate_text }}</td>
              <td>{{ record.source_type }}</td>
              <td>{{ Number(record.det_score).toFixed(2) }}</td>
              <td>{{ Number(record.rec_score).toFixed(2) }}</td>
              <td>{{ formatRecordDate(record.recognized_at) }}</td>
              <td>
                <a v-if="record.frame_image_path" :href="mediaUrl(record.frame_image_path)" target="_blank">查看</a>
                <span v-else>{{ isGuestMode ? '仅本地保存元数据' : '无' }}</span>
              </td>
            </tr>
            <tr v-if="!records.length">
              <td colspan="6">暂无记录</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="pagination">
        <button type="button" :disabled="page <= 1" @click="fetchRecords(page - 1)">上一页</button>
        <span>{{ page }} / {{ totalPages }}</span>
        <button type="button" :disabled="page >= totalPages" @click="fetchRecords(page + 1)">下一页</button>
      </div>
    </section>
    <div v-if="uploadOverlay.visible" class="upload-wait-mask" role="status" aria-live="polite">
      <section class="upload-wait-card">
        <div>
          <p class="eyebrow">Transfer</p>
          <h2>{{ uploadOverlay.title }}</h2>
          <p>{{ uploadOverlay.message }}</p>
          <p class="upload-file-line">{{ uploadOverlay.fileName }} · {{ uploadOverlay.fileSize }}</p>
        </div>
        <div class="upload-progress">
          <span>{{ uploadOverlay.sentPercent }}%</span>
          <progress :value="uploadOverlay.sentPercent" max="100"></progress>
        </div>
        <div class="wait-game" @pointermove="moveUploadGame" @pointerdown="scoreUploadGame">
          <span class="game-road"></span>
          <button
            class="game-plate"
            type="button"
            :style="{ left: `${uploadOverlay.gameX}%`, top: `${uploadOverlay.gameY}%` }"
            @click="scoreUploadGame"
          >
            临A·{{ String(uploadOverlay.score).padStart(3, '0') }}
          </button>
          <p>移动鼠标追车牌，点一下加分：{{ uploadOverlay.score }}</p>
        </div>
      </section>
    </div>
  </main>
</template>
