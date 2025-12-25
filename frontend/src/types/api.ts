// API Request and Response Types

// Voice API Types
export interface IngestResponse {
  success: boolean;
  message: string;
  audio_size_bytes: number;
  transcript: string;
  ai_response: string;
  audio_base64?: string;
  intent?: string;
  confidence?: number;
  data?: any;
}

// Task API Types
export interface Task {
  id: string;
  title: string;
  status: string;
  priority?: string;
  due_date?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateTaskRequest {
  title: string;
  status?: string;
  priority?: string;
  due_date?: string;
}

export interface UpdateTaskRequest {
  title?: string;
  status?: string;
  priority?: string;
  due_date?: string;
}

// Profile API Types
export interface Profile {
  user_id: string;
  name?: string;
  email?: string;
  timezone: string;
  location?: string;
  dietary_preference?: string;
  learning_level?: string;
  preferred_voice?: string;
  interests: string[];
  created_at: string;
  updated_at: string;
}

export interface ProfileUpdate {
  name?: string;
  email?: string;
  location?: string;
  dietary_preference?: string;
  learning_level?: string;
  preferred_voice?: string;
  interests?: string[];
  timezone?: string;
}

export interface Voice {
  id: string;
  name: string;
  description: string;
}

export interface VoicesResponse {
  voices: Voice[];
  default: string;
}
