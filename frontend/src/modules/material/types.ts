export interface Material {
  id: number
  user_id: number
  product_id: number | null
  material_type: 'image' | 'video' | 'text'
  input_type: string
  image_url: string | null
  video_url: string | null
  text_content: string | null
  tags: string[]
  source: string | null
  category: string | null
  created_at: string
  updated_at: string
}
