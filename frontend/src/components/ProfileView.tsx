import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Save } from 'lucide-react';
import { profileAPI } from '@/services/api';
import type { Profile, ProfileUpdate, Voice } from '@/types/api';

interface ProfileViewProps {
  onBack: () => void;
}

export function ProfileView({ onBack }: ProfileViewProps) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [voices, setVoices] = useState<Voice[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState<ProfileUpdate>({});

  useEffect(() => {
    loadProfile();
    loadVoices();
  }, []);

  const loadProfile = async () => {
    try {
      setLoading(true);
      const data = await profileAPI.getProfile();
      setProfile(data);
      setFormData({
        name: data.name || '',
        email: data.email || '',
        location: data.location || '',
        dietary_preference: data.dietary_preference || '',
        learning_level: data.learning_level || '',
        preferred_voice: data.preferred_voice || '',
        interests: data.interests || [],
        timezone: data.timezone || '',
      });
    } catch (err) {
      console.error('Failed to load profile:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadVoices = async () => {
    try {
      const data = await profileAPI.getVoices();
      setVoices(data.voices);
    } catch (err) {
      console.error('Failed to load voices:', err);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      await profileAPI.updateProfile(formData);
      await loadProfile();
    } catch (err) {
      console.error('Failed to save profile:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleInterestChange = (interest: string) => {
    setFormData((prev) => {
      const currentInterests = prev.interests || [];
      if (currentInterests.includes(interest)) {
        return { ...prev, interests: currentInterests.filter((i) => i !== interest) };
      } else {
        return { ...prev, interests: [...currentInterests, interest] };
      }
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-muted-foreground">Loading profile...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="p-2 rounded-lg hover:bg-muted/30 transition-colors"
            >
              <ArrowLeft size={20} className="text-foreground" />
            </button>
            <h1 className="text-2xl font-medium tracking-wide text-foreground">
              Profile
            </h1>
          </div>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            <Save size={16} />
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>

        {/* Profile Form */}
        <div className="space-y-6">
          {/* Personal Information */}
          <div className="glass-panel rounded-lg p-6">
            <h2 className="text-lg font-medium text-foreground mb-4">
              Personal Information
            </h2>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-muted-foreground block mb-2">Name</label>
                <input
                  type="text"
                  value={formData.name || ''}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Your name"
                  className="w-full px-4 py-2 rounded-lg bg-muted/30 border border-border/50 outline-none focus:border-primary transition-colors text-foreground"
                />
              </div>
              <div>
                <label className="text-sm text-muted-foreground block mb-2">Email</label>
                <input
                  type="email"
                  value={formData.email || ''}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="your.email@example.com"
                  className="w-full px-4 py-2 rounded-lg bg-muted/30 border border-border/50 outline-none focus:border-primary transition-colors text-foreground"
                />
              </div>
              <div>
                <label className="text-sm text-muted-foreground block mb-2">Location</label>
                <input
                  type="text"
                  value={formData.location || ''}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  placeholder="City, Country"
                  className="w-full px-4 py-2 rounded-lg bg-muted/30 border border-border/50 outline-none focus:border-primary transition-colors text-foreground"
                />
              </div>
              <div>
                <label className="text-sm text-muted-foreground block mb-2">Timezone</label>
                <input
                  type="text"
                  value={formData.timezone || ''}
                  onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
                  placeholder="e.g., America/New_York"
                  className="w-full px-4 py-2 rounded-lg bg-muted/30 border border-border/50 outline-none focus:border-primary transition-colors text-foreground"
                />
              </div>
            </div>
          </div>

          {/* Preferences */}
          <div className="glass-panel rounded-lg p-6">
            <h2 className="text-lg font-medium text-foreground mb-4">
              Preferences
            </h2>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-muted-foreground block mb-2">Voice</label>
                <select
                  value={formData.preferred_voice || ''}
                  onChange={(e) => setFormData({ ...formData, preferred_voice: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg bg-muted/30 border border-border/50 outline-none focus:border-primary transition-colors text-foreground"
                >
                  <option value="">Select a voice</option>
                  {voices.map((voice) => (
                    <option key={voice.id} value={voice.id}>
                      {voice.name} - {voice.description}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm text-muted-foreground block mb-2">Dietary Preference</label>
                <input
                  type="text"
                  value={formData.dietary_preference || ''}
                  onChange={(e) => setFormData({ ...formData, dietary_preference: e.target.value })}
                  placeholder="e.g., Vegetarian, Vegan, None"
                  className="w-full px-4 py-2 rounded-lg bg-muted/30 border border-border/50 outline-none focus:border-primary transition-colors text-foreground"
                />
              </div>
              <div>
                <label className="text-sm text-muted-foreground block mb-2">Learning Level</label>
                <select
                  value={formData.learning_level || ''}
                  onChange={(e) => setFormData({ ...formData, learning_level: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg bg-muted/30 border border-border/50 outline-none focus:border-primary transition-colors text-foreground"
                >
                  <option value="">Select level</option>
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                  <option value="expert">Expert</option>
                </select>
              </div>
            </div>
          </div>

          {/* Interests */}
          <div className="glass-panel rounded-lg p-6">
            <h2 className="text-lg font-medium text-foreground mb-4">
              Interests
            </h2>
            <div className="space-y-3">
              {['Technology', 'Science', 'Sports', 'Music', 'Art', 'Travel', 'Cooking', 'Reading'].map((interest) => (
                <label key={interest} className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={(formData.interests || []).includes(interest)}
                    onChange={() => handleInterestChange(interest)}
                    className="w-5 h-5 rounded border-2 border-muted-foreground checked:bg-primary checked:border-primary"
                  />
                  <span className="text-sm text-foreground">{interest}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
