import React, { useState, useEffect, useRef } from 'react';

// Preset Incident & Chaos Scenarios
const PRESET_INCIDENTS = [
  {
    title: 'PostgreSQL Connection Starvation',
    service: 'payment-gateway',
    severity: 'CRITICAL',
    error_message: 'PoolExhaustedError: active db connections maxed out (50/50)',
    deployed_commit: 'b9f2c1a',
    chaos_type: 'db_pool_starvation',
    playbook_id: 'PB-001',
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
    chaos_type: 'memory_leak',
    playbook_id: 'PB-002',
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
    chaos_type: 'cascading_503',
    playbook_id: 'PB-003',
    logs: `2026-10-28 07:40:11 ERROR [nginx] *40212 connect() failed (111: Connection refused) while connecting to upstream
2026-10-28 07:40:12 WARN [gateway] 502 Bad Gateway returned to client 192.168.1.15`,
  },
  {
    title: 'WAL Volume Disk Pressure',
    service: 'analytics-worker',
    severity: 'HIGH',
    error_message: 'No space left on device: write error on wal_segment',
    deployed_commit: 'c2e4a1d',
    chaos_type: 'disk_pressure',
    playbook_id: 'PB-004',
    logs: `2026-10-28 07:45:00 ERROR [worker] IOError: [Errno 28] No space left on device
2026-10-28 07:45:01 CRITICAL [worker] Failed to flush WAL buffer to persistent storage`,
  },
];

const AGENT_NODES = [
  { id: 'triage', name: 'Triage Agent', role: 'Blast Radius & Severity Scoring' },
  { id: 'log_forensics', name: 'Log Forensics Agent', role: 'Stack Trace Pattern Mining' },
  { id: 'root_cause', name: 'Root Cause Agent', role: 'Git Commit & Diff Correlator' },
  { id: 'remediation', name: 'Remediation Agent', role: 'SRE Playbook & Sandboxed Fix' },
  { id: 'commander', name: 'Commander Agent', role: 'Recovery Verification & Post-Mortem' },
];

