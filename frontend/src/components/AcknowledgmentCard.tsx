import { forwardRef } from 'react';
import { motion } from 'framer-motion';
import { Calendar, CheckCircle, Cloud, Lightbulb, MessageSquare, X, Wind, Droplets, ExternalLink, Clock, AlertTriangle, Newspaper, MapPin, AlignLeft } from 'lucide-react';

export type CardType = 'calendar' | 'task' | 'weather' | 'memory' | 'info' | 'news';

interface AcknowledgmentCardProps {
  type: CardType;
  title: string;
  subtitle?: string;
  data?: any;
  onDismiss?: () => void;
  index?: number;
  isCitation?: boolean;
}

const cardConfig = {
  calendar: {
    icon: Calendar,
    accentColor: 'hsl(185, 85%, 50%)',
    label: 'CALENDAR',
  },
  task: {
    icon: CheckCircle,
    accentColor: 'hsl(160, 70%, 45%)',
    label: 'TASK',
  },
  weather: {
    icon: Cloud,
    accentColor: 'hsl(200, 60%, 50%)',
    label: 'WEATHER',
  },
  memory: {
    icon: Lightbulb,
    accentColor: 'hsl(265, 60%, 55%)',
    label: 'INSIGHT',
  },
  info: {
    icon: MessageSquare,
    accentColor: 'hsl(215, 50%, 55%)',
    label: 'INFO',
  },
  news: {
    icon: Newspaper,
    accentColor: 'hsl(30, 80%, 50%)',
    label: 'NEWS',
  },
};

// --- Specialized Professional Views ---

const ensureAbsoluteUrl = (url: string) => {
  if (!/^https?:\/\//i.test(url)) {
    return `https://${url}`;
  }
  return url;
};

const CitationView = ({ data }: { data: any }) => (
  <a
    href={ensureAbsoluteUrl(data.url)}
    target="_blank"
    rel="noopener noreferrer"
    className="flex items-center gap-3 w-full p-3 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors group/cite"
  >
    {data.thumbnail && (
      <div className="w-12 h-12 rounded-lg overflow-hidden flex-shrink-0 border border-white/5">
        <img
          src={data.thumbnail}
          alt=""
          className="w-full h-full object-cover grayscale opacity-70 group-hover/cite:grayscale-0 group-hover/cite:opacity-100 transition-all"
        />
      </div>
    )}
    <div className="flex flex-col flex-1 min-w-0">
      {data.title && (
        <span className="text-xs font-medium text-foreground/80 truncate mb-0.5">
          {data.title}
        </span>
      )}
      <span className="text-[10px] text-muted-foreground truncate">
        {data.url.replace(/^https?:\/\/(www\.)?/, '')}
      </span>
    </div>
    <ExternalLink size={12} className="text-muted-foreground group-hover/cite:text-primary transition-colors flex-shrink-0" />
  </a>
);

const WeatherBriefing = ({ data }: { data: any }) => (
  <div className="mt-4 space-y-6 w-full">
    <div className="flex items-end justify-between border-b border-white/5 pb-6">
      <div className="flex flex-col">
        <div className="flex items-baseline gap-2">
          <span className="text-6xl font-light tracking-tighter text-foreground">
            {data.temperature_c}
          </span>
          <span className="text-2xl font-light text-muted-foreground">°C</span>
        </div>
        <span className="text-sm tracking-[0.2em] text-muted-foreground mt-2 uppercase font-semibold">
          {data.condition}
        </span>
      </div>
      <div className="text-right pb-1">
        <span className="text-xl font-light text-foreground/60">{data.temperature_f}°F</span>
      </div>
    </div>

    <div className="grid grid-cols-2 gap-4">
      <div className="flex items-center gap-3 p-4 rounded-2xl bg-white/[0.02] border border-white/5">
        <div className="p-2 rounded-lg bg-blue-500/10">
          <Droplets size={16} className="text-blue-400" />
        </div>
        <div className="flex flex-col">
          <span className="text-[10px] tracking-widest text-muted-foreground uppercase font-bold">Humidity</span>
          <span className="text-lg font-medium">{data.humidity}%</span>
        </div>
      </div>
      <div className="flex items-center gap-3 p-4 rounded-2xl bg-white/[0.02] border border-white/5">
        <div className="p-2 rounded-lg bg-teal-500/10">
          <Wind size={16} className="text-teal-400" />
        </div>
        <div className="flex flex-col">
          <span className="text-[10px] tracking-widest text-muted-foreground uppercase font-bold">Wind</span>
          <span className="text-lg font-medium">{data.wind_speed_kmh} <span className="text-xs font-normal opacity-50">km/h</span></span>
        </div>
      </div>
    </div>
  </div>
);

