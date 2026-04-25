import { useState, useEffect } from 'react';
import { Activity, AlertTriangle, CheckCircle2, Terminal, Server, ArrowRight } from 'lucide-react';
import './Dashboard.css';

// --- TYPES ---
interface HealthCheck {
  status: string;
  required: boolean;
  details: Record<string, any>;
}

interface HealthReadiness {
  status: string;
  database: string;
  workflows: string;
  checks: Record<string, HealthCheck>;
}

// --- MOCK DATA ---
const MOCK_AGENTS = [
  { id: 'run-8f72a', profile: 'lead-qualifier', status: 'RUNNING', duration: '2.4s' },
  { id: 'run-3b11c', profile: 'sales-closer', status: 'COMPLETED', duration: '12.1s' },
  { id: 'run-9d44e', profile: 'outreach-specialist', status: 'FAILED', duration: '45.0s' },
  { id: 'run-1a22b', profile: 'lead-qualifier', status: 'RUNNING', duration: '0.8s' },
  { id: 'run-5c33d', profile: 'researcher', status: 'AWAITING_APPROVAL', duration: '1m 12s' },
];

const MOCK_ALERTS = [
  { id: 'al-101', severity: 'error', message: 'Agent tool max retries exceeded', target: 'run-9d44e', time: '2m ago' },
  { id: 'al-102', severity: 'warning', message: 'LLM Provider latency spike', target: 'openai-gpt4', time: '5m ago' },
  { id: 'al-103', severity: 'error', message: 'Worker output invalid JSON', target: 'data-enricher', time: '12m ago' },
];

// --- COMPONENTS ---

const StatusBadge = ({ status }: { status: string }) => {
  let colorVar = '--color-text-secondary';
  let dotColor = 'transparent';

  const s = status.toUpperCase();
  if (s === 'RUNNING' || s === 'READY' || s === 'OK' || s === 'LIVE') {
    colorVar = '--color-semantic-healthy';
    dotColor = 'var(--color-semantic-healthy)';
  } else if (s === 'COMPLETED') {
    colorVar = '--color-semantic-healthy';
    dotColor = 'var(--color-semantic-healthy)';
  } else if (s === 'FAILED' || s === 'NOT_READY') {
    colorVar = '--color-semantic-error';
    dotColor = 'var(--color-semantic-error)';
  } else if (s === 'AWAITING_APPROVAL' || s === 'DEGRADED') {
    colorVar = '--color-semantic-warning';
    dotColor = 'var(--color-semantic-warning)';
  }

  return (
    <div className="status-badge" style={{ color: `var(${colorVar})`, borderColor: `var(${colorVar})` }}>
      <div className="status-dot" style={{ backgroundColor: dotColor }}></div>
      <span className="monospace text-xs">{status}</span>
    </div>
  );
};

