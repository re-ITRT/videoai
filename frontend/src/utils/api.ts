import request from './request'

// Auth
export const login = (data: { username: string; password: string }) =>
  request.post('/auth/login', data)
export const register = (data: { username: string; password: string }) =>
  request.post('/auth/register', data)
export const getMe = () => request.get('/auth/me')

// Products
export const getProducts = () => request.get('/products')
export const createProduct = (data: any) => request.post('/products', data)
export const updateProduct = (id: number, data: any) => request.put(`/products/${id}`, data)
export const deleteProduct = (id: number) => request.delete(`/products/${id}`)

// Materials
export const getMaterials = (params?: any) => request.get('/materials', { params })
export const uploadMaterial = (data: FormData) =>
  request.post('/materials/upload', data, { headers: { 'Content-Type': 'multipart/form-data' } })
export const deleteMaterial = (id: number) => request.delete(`/materials/${id}`)
export const searchMaterials = (params: any) => request.get('/materials/search', { params })

// Scripts
export const getScripts = (params?: any) => request.get('/scripts', { params })
export const generateScript = (data: any) => request.post('/scripts/generate', data)
export const getScript = (id: number) => request.get(`/scripts/${id}`)
export const updateScript = (id: number, data: any) => request.put(`/scripts/${id}`, data)
export const deleteScript = (id: number) => request.delete(`/scripts/${id}`)

// Video Tasks
export const getTasks = (params?: any) => request.get('/video-tasks', { params })
export const createTask = (data: any) => request.post('/video-tasks', data)
export const getTask = (id: number) => request.get(`/video-tasks/${id}`)
export const retryTask = (id: number) => request.post(`/video-tasks/${id}/retry`)
export const exportVideo = (id: number) => request.get(`/video-tasks/${id}/export`)