const TaskList = ({ tasks }: { tasks: any[] }) => (
  <div className="mt-4 space-y-2 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
    {tasks.map((task: any) => (
      <div key={task.id} className="flex items-center justify-between p-3 rounded-xl bg-white/[0.03] border border-white/5 group/task transition-all hover:bg-white/[0.06]">
        <div className="flex items-center gap-3">
          <div className={`w-1.5 h-1.5 rounded-full ${task.priority === 'high' ? 'bg-red-500' :
            task.priority === 'medium' ? 'bg-yellow-500' :
              task.priority === 'low' ? 'bg-green-500' : 'bg-primary/40'
            }`} />
          <span className="text-sm font-medium text-foreground/90">{task.title}</span>
        </div>
        {task.due_date && (
          <span className="text-[10px] font-mono text-muted-foreground">
            {new Date(task.due_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
          </span>
        )}
      </div>
    ))}
  </div>
);

const TaskReminders = ({ data }: { data: any }) => (
  <div className="mt-4 space-y-6 w-full">
    {data.tasks?.length > 0 && (
      <div className="space-y-3">
        <div className="flex items-center gap-2 px-1">
          <AlignLeft size={14} className="text-primary/70" />
          <span className="text-[10px] font-bold tracking-widest text-primary/70 uppercase">Pending Tasks</span>
        </div>
        <TaskList tasks={data.tasks} />
      </div>
    )}
    {data.overdue?.length > 0 && (
      <div className="space-y-3">
        <div className="flex items-center gap-2 px-1">
          <AlertTriangle size={14} className="text-red-400" />
          <span className="text-[10px] font-bold tracking-widest text-red-400 uppercase">Overdue</span>
        </div>
        <TaskList tasks={data.overdue} />
      </div>
    )}
    {data.due_today?.length > 0 && (
      <div className="space-y-3">
        <div className="flex items-center gap-2 px-1">
          <Clock size={14} className="text-yellow-400" />
          <span className="text-[10px] font-bold tracking-widest text-yellow-400 uppercase">Due Today</span>
        </div>
        <TaskList tasks={data.due_today} />
      </div>
    )}
    {data.due_soon?.length > 0 && (
      <div className="space-y-3">
        <div className="flex items-center gap-2 px-1">
          <Calendar size={14} className="text-teal-400" />
          <span className="text-[10px] font-bold tracking-widest text-teal-400 uppercase">Upcoming</span>
        </div>
        <TaskList tasks={data.due_soon} />
      </div>
    )}
  </div>
);

const SingleTaskDetails = ({ data }: { data: any }) => (
  <div className="mt-4 p-6 rounded-2xl bg-white/[0.03] border border-white/5 space-y-4">
    <div className="flex items-center justify-between">
      <div className={`px-2.5 py-1 rounded-lg text-[10px] font-bold tracking-widest uppercase border ${data.priority === 'high' ? 'bg-red-500/10 text-red-500 border-red-500/20' :
        data.priority === 'medium' ? 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20' :
          'bg-green-500/10 text-green-500 border-green-500/20'
        }`}>
        {data.priority?.toUpperCase() || 'NORMAL'} PRIORITY
      </div>
      {data.due_date && (
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <Clock size={12} />
          <span className="text-[10px] font-mono uppercase">
            {new Date(data.due_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
          </span>
        </div>
      )}
    </div>
    <div className="space-y-1">
      <h4 className="text-xl font-medium text-foreground tracking-tight">{data.title}</h4>
      {data.description && (
        <p className="text-sm text-muted-foreground leading-relaxed">{data.description}</p>
      )}
    </div>
    <div className="pt-2 flex items-center gap-4 text-[10px] font-bold tracking-widest text-muted-foreground/40 uppercase">
      <span>Status: {data.status || 'Active'}</span>
      <span>•</span>
      <span>ID: {data.id?.substring(0, 8) || 'AUTO'}</span>
    </div>
  </div>
);

const CalendarBriefing = ({ data }: { data: any }) => (
  <div className="mt-4 space-y-4 w-full">
    <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/5 space-y-6">
      <div className="flex flex-col gap-2">
        <span className="text-[10px] tracking-[0.2em] text-primary font-bold uppercase">Scheduled Appointment</span>
        <h4 className="text-2xl font-light text-foreground tracking-tight">{data.summary || data.title}</h4>
      </div>

      <div className="grid grid-cols-2 gap-8 py-4 border-y border-white/5">
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Clock size={12} className="text-primary/50" />
            <span className="text-[10px] tracking-widest uppercase font-bold">Start Time</span>
          </div>
          <span className="text-lg font-light">
            {data.start ? new Date(data.start).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }) : 'All day'}
          </span>
          <span className="text-[10px] text-muted-foreground/60 font-mono italic">
            {data.start ? new Date(data.start).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' }) : ''}
          </span>
        </div>
        {data.end && (
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Clock size={12} className="text-primary/50" />
              <span className="text-[10px] tracking-widest uppercase font-bold">End Time</span>
            </div>
            <span className="text-lg font-light">
              {new Date(data.end).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}
            </span>
          </div>
        )}
      </div>

      {(data.location || data.description) && (
        <div className="space-y-3 pt-2">
          {data.location && (
            <div className="flex items-start gap-3 text-muted-foreground">
              <MapPin size={14} className="mt-0.5 text-primary/40" />
              <span className="text-xs">{data.location}</span>
            </div>
          )}
          {data.description && (
            <div className="flex items-start gap-3 text-muted-foreground">
              <AlignLeft size={14} className="mt-0.5 text-primary/40" />
              <p className="text-xs italic leading-relaxed">{data.description}</p>
            </div>
          )}
        </div>
      )}
    </div>
  </div>
);

const NewsView = ({ data }: { data: any }) => (
  <div className="mt-4 space-y-4 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
    {data.articles?.map((article: any, idx: number) => (
      <a
        key={idx}
        href={ensureAbsoluteUrl(article.url)}
        target="_blank"
        rel="noopener noreferrer"
        className="flex gap-4 p-4 rounded-2xl bg-white/[0.03] border border-white/5 hover:bg-white/[0.06] transition-all group/news"
      >
        {article.thumbnail && (
          <div className="w-20 h-20 rounded-xl overflow-hidden flex-shrink-0 border border-white/5">
            <img src={article.thumbnail} alt="" className="w-full h-full object-cover grayscale opacity-80 group-hover/news:grayscale-0 group-hover/news:opacity-100 transition-all" />
          </div>
        )}
        <div className="flex flex-col flex-1 min-w-0 gap-1">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[10px] font-bold tracking-widest text-orange-400 uppercase truncate">
              {article.source}
            </span>
            {article.timestamp && (
              <span className="text-[9px] font-mono text-muted-foreground whitespace-nowrap">
                {new Date(article.timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
              </span>
            )}
          </div>
          <h4 className="text-sm font-medium text-foreground/90 leading-snug group-hover/news:text-primary transition-colors line-clamp-2">
            {article.title}
          </h4>
          <p className="text-xs text-muted-foreground line-clamp-2 mt-1 italic">
            {article.description}
          </p>
        </div>
      </a>
    ))}
  </div>
);

const InsightBriefing = ({ data }: { data: any }) => (
  <div className="mt-4 w-full">
    <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/5 relative overflow-hidden">
      <Lightbulb className="absolute -right-6 -bottom-6 w-32 h-32 text-primary/5 -rotate-12 pointer-events-none" />
      <p className="text-lg text-foreground/90 leading-relaxed font-light relative z-10">
        {data.answer}
      </p>
    </div>
  </div>
);

export const AcknowledgmentCard = forwardRef<HTMLDivElement, AcknowledgmentCardProps>(
  ({ type, title, subtitle, data, onDismiss, isCitation = false }, ref) => {
    const config = cardConfig[type];
    const Icon = config.icon;

    if (isCitation) {
      return (
        <motion.div
          ref={ref}
          initial={{ x: -50, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: -100, opacity: 0 }}
          className="pointer-events-auto w-full max-w-xs"
        >
          <CitationView data={data} />
        </motion.div>
      );
    }

    // Determine layout based on data structure
    const renderContent = () => {
      if (!data) return <p className="text-lg font-medium text-foreground leading-relaxed">{title}</p>;

      if (type === 'weather') return <WeatherBriefing data={data} />;
      if (type === 'memory') return <InsightBriefing data={data} />;
      if (type === 'news') return <NewsView data={data} />;

      // Task logic
      if (type === 'task') {
        if (data.tasks || data.overdue || data.due_today) {
          return <TaskReminders data={data} />;
        }
        return <SingleTaskDetails data={data} />;
      }

      // Calendar logic
      if (type === 'calendar') {
        if (data.events) {
          return (
            <div className="mt-4 space-y-4">
              <span className="text-[10px] tracking-widest text-muted-foreground font-bold uppercase px-1">Today's Agenda</span>
              <TaskList tasks={data.events.map((e: any) => ({ ...e, title: e.summary, priority: 'none' }))} />
            </div>
          );
        }
        return <CalendarBriefing data={data} />;
      }

      return <p className="text-lg font-medium text-foreground leading-relaxed">{title}</p>;
    };

    return (
      <motion.div
        ref={ref}
        initial={{ x: 100, opacity: 0, scale: 0.95 }}
        animate={{ x: 0, opacity: 1, scale: 1 }}
        exit={{ x: 100, opacity: 0, scale: 0.95 }}
        transition={{
          type: 'spring',
          stiffness: 350,
          damping: 30,
        }}
        className="glass-panel rounded-3xl p-8 w-full max-w-xl shadow-2xl relative overflow-hidden group"
        onClick={(e) => e.stopPropagation()}
        style={{
          borderTop: `1px solid ${config.accentColor}30`,
          background: 'linear-gradient(135deg, rgba(255,255,255,0.03), transparent)',
        }}
      >
        <div className="flex flex-col gap-6 relative z-10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div
                className="p-2.5 rounded-xl flex-shrink-0"
                style={{
                  background: `${config.accentColor}10`,
                  border: `1px solid ${config.accentColor}20`,
                }}
              >
                <Icon
                  size={18}
                  style={{ color: config.accentColor }}
                />
              </div>
              <div>
                <span
                  className="text-[10px] font-bold tracking-[0.25em] uppercase block opacity-60 font-mono"
                  style={{ color: config.accentColor }}
                >
                  {config.label}
                </span>
                <h3 className="text-sm font-bold text-foreground/90 tracking-widest uppercase mt-0.5">
                  {(subtitle || 'Briefing System').replace(/_/g, ' ')}
                </h3>
              </div>
            </div>
          </div>

          <div className="flex-1 w-full">
            {renderContent()}

            {subtitle && !data && (
              <p className="text-xs text-muted-foreground mt-3 font-medium uppercase tracking-wider opacity-60">
                {subtitle}
              </p>
            )}
          </div>
        </div>

        {/* Action Button - refined */}
        <button
          className="absolute top-8 right-8 p-3 rounded-full hover:bg-white/10 transition-all text-muted-foreground/60 hover:text-foreground z-20 group-hover:bg-white/5"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onDismiss?.();
          }}
          type="button"
          aria-label="Dismiss"
        >
          <X size={18} />
        </button>
      </motion.div >
    );
  }
);

AcknowledgmentCard.displayName = 'AcknowledgmentCard';