const MetricBlock = ({ label, value, unit, isLive = false }: { label: string, value: string | number, unit?: string, isLive?: boolean }) => {
  const [flash, setFlash] = useState(false);
  
  useEffect(() => {
    if (isLive) {
      const interval = setInterval(() => {
        if (Math.random() > 0.7) {
          setFlash(true);
          setTimeout(() => setFlash(false), 1500);
        }
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [isLive]);

  return (
    <div className="metric-block">
      <div className="metric-label">{label}</div>
      <div className={`metric-value monospace ${flash ? 'flash-on-update' : ''}`}>
        {value}
        {unit && <span className="metric-unit">{unit}</span>}
      </div>
    </div>
  );
};

export const Dashboard = () => {
  const [health, setHealth] = useState<HealthReadiness | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const response = await fetch('/api/v1/health/readiness');
        const json = await response.json();
        setHealth(json.data);
      } catch (error) {
        console.error('Failed to fetch health:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  const overallStatus = health?.status || 'UNKNOWN';

  return (
    <div className="dashboard-container">
      {/* Header Panel */}
      <header className="panel header-panel">
        <div className="header-brand">
          <Terminal size={20} className="brand-icon" />
          <h1>HELLO_SALES // CENTRAL PULSE</h1>
        </div>
        <div className="header-status">
          <div className={`system-health ${overallStatus.toLowerCase()}`}>
            {overallStatus === 'ready' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
            <span className="monospace">SYSTEM {overallStatus.toUpperCase()}</span>
          </div>
          <div className="live-indicator">
            <div className="pulse-dot"></div>
            <span className="monospace">LIVE</span>
          </div>
        </div>
      </header>

      {/* Main Grid */}
      <main className="dashboard-grid">
        
        {/* Top Metrics Row */}
        <div className="panel metric-row">
          <MetricBlock label="ACTIVE AGENTS" value={42} isLive />
          <div className="panel-divider"></div>
          <MetricBlock label="WORKERS (CPM)" value={128} isLive />
          <div className="panel-divider"></div>
          <MetricBlock label="AVG LLM LATENCY" value="1.2" unit="s" />
          <div className="panel-divider"></div>
          <MetricBlock label="SUCCESS RATE" value="98.4" unit="%" />
        </div>

        {/* Content Layout */}
        <div className="content-layout">
          
          {/* Left Column: Live Agent Feed */}
          <div className="panel feed-panel">
            <div className="panel-header">
              <h2><Activity size={16}/> ACTIVE RUNS</h2>
              <span className="monospace text-xs text-secondary">REAL-TIME</span>
            </div>
            
            <div className="feed-table">
              <div className="feed-table-header monospace text-xs">
                <div>RUN ID</div>
                <div>PROFILE</div>
                <div>DURATION</div>
                <div>STATE</div>
              </div>
              <div className="feed-table-body">
                {MOCK_AGENTS.map((agent, i) => (
                  <div key={i} className="feed-row">
                    <div className="monospace text-secondary">{agent.id}</div>
                    <div className="monospace">{agent.profile}</div>
                    <div className="monospace text-secondary">{agent.duration}</div>
                    <div><StatusBadge status={agent.status} /></div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right Column: Alerts & Workloads */}
          <div className="side-column">
            
            {/* Alerts Panel */}
            <div className="panel alerts-panel">
              <div className="panel-header">
                <h2 className="text-error"><AlertTriangle size={16}/> ACTIVE ALERTS</h2>
                <span className="badge-count">3</span>
              </div>
              <div className="alerts-list">
                {MOCK_ALERTS.map((alert, i) => (
                  <div key={i} className={`alert-item severity-${alert.severity}`}>
                    <div className="alert-meta monospace text-xs">
                      <span>{alert.time}</span>
                      <span className="alert-target">{alert.target}</span>
                    </div>
                    <div className="alert-message">{alert.message}</div>
                    <button className="alert-action">
                      <span className="monospace text-xs">VIEW TRACE</span>
                      <ArrowRight size={14} />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Infrastructure Panel */}
            <div className="panel infra-panel">
              <div className="panel-header">
                <h2><Server size={16}/> INFRASTRUCTURE</h2>
              </div>
              <div className="infra-grid">
                {loading ? (
                   <div className="infra-item monospace text-xs text-secondary">LOADING INFRA STATUS...</div>
                ) : (
                  <>
                    <div className="infra-item">
                      <span className="monospace text-xs text-secondary">DATABASE</span>
                      <StatusBadge status={health?.database || 'unknown'} />
                    </div>
                    <div className="infra-item">
                      <span className="monospace text-xs text-secondary">WORKFLOWS</span>
                      <StatusBadge status={health?.workflows || 'unknown'} />
                    </div>
                    {health && Object.entries(health.checks).map(([name, check]) => (
                      <div key={name} className="infra-item">
                        <span className="monospace text-xs text-secondary">{name.toUpperCase()}</span>
                        <StatusBadge status={check.status} />
                      </div>
                    ))}
                  </>
                )}
              </div>
            </div>

          </div>
        </div>
      </main>
    </div>
  );
};
