import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Plus, Trash2, Check } from 'lucide-react';
import { tasksAPI } from '@/services/api';
import type { Task, CreateTaskRequest } from '@/types/api';

interface TasksViewProps {
  onBack: () => void;
}

export function TasksView({ onBack }: TasksViewProps) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [filter, setFilter] = useState<string>('');

  useEffect(() => {
    loadTasks();
  }, [filter]);

  const loadTasks = async () => {
    try {
      setLoading(true);
      const data = await tasksAPI.listTasks(filter || undefined);
      setTasks(data);
    } catch (err) {
      console.error('Failed to load tasks:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTask = async () => {
    if (!newTaskTitle.trim()) return;

    try {
      const request: CreateTaskRequest = {
        title: newTaskTitle.trim(),
        status: 'pending',
      };
      await tasksAPI.createTask(request);
      setNewTaskTitle('');
      await loadTasks();
    } catch (err) {
      console.error('Failed to create task:', err);
    }
  };

  const handleToggleStatus = async (task: Task) => {
    try {
      const newStatus = task.status === 'completed' ? 'pending' : 'completed';
      await tasksAPI.updateTask(task.id, { status: newStatus });
      await loadTasks();
    } catch (err) {
      console.error('Failed to update task:', err);
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    try {
      await tasksAPI.deleteTask(taskId);
      await loadTasks();
    } catch (err) {
      console.error('Failed to delete task:', err);
    }
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <button
            onClick={onBack}
            className="p-2 rounded-lg hover:bg-muted/30 transition-colors"
          >
            <ArrowLeft size={20} className="text-foreground" />
          </button>
          <h1 className="text-2xl font-medium tracking-wide text-foreground">
            Tasks
          </h1>
        </div>

        {/* Filter */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setFilter('')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${filter === '' ? 'bg-primary text-primary-foreground' : 'glass-panel text-foreground'
              }`}
          >
            All
          </button>
          <button
            onClick={() => setFilter('pending')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${filter === 'pending' ? 'bg-primary text-primary-foreground' : 'glass-panel text-foreground'
              }`}
          >
            Pending
          </button>
          <button
            onClick={() => setFilter('completed')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${filter === 'completed' ? 'bg-primary text-primary-foreground' : 'glass-panel text-foreground'
              }`}
          >
            Completed
          </button>
        </div>

        {/* New Task Input */}
        <div className="glass-panel rounded-lg p-4 mb-6">
          <div className="flex gap-3">
            <input
              type="text"
              value={newTaskTitle}
              onChange={(e) => setNewTaskTitle(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreateTask()}
              placeholder="Add a new task..."
              className="flex-1 bg-transparent border-none outline-none text-foreground placeholder:text-muted-foreground"
            />
            <button
              onClick={handleCreateTask}
              disabled={!newTaskTitle.trim()}
              className="p-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Plus size={20} />
            </button>
          </div>
        </div>

        {/* Tasks List */}
        <div className="space-y-3">
          {loading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading tasks...
            </div>
          ) : tasks.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No tasks found. Create one above!
            </div>
          ) : (
            tasks.map((task) => (
              <motion.div
                key={task.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="glass-panel rounded-lg p-4 hover:border-primary/40 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => handleToggleStatus(task)}
                    className={`flex-shrink-0 w-6 h-6 rounded border-2 flex items-center justify-center transition-colors ${task.status === 'completed'
                        ? 'bg-primary border-primary'
                        : 'border-muted-foreground'
                      }`}
                  >
                    {task.status === 'completed' && <Check size={14} className="text-primary-foreground" />}
                  </button>

                  <div className="flex-1 min-w-0">
                    <p
                      className={`text-sm font-medium ${task.status === 'completed'
                          ? 'text-muted-foreground line-through'
                          : 'text-foreground'
                        }`}
                    >
                      {task.title}
                    </p>
                    {task.due_date && (
                      <p className="text-xs text-muted-foreground mt-1">
                        Due: {new Date(task.due_date).toLocaleDateString()}
                      </p>
                    )}
                  </div>

                  {task.priority && (
                    <span
                      className={`text-xs px-2 py-1 rounded ${task.priority === 'high'
                          ? 'bg-destructive/20 text-destructive'
                          : task.priority === 'medium'
                            ? 'bg-accent/20 text-accent'
                            : 'bg-muted/30 text-muted-foreground'
                        }`}
                    >
                      {task.priority}
                    </span>
                  )}

                  <button
                    onClick={() => handleDeleteTask(task.id)}
                    className="p-2 rounded-lg hover:bg-destructive/20 hover:text-destructive transition-colors"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </motion.div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
