// API Service Layer for Backend Communication

import type {
  IngestResponse,
  Task,
  CreateTaskRequest,
  UpdateTaskRequest,
  Profile,
  ProfileUpdate,
  VoicesResponse,
} from '@/types/api';
import { auth } from '@/config/firebase';

const API_BASE_URL = 'http://localhost:8000/api';

// Helper to get auth token
async function getAuthToken(): Promise<string | null> {
  const user = auth.currentUser;
  if (!user) {
    return null;
  }
  return await user.getIdToken();
}

// Voice API
export const voiceAPI = {
  async ingestAudio(audioBlob: Blob, voiceId?: string): Promise<IngestResponse> {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'audio.webm');
    if (voiceId) {
      formData.append('voice_id', voiceId);
    }

    // Get auth token
    const token = await getAuthToken();
    const headers: HeadersInit = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}/voice/ingest`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Voice API error: ${response.statusText}`);
    }

    return response.json();
  },
};

// Tasks API
export const tasksAPI = {
  async listTasks(status?: string): Promise<Task[]> {
    const url = new URL(`${API_BASE_URL}/tasks`);
    if (status) {
      url.searchParams.append('status', status);
    }

    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`Tasks API error: ${response.statusText}`);
    }

    return response.json();
  },

  async getTask(taskId: string): Promise<Task> {
    const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`);
    if (!response.ok) {
      throw new Error(`Tasks API error: ${response.statusText}`);
    }

    return response.json();
  },

  async createTask(request: CreateTaskRequest): Promise<Task> {
    const response = await fetch(`${API_BASE_URL}/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Tasks API error: ${response.statusText}`);
    }

    return response.json();
  },

  async updateTask(taskId: string, updates: UpdateTaskRequest): Promise<Task> {
    const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });

    if (!response.ok) {
      throw new Error(`Tasks API error: ${response.statusText}`);
    }

    return response.json();
  },

  async deleteTask(taskId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`Tasks API error: ${response.statusText}`);
    }
  },
};

// Profile API
export const profileAPI = {
  async getProfile(userId: string = 'default'): Promise<Profile> {
    const url = new URL(`${API_BASE_URL}/profile`);
    url.searchParams.append('user_id', userId);

    const response = await fetch(url.toString());
    if (!response.ok) {
      throw new Error(`Profile API error: ${response.statusText}`);
    }

    return response.json();
  },

  async updateProfile(updates: ProfileUpdate, userId: string = 'default'): Promise<Profile> {
    const url = new URL(`${API_BASE_URL}/profile`);
    url.searchParams.append('user_id', userId);

    const response = await fetch(url.toString(), {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });

    if (!response.ok) {
      throw new Error(`Profile API error: ${response.statusText}`);
    }

    return response.json();
  },

  async getVoices(): Promise<VoicesResponse> {
    const response = await fetch(`${API_BASE_URL}/profile/voices`);
    if (!response.ok) {
      throw new Error(`Voice list API error: ${response.statusText}`);
    }

    return response.json();
  },
};
