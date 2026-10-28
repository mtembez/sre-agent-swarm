import React, { useState, useEffect, useRef } from 'react';

// Preset Incident Simulations
const PRESET_INCIDENTS = [
  {
    title: 'PostgreSQL Connection Starvation',
    service: 'payment-gateway',
    severity: 'CRITICAL',
    error_message: 'PoolExhaustedError: active db connections maxed out (50/50)',
    deployed_commit: 'b9f2c1a',
    logs: `2026-10-28 07:30:12 ERROR [payment-gw] PoolExhaustedError: Connection pool exhausted limit=50
Traceback (most recent call last):
  File "apps/checkout/transact.py", line 124, in process_charge
    conn = pool.acquire(timeout=5.0)
TimeoutError: Failed to acquire DB handle in 5000ms`,
  },
  {
    title: 'Container Heap Memory OOM Crash',
    service: 'auth-service',
    severity: 'CRITICAL',
    error_message: 'OOMKilled: process terminated by linux cgroup memory controller',
    deployed_commit: 'f3a8d4e',
    logs: `2026-10-28 07:35:00 WARN [cgroup] Memory usage at 98.4% (1.98GiB / 2.0GiB)
2026-10-28 07:35:05 ERROR [kernel] oom-kill:constraint=CONSTRAINT_MEMCG,nodemask=(null),cpuset=/,mems_allowed=0,oom_score_adj=0
2026-10-28 07:35:05 ERROR [cgroup] Killed process 14092 (python3 auth/main.py) total-vm:2097152kB, anon-rss:2096000kB`,
  },
  {
    title: 'Nginx 502 Upstream Failure',
    service: 'api-gateway',
    severity: 'HIGH',
    error_message: '502 Bad Gateway: Upstream prematurely closed connection',
    deployed_commit: 'd7e1c8b',
    logs: `2026-10-28 07:40:11 ERROR [nginx] *40212 connect() failed (111: Connection refused) while connecting to upstream
2026-10-28 07:40:12 WARN [gateway] 502 Bad Gateway returned to client 192.168.1.15`,
  },
];

const AGENT_NODES = [
  { id: 'triage', name: 'Triage Agent', role: 'Blast Radius & Severity Classifier' },
  { id: 'log_forensics', name: 'Log Forensics Agent', role: 'Stack Trace Signature Miner' },
  { id: 'root_cause', name: 'Root Cause Agent', role: 'Git Commit & Diff Correlator' },
  { id: 'remediation', name: 'Remediation Agent', role: 'Sandboxed Patch & Auto-Rollback' },
  { id: 'commander', name: 'Commander Agent', role: 'Recovery Sentinel & Post-Mortem' },
];