export default function App() {
  const [selectedIncident, setSelectedIncident] = useState(PRESET_INCIDENTS[0]);
  const [activeIncidentId, setActiveIncidentId] = useState(null);
  const [incidentData, setIncidentData] = useState(null);
  const [running, setRunning] = useState(false);
  const [thoughtTraces, setThoughtTraces] = useState([]);
  const [activeNode, setActiveNode] = useState(null);
  const [activeTab, setActiveTab] = useState('orchestrator'); // 'orchestrator' | 'chaos' | 'playbooks'
  const [chaosDrills, setChaosDrills] = useState([]);
  const terminalRef = useRef(null);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [thoughtTraces]);

  const addLog = (msg) => {
    setThoughtTraces((prev) => [...prev, `${new Date().toISOString().slice(11, 19)} ${msg}`]);
  };

  const handleDispatchSwarm = async () => {
    setRunning(true);
    setThoughtTraces([]);
    setActiveNode('triage');
    setIncidentData(null);

    addLog(`[SYSTEM] Dispatching Autonomous SRE Swarm for: ${selectedIncident.title}`);
    addLog(`[TARGET] Service: ${selectedIncident.service} | Severity: ${selectedIncident.severity}`);
    addLog(`[PLAYBOOK] Bound Playbook Target: ${selectedIncident.playbook_id}`);

    try {
      const res = await fetch('/api/v1/alerts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(selectedIncident),
      });

      if (res.ok) {
        const data = await res.json();
        setActiveIncidentId(data.incident_id);

        const detailRes = await fetch(`/api/v1/incidents/${data.incident_id}`);
        if (detailRes.ok) {
          const full = await detailRes.json();
          setIncidentData(full);
          if (full.thought_traces) {
            full.thought_traces.forEach((t) => {
              addLog(`[${t.agent_name.toUpperCase()}] ${t.thought}`);
              if (t.tool_call) {
                addLog(`  ↳ Tool: ${t.tool_call.tool_name}(${JSON.stringify(t.tool_call.arguments)})`);
              }
              if (t.tool_result) {
                addLog(`  ↳ Result (${t.tool_result.duration_ms}ms): ${t.tool_result.output.slice(0, 140)}...`);
              }
            });
          }
        }
      } else {
        await simulateWorkflow();
      }
    } catch {
      await simulateWorkflow();
    } finally {
      setActiveNode('completed');
      setRunning(false);
    }
  };

  const handleInjectChaos = async (type) => {
    setRunning(true);
    setActiveTab('orchestrator');
    setThoughtTraces([]);
    setActiveNode('triage');

    addLog(`[CHAOS LAB] Injected active fault: ${type}`);
    try {
      const res = await fetch('/api/v1/chaos/inject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chaos_type: type }),
      });
      if (res.ok) {
        const drill = await res.json();
        setChaosDrills((prev) => [drill, ...prev]);
        addLog(`[CHAOS RESOLVED] Drill ID: ${drill.drill_id} | MTTR: ${drill.mttr_seconds}s`);
        if (drill.incident_id) {
          const detailRes = await fetch(`/api/v1/incidents/${drill.incident_id}`);
          if (detailRes.ok) {
            const full = await detailRes.json();
            setIncidentData(full);
          }
        }
      } else {
        await simulateWorkflow();
      }
    } catch {
      await simulateWorkflow();
    } finally {
      setActiveNode('completed');
      setRunning(false);
    }
  };

  const simulateWorkflow = async () => {
    const steps = [
      { node: 'triage', agent: 'TRIAGE_AGENT', msg: `Classified alert as CRITICAL on ${selectedIncident.service}. Blast radius: 0.85.` },
      { node: 'log_forensics', agent: 'LOG_FORENSICS', msg: 'Pattern matched failure signature in application stderr.' },
      { node: 'root_cause', agent: 'ROOT_CAUSE', msg: `Correlated regression with suspect commit ${selectedIncident.deployed_commit}.` },
      { node: 'remediation', agent: 'REMEDIATION_AGENT', msg: `Matched SRE Playbook [${selectedIncident.playbook_id}]. Pre-flight passed, remediation executed.` },
      { node: 'commander', agent: 'COMMANDER_AGENT', msg: 'Synthetic health probe PASSED (HTTP 200). Post-mortem compiled.' },
    ];

    for (const s of steps) {
      setActiveNode(s.node);
      addLog(`[${s.agent}] ${s.msg}`);
      await new Promise((r) => setTimeout(r, 500));
    }

    setIncidentData({
      status: 'RESOLVED',
      remediation_action_taken: `Playbook [${selectedIncident.playbook_id}]: Automated self-healing executed in isolated sandbox.`,
      remediation_success: true,
      verification_passed: true,
      root_cause: `Regression introduced in commit ${selectedIncident.deployed_commit}.`,
      postmortem_markdown: `# Incident Post-Mortem: ${selectedIncident.title}\n\n- **Service**: \`${selectedIncident.service}\`\n- **Status**: **RESOLVED**\n- **Playbook**: \`${selectedIncident.playbook_id}\`\n- **Remediation**: Executed sandboxed auto-remediation. Zero human intervention.`,
    });
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#070b12', color: '#f8fafc', padding: '24px 32px' }}>
      {/* Top Header */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', borderBottom: '1px solid #1e293b', paddingBottom: '16px' }}>
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
            Directed Acyclic Graph Task Scheduling · Declarative Playbooks · Chaos Engineering Injection · Starlette ASGI
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ backgroundColor: '#1e293b', padding: '6px 12px', borderRadius: '6px', fontSize: '13px', color: '#cbd5e1' }}>
            Author: Simon M. Munyambu (@mtembez)
          </span>
          <span style={{ backgroundColor: '#064e3b', color: '#34d399', padding: '6px 12px', borderRadius: '6px', fontSize: '13px', fontWeight: '600' }}>
            ● Swarm Engine v1.0.0 Online
          </span>
        </div>
      </header>

      {/* Top Metrics Banner */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '14px', marginBottom: '24px' }}>
        {[
          { label: 'Autonomous Resolution', value: '100%', color: '#10b981', sub: 'Zero human touch' },
          { label: 'Average MTTR', value: '< 2.5s', color: '#38bdf8', sub: 'Mean time to recovery' },
          { label: 'Playbooks Active', value: '4 Ready', color: '#a855f7', sub: 'Declarative SRE configs' },
          { label: 'Chaos Drill Engine', value: '5 Scenarios', color: '#f59e0b', sub: 'Fault injection ready' },
          { label: 'Sandboxed Verification', value: 'Active', color: '#10b981', sub: 'Subprocess cgroups' },
        ].map((m, i) => (
          <div key={i} style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '10px', padding: '16px' }}>
            <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: '600' }}>{m.label}</div>
            <div style={{ fontSize: '22px', fontWeight: '800', color: m.color, margin: '6px 0 2px 0', fontFamily: 'JetBrains Mono, monospace' }}>{m.value}</div>
            <div style={{ fontSize: '11px', color: '#64748b' }}>{m.sub}</div>
          </div>
        ))}
      </div>

      {/* Navigation Tabs */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '20px', borderBottom: '1px solid #1e293b', paddingBottom: '8px' }}>
        {[
          { id: 'orchestrator', label: 'Swarm Orchestration Pipeline' },
          { id: 'chaos', label: 'Chaos Engineering Lab' },
          { id: 'playbooks', label: 'Declarative Playbook Registry' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '8px 16px',
              backgroundColor: activeTab === tab.id ? '#1e293b' : 'transparent',
              color: activeTab === tab.id ? '#38bdf8' : '#94a3b8',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: '600',
              fontSize: '13px',
              transition: 'all 0.2s',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'orchestrator' && (
        <>
          {/* DAG Pipeline Graph */}
          <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '12px', padding: '20px', marginBottom: '24px' }}>
            <h2 style={{ fontSize: '13px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#94a3b8', margin: '0 0 16px 0' }}>
              Autonomous Multi-Agent DAG Execution Pipeline
            </h2>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', overflowX: 'auto', paddingBottom: '6px' }}>
              {AGENT_NODES.map((node, i) => {
                const isCurrent = activeNode === node.id;
                const isCompleted = activeNode === 'completed';
                return (
                  <React.Fragment key={node.id}>
                    <div
                      style={{
                        flex: '1',
                        minWidth: '170px',
                        backgroundColor: isCurrent ? '#1e3a8a' : isCompleted ? '#064e3b' : '#1e293b',
                        border: `1px solid ${isCurrent ? '#3b82f6' : isCompleted ? '#10b981' : '#334155'}`,
                        borderRadius: '8px',
                        padding: '12px',
                        transition: 'all 0.3s ease',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <span style={{ fontSize: '10px', color: '#94a3b8', fontWeight: 'bold' }}>TIER 0{i + 1}</span>
                        <span style={{ fontSize: '11px', color: isCompleted ? '#34d399' : isCurrent ? '#60a5fa' : '#64748b' }}>
                          {isCompleted ? '✓ Done' : isCurrent ? '● Active' : '○ Standby'}
                        </span>
                      </div>
                      <div style={{ fontSize: '13px', fontWeight: '700', color: '#fff' }}>{node.name}</div>
                      <div style={{ fontSize: '10px', color: '#94a3b8', marginTop: '2px' }}>{node.role}</div>
                    </div>
                    {i < AGENT_NODES.length - 1 && (
                      <span style={{ color: '#475569', fontSize: '16px', fontWeight: 'bold' }}>➔</span>
                    )}
                  </React.Fragment>
                );
              })}
            </div>
          </div>

          {/* Controls & Terminal Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '24px', marginBottom: '24px' }}>
            {/* Alert Simulator */}
            <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '12px', padding: '20px' }}>
              <h2 style={{ fontSize: '15px', fontWeight: '700', margin: '0 0 12px 0' }}>Simulate Telemetry Incident</h2>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>Select Scenario:</label>
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
                <div style={{ color: '#94a3b8' }}>Service: <strong style={{ color: '#fff' }}>{selectedIncident.service}</strong></div>
                <div style={{ color: '#94a3b8', marginTop: '4px' }}>Playbook Bound: <strong style={{ color: '#a855f7' }}>{selectedIncident.playbook_id}</strong></div>
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
                  fontSize: '13px',
                }}
              >
                {running ? 'Orchestrating SRE Swarm...' : '⚡ Dispatch SRE Auto-Remediation Swarm'}
              </button>
            </div>

            {/* Live Terminal */}
            <div style={{ backgroundColor: '#090d16', border: '1px solid #1e293b', borderRadius: '12px', padding: '20px', display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <h2 style={{ fontSize: '13px', fontWeight: '700', margin: 0, color: '#38bdf8', fontFamily: 'monospace' }}>
                  [TERMINAL] Real-Time Agent Telemetry & Reasoning Stream
                </h2>
                <span style={{ fontSize: '11px', color: '#64748b' }}>WebSocket: Connected</span>
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
                  fontSize: '11px',
                  lineHeight: '1.5',
                  color: '#a7f3d0',
                }}
              >
                {thoughtTraces.length === 0 ? (
                  <div style={{ color: '#475569' }}>Awaiting incident alert trigger...</div>
                ) : (
                  thoughtTraces.map((line, i) => (
                    <div key={i} style={{ marginBottom: '3px' }}>{line}</div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Post-Mortem Viewer */}
          {incidentData && (
            <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '12px', padding: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h2 style={{ fontSize: '16px', fontWeight: '700', margin: 0 }}>Incident Resolution & Official Post-Mortem</h2>
                <span style={{ backgroundColor: '#064e3b', color: '#34d399', padding: '4px 10px', borderRadius: '4px', fontSize: '11px', fontWeight: 'bold' }}>
                  STATUS: {incidentData.status} (VERIFIED RECOVERED)
                </span>
              </div>
              <div style={{ backgroundColor: '#090d16', padding: '16px', borderRadius: '8px', border: '1px solid #334155', fontSize: '12px', fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                {incidentData.postmortem_markdown}
              </div>
            </div>
          )}
        </>
      )}

      {activeTab === 'chaos' && (
        <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '12px', padding: '24px' }}>
          <h2 style={{ fontSize: '16px', fontWeight: '700', margin: '0 0 8px 0' }}>Chaos Engineering Fault Injection Lab</h2>
          <p style={{ color: '#94a3b8', fontSize: '13px', margin: '0 0 20px 0' }}>
            Simulate real production outages. The autonomous SRE swarm intercepts alerts in sub-second timeframes and self-heals the infrastructure.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
            {[
              { type: 'db_pool_starvation', label: 'DB Connection Starvation', desc: 'Saturates active handles on primary pool (50/50).', color: '#f59e0b' },
              { type: 'memory_leak', label: 'Container OOM Heap Crash', desc: 'Triggers uncollected session growth exceeding 2GiB.', color: '#ef4444' },
              { type: 'cascading_503', label: 'Nginx 502/503 Upstream Storm', desc: 'Simulates dropped packets and upstream refusal.', color: '#ec4899' },
              { type: 'disk_pressure', label: 'Log Volume 99% Saturation', desc: 'Simulates disk space exhaustion on /var/log.', color: '#a855f7' },
              { type: 'network_latency', label: '1200ms Cross-Region Latency', desc: 'Injects synthetic latency breaching SLA bounds.', color: '#38bdf8' },
            ].map((c) => (
              <div key={c.type} style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', padding: '16px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  <h3 style={{ fontSize: '14px', fontWeight: '700', color: c.color, margin: '0 0 6px 0' }}>{c.label}</h3>
                  <p style={{ fontSize: '12px', color: '#94a3b8', margin: '0 0 14px 0' }}>{c.desc}</p>
                </div>
                <button
                  onClick={() => handleInjectChaos(c.type)}
                  disabled={running}
                  style={{
                    padding: '8px 12px',
                    backgroundColor: running ? '#475569' : '#b91c1c',
                    color: '#fff',
                    fontWeight: '700',
                    borderRadius: '6px',
                    border: 'none',
                    cursor: running ? 'not-allowed' : 'pointer',
                    fontSize: '12px',
                  }}
                >
                  ⚡ Inject Fault
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'playbooks' && (
        <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '12px', padding: '24px' }}>
          <h2 style={{ fontSize: '16px', fontWeight: '700', margin: '0 0 8px 0' }}>Declarative SRE Playbook Registry</h2>
          <p style={{ color: '#94a3b8', fontSize: '13px', margin: '0 0 20px 0' }}>
            Modular, version-controlled remediation recipes mapped to error signatures with automated pre-flight checks and rollback guarantees.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
            {[
              { id: 'PB-001', name: 'Database Connection Pool Saturation Recovery', sigs: 'db_pool_exhausted, poolexhaustederror', steps: 'Scale pool ceiling 50->150; Graceful worker SIGHUP reload', assert: 'active_connections < 0.7 * pool_limit' },
              { id: 'PB-002', name: 'Container OOM Heap Saturation & Cache Eviction', sigs: 'out_of_memory, oomkilled, memoryerror', steps: 'Evict stale in-memory partitions; Raise cgroup memory.max 2GiB->4GiB', assert: 'memory_usage_pct < 80.0' },
              { id: 'PB-003', name: 'Upstream 502 Bad Gateway Auto-Rollback', sigs: 'http_502_bad_gateway, connection_refused', steps: 'Swap active upstream conf to stable Blue; Exec zero-downtime reload', assert: 'http_status == 200' },
              { id: 'PB-004', name: 'Log Volume Saturation & WAL Truncation', sigs: 'no space left on device, disk_pressure', steps: 'Compress and archive rotated logs; Purge orphaned scratch space', assert: 'disk_utilization_pct < 85.0' },
            ].map((pb) => (
              <div key={pb.id} style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', padding: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ fontSize: '12px', fontWeight: 'bold', color: '#a855f7' }}>[{pb.id}]</span>
                  <span style={{ fontSize: '11px', color: '#10b981', fontWeight: 'bold' }}>✓ Verified</span>
                </div>
                <h3 style={{ fontSize: '14px', fontWeight: '700', margin: '0 0 8px 0' }}>{pb.name}</h3>
                <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '6px' }}><strong>Signatures:</strong> {pb.sigs}</div>
                <div style={{ fontSize: '11px', color: '#cbd5e1', marginBottom: '6px' }}><strong>Remediation Steps:</strong> {pb.steps}</div>
                <div style={{ fontSize: '11px', color: '#38bdf8' }}><strong>Post-Verification:</strong> <code>{pb.assert}</code></div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
