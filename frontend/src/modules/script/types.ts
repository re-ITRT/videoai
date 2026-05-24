export interface Script {
  id: number; user_id: number; product_id: number | null; mode: string; strategy: string | null;
  factors: Record<string, any> | null; video_style: string | null; total_duration: number | null;
  scenes: any[] | null; reference_video_id: number | null; template_id: number | null;
  created_at: string; updated_at: string;
}