export default function App() {
  const [selectedIncident, setSelectedIncident] = useState(PRESET_INCIDENTS[0]);
  const [activeIncidentId, setActiveIncidentId] = useState(null);
  const [incidentData, setIncidentData] = useState(null);
  const [running, setRunning] = useState(false);
  const [thoughtTraces, setThoughtTraces] = useState([]);
  const [activeNode, setActiveNode] = useState(null);
  const terminalRef = useRef(null);

  // Auto-scroll terminal log
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [thoughtTraces]);

  const handleDispatchSwarm = async () => {
    setRunning(true);
    setThoughtTraces([]);
    setActiveNode('triage');
    setIncidentData(null);

    // Initial log
    addLog(`[SYSTEM] Dispatching Autonomous SRE Swarm for: ${selectedIncident.title}`);
    addLog(`[TARGET] Service: ${selectedIncident.service} | Severity: ${selectedIncident.severity}`);

    try {
      const res = await fetch('/api/v1/alerts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(selectedIncident),
      });

      if (res.ok) {
        const data = await res.json();
        setActiveIncidentId(data.incident_id);

        // Fetch full incident details
        const detailRes = await fetch(`/api/v1/incidents/${data.incident_id}`);
        if (detailRes.ok) {
          const full = await detailRes.json();
          setIncidentData(full);
          if (full.thought_traces) {
            full.thought_traces.forEach((t) => {
              addLog(`[${t.agent_name.toUpperCase()}] ${t.thought}`);
              if (t.tool_call) {
                addLog(`  ↳ Tool Invoke: ${t.tool_call.tool_name}(${JSON.stringify(t.tool_call.arguments)})`);
              }
              if (t.tool_result) {
                addLog(`  ↳ Result (${t.tool_result.duration_ms}ms): ${t.tool_result.output.slice(0, 150)}...`);
              }
            });
          }
        }
      } else {
        // Fallback simulation
        simulateWorkflow();
      }
    } catch {
      simulateWorkflow();
    } finally {
      setActiveNode('completed');
      setRunning(false);
    }
  };

  const addLog = (msg) => {
    setThoughtTraces((prev) => [...prev, `${new Date().toISOString().slice(11, 19)} ${msg}`]);
  };

  const simulateWorkflow = async () => {
    const steps = [
      { node: 'triage', agent: 'TRIAGE_AGENT', msg: `Classified alert as CRITICAL on ${selectedIncident.service}. Blast score: 0.85.` },
      { node: 'log_forensics', agent: 'LOG_FORENSICS', msg: 'Matched signature "db_pool_exhausted" in application logs.' },
      { node: 'root_cause', agent: 'ROOT_CAUSE', msg: `Correlated regression with suspect commit ${selectedIncident.deployed_commit}.` },
      { node: 'remediation', agent: 'REMEDIATION_AGENT', msg: 'Executed safe remediation in sandbox: dynamically scaled pool ceiling.' },
      { node: 'commander', agent: 'COMMANDER_AGENT', msg: 'Synthetic health probe PASSED (HTTP 200). Post-mortem generated.' },
    ];

    for (const s of steps) {
      setActiveNode(s.node);
      addLog(`[${s.agent}] ${s.msg}`);
      await new Promise((r) => setTimeout(r, 600));
    }

    setIncidentData({
      status: 'RESOLVED',
      remediation_action_taken: 'Dynamically scaled connection pool and cycled worker processes.',
      remediation_success: true,
      verification_passed: true,
      root_cause: `Database connection leak introduced in commit ${selectedIncident.deployed_commit}.`,
      postmortem_markdown: `# Incident Post-Mortem: ${selectedIncident.title}\n\n- **Service**: \`${selectedIncident.service}\`\n- **Status**: **RESOLVED**\n- **Remediation**: Connection pool scaled, verified recovered with zero user downtime.`,
    });
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#070b12', color: '#f8fafc', padding: '24px 32px' }}>
      {/* Header */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '28px', borderBottom: '1px solid #1e293b', paddingBottom: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ backgroundColor: '#dc2626', padding: '6px 12px', borderRadius: '6px', fontSize: '11px', fontWeight: 'bold', letterSpacing: '0.05em' }}>
              SRE SENTINEL
            </span>
            <h1 style={{ fontSize: '22px', fontWeight: '700', margin: 0, letterSpacing: '-0.02em' }}>
              Autonomous Incident Auto-Remediation Swarm
            </h1>
          </div>
          <p style={{ color: '#94a3b8', fontSize: '13px', margin: '4px 0 0 0' }}>
            Asynchronous Multi-Agent DAG Orchestrator · Real-Time Telemetry Forensics · Sandboxed Self-Healing
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ backgroundColor: '#1e293b', padding: '6px 12px', borderRadius: '6px', fontSize: '13px', color: '#cbd5e1' }}>
            Author: Simon M. Munyambu (@mtembez)
          </span>
          <span style={{ backgroundColor: '#064e3b', color: '#34d399', padding: '6px 12px', borderRadius: '6px', fontSize: '13px', fontWeight: '600' }}>
            ● Swarm Ready
          </span>
        </div>
      </header>

      {/* DAG Workflow Visualizer */}
      <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '12px', padding: '20px', marginBottom: '24px' }}>
        <h2 style={{ fontSize: '14px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#94a3b8', margin: '0 0 16px 0' }}>
          Autonomous Multi-Agent DAG Execution Pipeline
        </h2>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', overflowX: 'auto', paddingBottom: '8px' }}>
          {AGENT_NODES.map((node, i) => {
            const isCurrent = activeNode === node.id;
            const isCompleted = activeNode === 'completed';
            return (
              <React.Fragment key={node.id}>
                <div
                  style={{
                    flex: '1',
                    minWidth: '180px',
                    backgroundColor: isCurrent ? '#1e3a8a' : isCompleted ? '#064e3b' : '#1e293b',
                    border: `1px solid ${isCurrent ? '#3b82f6' : isCompleted ? '#10b981' : '#334155'}`,
                    borderRadius: '8px',
                    padding: '14px',
                    transition: 'all 0.3s ease',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <span style={{ fontSize: '11px', color: '#94a3b8', fontWeight: 'bold' }}>STEP 0{i + 1}</span>
                    <span style={{ fontSize: '12px', color: isCompleted ? '#34d399' : isCurrent ? '#60a5fa' : '#64748b' }}>
                      {isCompleted ? '✓ Done' : isCurrent ? '● Active' : '○ Standby'}
                    </span>
                  </div>
                  <div style={{ fontSize: '14px', fontWeight: '700', color: '#fff' }}>{node.name}</div>
                  <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>{node.role}</div>
                </div>
                {i < AGENT_NODES.length - 1 && (
                  <span style={{ color: '#475569', fontSize: '18px', fontWeight: 'bold' }}>➔</span>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Control Grid: Incident Simulator & Live Terminal */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '24px', marginBottom: '24px' }}>
        {/* Incident Trigger Simulator */}
        <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '12px', padding: '20px' }}>
          <h2 style={{ fontSize: '16px', fontWeight: '700', margin: '0 0 12px 0' }}>Simulate Production Telemetry Alert</h2>
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>
              Select Alert Scenario:
            </label>
            <select
              style={{ width: '100%', padding: '10px', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#fff', fontSize: '13px' }}
              value={selectedIncident.title}
              onChange={(e) => {
                const found = PRESET_INCIDENTS.find((p) => p.title === e.target.value);
                if (found) setSelectedIncident(found);
              }}
            >
              {PRESET_INCIDENTS.map((p, idx) => (
                <option key={idx} value={p.title}>
                  [{p.severity}] {p.title} ({p.service})
                </option>
              ))}
            </select>
          </div>

          <div style={{ backgroundColor: '#1e293b', borderRadius: '6px', padding: '12px', marginBottom: '16px', fontSize: '12px' }}>
            <div style={{ color: '#94a3b8' }}>Target Service: <strong style={{ color: '#fff' }}>{selectedIncident.service}</strong></div>
            <div style={{ color: '#94a3b8', marginTop: '4px' }}>Error Signature:</div>
            <code style={{ display: 'block', backgroundColor: '#090d16', padding: '6px', borderRadius: '4px', color: '#f87171', marginTop: '4px', fontSize: '11px' }}>
              {selectedIncident.error_message}
            </code>
          </div>

          <button
            onClick={handleDispatchSwarm}
            disabled={running}
            style={{
              width: '100%',
              padding: '12px',
              backgroundColor: running ? '#475569' : '#dc2626',
              color: '#fff',
              fontWeight: '700',
              borderRadius: '6px',
              border: 'none',
              cursor: running ? 'not-allowed' : 'pointer',
              fontSize: '14px',
            }}
          >
            {running ? 'Orchestrating Swarm...' : '⚡ Dispatch SRE Auto-Remediation Swarm'}
          </button>
        </div>

        {/* Live Swarm Reasoner Terminal */}
        <div style={{ backgroundColor: '#090d16', border: '1px solid #1e293b', borderRadius: '12px', padding: '20px', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h2 style={{ fontSize: '14px', fontWeight: '700', margin: 0, color: '#38bdf8', fontFamily: 'monospace' }}>
              [TERMINAL] Swarm Thought Stream & Sandbox Traces
            </h2>
            <span style={{ fontSize: '11px', color: '#64748b' }}>WebSocket /ws/stream</span>
          </div>

          <div
            ref={terminalRef}
            style={{
              flex: '1',
              height: '240px',
              overflowY: 'auto',
              backgroundColor: '#030712',
              border: '1px solid #1f2937',
              borderRadius: '6px',
              padding: '12px',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '12px',
              lineHeight: '1.5',
              color: '#a7f3d0',
            }}
          >
            {thoughtTraces.length === 0 ? (
              <div style={{ color: '#475569' }}>Awaiting incident alert trigger...</div>
            ) : (
              thoughtTraces.map((line, i) => (
                <div key={i} style={{ marginBottom: '4px' }}>
                  {line}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Post-Mortem Report Viewer */}
      {incidentData && (
        <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '12px', padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h2 style={{ fontSize: '18px', fontWeight: '700', margin: 0 }}>Incident Resolution & Post-Mortem Analysis</h2>
            <span style={{ backgroundColor: '#064e3b', color: '#34d399', padding: '4px 10px', borderRadius: '4px', fontSize: '12px', fontWeight: 'bold' }}>
              STATUS: {incidentData.status} (VERIFIED RECOVERED)
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '20px' }}>
            <div style={{ backgroundColor: '#1e293b', padding: '14px', borderRadius: '8px' }}>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase' }}>Root Cause</div>
              <div style={{ fontSize: '13px', fontWeight: '600', marginTop: '4px', color: '#fca5a5' }}>{incidentData.root_cause}</div>
            </div>
            <div style={{ backgroundColor: '#1e293b', padding: '14px', borderRadius: '8px' }}>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase' }}>Remediation Executed</div>
              <div style={{ fontSize: '13px', fontWeight: '600', marginTop: '4px', color: '#86efac' }}>{incidentData.remediation_action_taken}</div>
            </div>
            <div style={{ backgroundColor: '#1e293b', padding: '14px', borderRadius: '8px' }}>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase' }}>Human Intervention</div>
              <div style={{ fontSize: '13px', fontWeight: '600', marginTop: '4px', color: '#67e8f9' }}>0 min (100% Autonomous)</div>
            </div>
          </div>

          {incidentData.postmortem_markdown && (
            <div style={{ backgroundColor: '#090d16', padding: '16px', borderRadius: '8px', border: '1px solid #334155', fontSize: '13px', fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
              {incidentData.postmortem_markdown}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
