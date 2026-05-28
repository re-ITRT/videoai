import request from './request'

// ==============================
// Auth
// ==============================
export const login = (data: { username: string; password: string }) =>
  request.post('/auth/login', data)
export const register = (data: { username: string; password: string; nickname?: string }) =>
  request.post('/auth/register', data)
export const getMe = () => request.get('/auth/me')
export const logout = () => request.post('/auth/logout')
export const refreshToken = (refreshToken: string) =>
  request.post('/auth/refresh', { refresh_token: refreshToken })

// ==============================
// Users
// ==============================
export const getMyProfile = () => request.get('/users/me')
export const updateMyProfile = (data: { nickname?: string; email?: string }) =>
  request.put('/users/me', data)
export const changeMyPassword = (data: { old_password: string; new_password: string }) =>
  request.put('/users/me/password', data)

// Admin user management
export const getUsers = (params?: { skip?: number; limit?: number }) =>
  request.get('/users', { params })
export const adminUpdateUser = (id: number, data: any) =>
  request.patch(`/users/${id}`, data)
export const adminDeleteUser = (id: number) =>
  request.delete(`/users/${id}`)

// ==============================
// Products
// ==============================
export const getProducts = () => request.get('/products')
export const createProduct = (data: any) => request.post('/products', data)
export const updateProduct = (id: number, data: any) => request.put(`/products/${id}`, data)
export const deleteProduct = (id: number) => request.delete(`/products/${id}`)

// ==============================
// Materials
// ==============================
export const getMaterials = (params?: any) => request.get('/materials', { params })
export const uploadMaterial = (data: any) =>
  request.post('/materials/upload', data)
export const deleteMaterial = (id: number) => request.delete(`/materials/${id}`)
export const searchMaterials = (params: any) => request.get('/materials/search', { params })

// ==============================
// Scripts
// ==============================
export const getScripts = (params?: any) => request.get('/scripts', { params })
export const generateScript = (data: any) => request.post('/scripts/generate', data)
export const getScript = (id: number) => request.get(`/scripts/${id}`)
export const updateScript = (id: number, data: any) => request.put(`/scripts/${id}`, data)
export const deleteScript = (id: number) => request.delete(`/scripts/${id}`)

// ==============================
// Tasks / Creation
// ==============================
export const getTasks = (params?: any) => request.get('/tasks', { params })
export const createTask = (data: any) => request.post('/tasks', data)
export const getTask = (id: number) => request.get(`/tasks/${id}`)
export const retryTask = (id: number) => request.post(`/tasks/${id}/retry`)
export const exportVideo = (id: number) => request.get(`/tasks/${id}/export`)
export const getTaskLogs = (id: number) => request.get(`/tasks/${id}/logs`)
export const approveScript = (id: number) => request.post(`/tasks/${id}/approve-script`)
export const regenerateScene = (taskId: number, sceneId: number) =>
  request.post(`/tasks/${taskId}/regenerate-scene/${sceneId}`)
