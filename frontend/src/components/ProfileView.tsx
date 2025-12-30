import { useState, useEffect } from 'react';
import { ArrowLeft, Save, Calendar, ExternalLink, CheckCircle, Mail, Activity } from 'lucide-react';
import { profileAPI, calendarAPI, API_BASE_URL } from '@/services/api';

// Get base URL without /api suffix for auth endpoints
const AUTH_BASE_URL = API_BASE_URL.replace('/api', '');
import { useAuth } from '@/contexts/AuthContext';
import type { Profile, ProfileUpdate, Voice } from '@/types/api';

interface ProfileViewProps {
  onBack: () => void;
}

export function ProfileView({ onBack }: ProfileViewProps) {
  const { currentUser } = useAuth();
  const [, setProfile] = useState<Profile | null>(null);
  const [voices, setVoices] = useState<Voice[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState<ProfileUpdate>({});
  const [calendarStatus, setCalendarStatus] = useState<{ authorized: boolean; calendar_connected: boolean } | null>(null);
  const [gmailStatus, setGmailStatus] = useState<{ authorized: boolean; gmail_connected: boolean } | null>(null);
  const [fitbitStatus, setFitbitStatus] = useState<{ authorized: boolean; fitbit_connected: boolean } | null>(null);

  useEffect(() => {
    loadProfile();
    loadVoices();
    loadCalendarStatus();
    loadGmailStatus();
    loadFitbitStatus();
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

  const loadCalendarStatus = async () => {
    try {
      const status = await calendarAPI.checkStatus();
      setCalendarStatus(status);
    } catch (err) {
      console.error('Failed to load calendar status:', err);
    }
  };

  const loadGmailStatus = async () => {
    try {
      const userId = currentUser?.uid || 'default';
      const response = await fetch(`${AUTH_BASE_URL}/auth/gmail/status?user_id=${userId}`);
      if (response.ok) {
        const status = await response.json();
        setGmailStatus(status);
      }
    } catch (err) {
      console.error('Failed to load Gmail status:', err);
    }
  };

  const loadFitbitStatus = async () => {
    try {
      const response = await fetch(`${AUTH_BASE_URL}/auth/fitbit/status`);
      if (response.ok) {
        const status = await response.json();
        setFitbitStatus(status);
      }
    } catch (err) {
      console.error('Failed to load Fitbit status:', err);
    }
  };

  const handleConnectCalendar = async () => {
    try {
      const url = await calendarAPI.getConnectUrl();
      window.open(url, '_blank', 'width=600,height=700');

      // Poll for status update or just tell user to refresh
      const interval = setInterval(async () => {
        const status = await calendarAPI.checkStatus();
        if (status.calendar_connected) {
          setCalendarStatus(status);
          clearInterval(interval);
        }
      }, 3000);

      // Stop polling after 2 minutes
      setTimeout(() => clearInterval(interval), 120000);
    } catch (err) {
      console.error('Failed to get calendar connect URL:', err);
    }
  };

  const handleConnectGmail = () => {
    // Open Gmail OAuth in popup
    const userId = currentUser?.uid || 'default';
    const url = `${AUTH_BASE_URL}/auth/google/gmail?user_id=${userId}`;
    window.open(url, '_blank', 'width=600,height=700');

    // Poll for status update
    const interval = setInterval(async () => {
      try {
        const uid = currentUser?.uid || 'default';
        const response = await fetch(`${AUTH_BASE_URL}/auth/gmail/status?user_id=${uid}`);
        if (response.ok) {
          const status = await response.json();
          setGmailStatus(status);
          if (status.gmail_connected) {
            clearInterval(interval);
          }
        }
      } catch (err) {
        console.error('Gmail polling error:', err);
      }
    }, 3000);

    // Stop polling after 2 minutes
    setTimeout(() => clearInterval(interval), 120000);
  };

  const handleConnectFitbit = () => {
    // Open Fitbit OAuth in popup
    const url = `${AUTH_BASE_URL}/auth/fitbit`;
    window.open(url, '_blank', 'width=600,height=700');

    // Poll for status update
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${AUTH_BASE_URL}/auth/fitbit/status`);
        if (response.ok) {
          const status = await response.json();
          setFitbitStatus(status);
          if (status.fitbit_connected) {
            clearInterval(interval);
          }
        }
      } catch (err) {
        console.error('Fitbit polling error:', err);
      }
    }, 3000);

    // Stop polling after 2 minutes
    setTimeout(() => clearInterval(interval), 120000);
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

          {/* Calendar Integration */}
          <div className="glass-panel rounded-lg p-6 mb-12">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-medium text-foreground">
                Calendar Integration
              </h2>
              {calendarStatus?.calendar_connected ? (
                <div className="flex items-center gap-2 text-green-400 text-sm">
                  <CheckCircle size={16} />
                  Connected
                </div>
              ) : (
                <div className="text-amber-400 text-sm">Not Connected</div>
              )}
            </div>

            <p className="text-sm text-muted-foreground mb-6">
              Connect your Google Calendar so Manas can manage your schedule and provide daily summaries.
            </p>

            <button
              onClick={handleConnectCalendar}
              className={`flex items-center justify-center gap-3 w-full py-3 rounded-lg border transition-all ${calendarStatus?.calendar_connected
                ? 'bg-muted/20 border-border/50 text-foreground hover:bg-muted/30'
                : 'bg-primary/10 border-primary/30 text-primary hover:bg-primary/20'
                }`}
            >
              <Calendar size={20} />
              {calendarStatus?.calendar_connected ? 'Reconnect Google Calendar' : 'Connect Google Calendar'}
              <ExternalLink size={16} className="opacity-50" />
            </button>
          </div>

          {/* Gmail Integration */}
          <div className="glass-panel rounded-lg p-6 mb-12">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-medium text-foreground">
                Gmail Integration
              </h2>
              {gmailStatus?.gmail_connected ? (
                <div className="flex items-center gap-2 text-green-400 text-sm">
                  <CheckCircle size={16} />
                  Connected
                </div>
              ) : (
                <div className="text-amber-400 text-sm">Not Connected</div>
              )}
            </div>

            <p className="text-sm text-muted-foreground mb-6">
              Connect your Gmail so Manas can check your emails and provide summaries.
            </p>

            <button
              onClick={handleConnectGmail}
              className={`flex items-center justify-center gap-3 w-full py-3 rounded-lg border transition-all ${gmailStatus?.gmail_connected
                ? 'bg-muted/20 border-border/50 text-foreground hover:bg-muted/30'
                : 'bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20'
                }`}
            >
              <Mail size={20} />
              {gmailStatus?.gmail_connected ? 'Reconnect Gmail' : 'Connect Gmail'}
              <ExternalLink size={16} className="opacity-50" />
            </button>
          </div>

          {/* Fitbit Integration */}
          <div className="glass-panel rounded-lg p-6 mb-12">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-medium text-foreground">
                Fitbit Integration
              </h2>
              {fitbitStatus?.fitbit_connected ? (
                <div className="flex items-center gap-2 text-green-400 text-sm">
                  <CheckCircle size={16} />
                  Connected
                </div>
              ) : (
                <div className="text-amber-400 text-sm">Not Connected (using demo data)</div>
              )}
            </div>

            <p className="text-sm text-muted-foreground mb-6">
              Connect your Fitbit to get real health data in your daily summaries. Without it, Manas uses demo data.
            </p>

            <button
              onClick={handleConnectFitbit}
              className={`flex items-center justify-center gap-3 w-full py-3 rounded-lg border transition-all ${fitbitStatus?.fitbit_connected
                ? 'bg-muted/20 border-border/50 text-foreground hover:bg-muted/30'
                : 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/20'
                }`}
            >
              <Activity size={20} />
              {fitbitStatus?.fitbit_connected ? 'Reconnect Fitbit' : 'Connect Fitbit'}
              <ExternalLink size={16} className="opacity-50" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
