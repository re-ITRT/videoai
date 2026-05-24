export interface VideoTask {
  id: number; script_id: number; user_id: number; state: string; current_step: number; total_steps: number;
  aspect_ratio: string; auto_mode: boolean; video_url: string | null; duration: number | null;
  error_message: string | null; retry_count: number; created_at: string; updated_at: string;
}
