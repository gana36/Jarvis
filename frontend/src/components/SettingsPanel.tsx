import { motion, AnimatePresence } from 'framer-motion';
import { X, ListTodo, User, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (view: 'tasks' | 'profile') => void;
}

export function SettingsPanel({ isOpen, onClose, onNavigate }: SettingsPanelProps) {
  const navigate = useNavigate();
  const { logout } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
      onClose();
      navigate('/login');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  const menuItems = [
    {
      id: 'tasks' as const,
      icon: ListTodo,
      label: 'Tasks',
      description: 'Manage your tasks and to-dos',
    },
    {
      id: 'profile' as const,
      icon: User,
      label: 'Profile',
      description: 'Update your preferences and settings',
    },
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40"
          />

          {/* Panel */}
          <motion.div
            initial={{ x: 300, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 300, opacity: 0 }}
            transition={{
              type: 'spring',
              stiffness: 300,
              damping: 30,
            }}
            className="fixed right-0 top-0 bottom-0 w-80 glass-panel border-l border-border/50 z-50 p-6 flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
              <h2 className="text-xl font-medium tracking-wide text-foreground">
                Settings
              </h2>
              <button
                onClick={onClose}
                className="p-2 rounded-lg hover:bg-muted/30 transition-colors"
              >
                <X size={20} className="text-foreground" />
              </button>
            </div>

            {/* Menu Items */}
            <div className="space-y-3 flex-1">
              {menuItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => {
                    onNavigate(item.id);
                    onClose();
                  }}
                  className="w-full glass-panel rounded-lg p-4 hover:border-primary/40 transition-all text-left group"
                >
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded-md bg-primary/10 group-hover:bg-primary/20 transition-colors">
                      <item.icon size={20} className="text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground mb-1">
                        {item.label}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {item.description}
                      </p>
                    </div>
                  </div>
                </button>
              ))}
            </div>

            {/* Logout Button */}
            <div className="pt-4 border-t border-border/30">
              <button
                onClick={handleLogout}
                className="w-full glass-panel rounded-lg p-4 hover:border-red-500/40 transition-all text-left group"
              >
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-md bg-red-500/10 group-hover:bg-red-500/20 transition-colors">
                    <LogOut size={20} className="text-red-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground mb-1">
                      Logout
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Sign out of your account
                    </p>
                  </div>
                </div>
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
