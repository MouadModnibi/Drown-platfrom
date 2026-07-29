'use client';

import React, { useEffect, useState, use } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
  Globe,
  Layers,
  Terminal,
  Activity,
  History,
  Key,
  Trash2,
  Copy,
  Check,
  Eye,
  EyeOff,
  Plus,
  RefreshCw,
  AlertCircle,
  ExternalLink,
  Cpu,
  HardDrive,
} from 'lucide-react';
import {
  fetchApi,
  ReplicaMetric,
  AppDeployment,
  AppConfig,
} from '@/lib/api-client';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Tabs } from '@/components/ui/Tabs';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';

export default function AppDetailPage({ params }: { params: Promise<{ name: string }> }) {
  const resolvedParams = use(params);
  const appName = resolvedParams.name;
  const router = useRouter();

  const [activeTab, setActiveTab] = useState('replicas');

  // App metrics & state
  const [replicas, setReplicas] = useState<ReplicaMetric[]>([]);
  const [replicasLoading, setReplicasLoading] = useState(true);

  // Scaling
  const [scalingCount, setScalingCount] = useState(1);
  const [isScaleOpen, setIsScaleOpen] = useState(false);
  const [scaleLoading, setScaleLoading] = useState(false);

  // Logs
  const [logs, setLogs] = useState('');
  const [logsLoading, setLogsLoading] = useState(false);

  // Deployments
  const [deployments, setDeployments] = useState<AppDeployment[]>([]);
  const [deploymentsLoading, setDeploymentsLoading] = useState(false);

  // Environment Configs
  const [configs, setConfigs] = useState<AppConfig[]>([]);
  const [configsLoading, setConfigsLoading] = useState(false);
  const [visibleKeys, setVisibleKeys] = useState<Record<string, boolean>>({});
  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');
  const [isAddConfigOpen, setIsAddConfigOpen] = useState(false);

  // Delete App Modal
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [confirmNameInput, setConfirmNameInput] = useState('');
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  // Copy helper
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const loadMetrics = async () => {
    try {
      const data = await fetchApi<{ replicas: ReplicaMetric[] }>(`/apps/${appName}/metrics`);
      setReplicas(data.replicas || []);
      setScalingCount(data.replicas?.length || 1);
    } catch (err: any) {
      console.error('Failed to load metrics:', err);
    } finally {
      setReplicasLoading(false);
    }
  };

  const loadLogs = async () => {
    setLogsLoading(true);
    try {
      const data = await fetchApi<{ logs: string }>(`/apps/${appName}/logs`);
      setLogs(data.logs || 'No logs available');
    } catch (err: any) {
      setLogs('Error fetching container logs');
    } finally {
      setLogsLoading(false);
    }
  };

  const loadDeployments = async () => {
    setDeploymentsLoading(true);
    try {
      const data = await fetchApi<{ deployments: AppDeployment[] }>(`/apps/${appName}/deployments`);
      setDeployments(data.deployments || []);
    } catch (err: any) {
      console.error('Failed to load deployments:', err);
    } finally {
      setDeploymentsLoading(false);
    }
  };

  const loadConfigs = async () => {
    setConfigsLoading(true);
    try {
      const data = await fetchApi<{ configs: AppConfig[] }>(`/apps/${appName}/config`);
      setConfigs(data.configs || []);
    } catch (err: any) {
      console.error('Failed to load configs:', err);
    } finally {
      setConfigsLoading(false);
    }
  };

  useEffect(() => {
    loadMetrics();
  }, [appName]);

  useEffect(() => {
    if (activeTab === 'logs') loadLogs();
    if (activeTab === 'deployments') loadDeployments();
    if (activeTab === 'config') loadConfigs();
  }, [activeTab]);

  const handleScale = async () => {
    setScaleLoading(true);
    try {
      await fetchApi(`/apps/${appName}/scale`, {
        method: 'POST',
        body: JSON.stringify({ replicas: scalingCount }),
      });
      setIsScaleOpen(false);
      loadMetrics();
    } catch (err: any) {
      alert(err.message || 'Scale failed');
    } finally {
      setScaleLoading(false);
    }
  };

  const handleAddConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKey) return;
    try {
      const data = await fetchApi<{ configs: AppConfig[] }>(`/apps/${appName}/config`, {
        method: 'POST',
        body: JSON.stringify({ key: newKey.trim(), value: newValue }),
      });
      setConfigs(data.configs || []);
      setNewKey('');
      setNewValue('');
      setIsAddConfigOpen(false);
    } catch (err: any) {
      alert(err.message || 'Failed to set config');
    }
  };

  const handleDeleteConfig = async (key: string) => {
    try {
      const data = await fetchApi<{ configs: AppConfig[] }>(`/apps/${appName}/config`, {
        method: 'DELETE',
        body: JSON.stringify({ key }),
      });
      setConfigs(data.configs || []);
    } catch (err: any) {
      alert(err.message || 'Failed to delete config');
    }
  };

  const handleDeleteApp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (confirmNameInput !== appName) {
      setDeleteError('App name confirmation does not match exact app name');
      return;
    }
    setDeleteLoading(true);
    setDeleteError('');

    try {
      await fetchApi(`/apps/${appName}`, {
        method: 'DELETE',
        body: JSON.stringify({ confirm_name: confirmNameInput }),
      });
      router.push('/dashboard');
      router.refresh();
    } catch (err: any) {
      setDeleteError(err.message || 'Failed to delete app');
      setDeleteLoading(false);
    }
  };

  const toggleKeyVisibility = (key: string) => {
    setVisibleKeys((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const copyText = (key: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const tabs = [
    { id: 'replicas', label: 'Replicas & Scale', icon: <Layers className="w-4 h-4" /> },
    { id: 'logs', label: 'Container Logs', icon: <Terminal className="w-4 h-4" /> },
    { id: 'deployments', label: 'Deployment History', icon: <History className="w-4 h-4" /> },
    { id: 'config', label: 'Environment Variables', icon: <Key className="w-4 h-4" /> },
    { id: 'danger', label: 'Danger Zone', icon: <Trash2 className="w-4 h-4 text-rose-400" /> },
  ];

  const domainUrl = `https://${appName}.dr0wn.duckdns.org`;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* App Header Bar */}
      <div className="glass-card rounded-xl p-6 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-extrabold text-slate-100">{appName}</h1>
            <Badge status={replicas.length > 0 ? 'running' : 'stopped'} />
          </div>
          <div className="flex flex-wrap items-center gap-4 mt-2 text-xs text-slate-400">
            <a
              href={domainUrl}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 text-indigo-400 hover:underline font-mono"
            >
              <Globe className="w-3.5 h-3.5" />
              {domainUrl}
              <ExternalLink className="w-3 h-3" />
            </a>
            <span className="text-slate-600">&bull;</span>
            <span className="font-mono">Git Remote: ssh://ubuntu@51.170.134.251/home/ubuntu/git-hook-test/{appName}.git</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="secondary" onClick={() => setIsScaleOpen(true)}>
            <Layers className="w-4 h-4" /> Scale Replicas ({replicas.length})
          </Button>
          <Button variant="danger" size="sm" onClick={() => setIsDeleteOpen(true)}>
            <Trash2 className="w-4 h-4" /> Delete
          </Button>
        </div>
      </div>

      {/* Tabs Switcher */}
      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {/* Tab 1: Replicas & Scale */}
      {activeTab === 'replicas' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <Activity className="w-5 h-5 text-indigo-400" />
              Active Replicas ({replicas.length})
            </h2>
            <Button size="sm" variant="secondary" onClick={loadMetrics} isLoading={replicasLoading}>
              <RefreshCw className="w-3.5 h-3.5" /> Refresh Metrics
            </Button>
          </div>

          {replicasLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {[1, 2].map((i) => (
                <div key={i} className="h-36 glass-card rounded-xl animate-pulse bg-slate-900/40" />
              ))}
            </div>
          ) : replicas.length === 0 ? (
            <Card className="text-center py-10">
              <p className="text-slate-400 text-sm">No active replicas running for this app.</p>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {replicas.map((rep) => (
                <Card key={rep.replica_num} className="border-slate-800">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-4">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-semibold text-slate-200">
                        Replica #{rep.replica_num}
                      </span>
                      <Badge status={rep.status || 'running'} />
                    </div>
                    <span className="font-mono text-xs text-slate-500">Port {rep.port}</span>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800 flex items-center gap-3">
                      <Cpu className="w-5 h-5 text-indigo-400 shrink-0" />
                      <div>
                        <p className="text-[11px] text-slate-400">CPU Usage</p>
                        <p className="font-mono text-sm font-bold text-slate-100">{rep.cpu || '0.0%'}</p>
                      </div>
                    </div>

                    <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800 flex items-center gap-3">
                      <HardDrive className="w-5 h-5 text-cyan-400 shrink-0" />
                      <div>
                        <p className="text-[11px] text-slate-400">Memory</p>
                        <p className="font-mono text-sm font-bold text-slate-100">{rep.memory || 'N/A'}</p>
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Logs */}
      {activeTab === 'logs' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <Terminal className="w-5 h-5 text-indigo-400" />
              Container stdout / stderr (Last 50 lines)
            </h2>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="secondary"
                onClick={() => copyText('logs', logs)}
              >
                {copiedKey === 'logs' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />} Copy Logs
              </Button>
              <Button size="sm" variant="secondary" onClick={loadLogs} isLoading={logsLoading}>
                <RefreshCw className="w-3.5 h-3.5" /> Refresh
              </Button>
            </div>
          </div>

          <div className="glass-card rounded-xl border border-slate-800 p-5 font-mono text-xs bg-slate-950 text-slate-300 leading-relaxed overflow-x-auto min-h-[350px]">
            {logsLoading ? (
              <div className="flex items-center justify-center h-48 text-slate-500">Loading container logs...</div>
            ) : (
              <pre className="whitespace-pre-wrap">{logs}</pre>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Deployment History */}
      {activeTab === 'deployments' && (
        <div className="space-y-4">
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <History className="w-5 h-5 text-indigo-400" />
            Deployment Feed
          </h2>

          {deploymentsLoading ? (
            <div className="space-y-3">
              {[1, 2].map((i) => (
                <div key={i} className="h-16 glass-card rounded-xl animate-pulse bg-slate-900/40" />
              ))}
            </div>
          ) : deployments.length === 0 ? (
            <Card className="text-center py-10">
              <p className="text-slate-400 text-sm">No deployment history recorded yet.</p>
            </Card>
          ) : (
            <div className="space-y-3">
              {deployments.map((dep, idx) => (
                <Card key={idx} className="flex items-center justify-between p-4 border-slate-800">
                  <div className="flex items-center gap-3">
                    <Badge status={dep.status} />
                    <span className="text-sm font-medium text-slate-200">{dep.message || 'Build completed'}</span>
                  </div>
                  <span className="font-mono text-xs text-slate-500">{dep.created_at}</span>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Environment Variables */}
      {activeTab === 'config' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <Key className="w-5 h-5 text-indigo-400" />
                Environment Configuration
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Keys are injected into container environment variables at runtime. Values are masked by default.
              </p>
            </div>
            <Button size="sm" onClick={() => setIsAddConfigOpen(true)}>
              <Plus className="w-4 h-4" /> Add Variable
            </Button>
          </div>

          {configsLoading ? (
            <div className="space-y-3">
              {[1, 2].map((i) => (
                <div key={i} className="h-16 glass-card rounded-xl animate-pulse bg-slate-900/40" />
              ))}
            </div>
          ) : configs.length === 0 ? (
            <Card className="text-center py-10">
              <p className="text-slate-400 text-sm">No custom environment variables set.</p>
            </Card>
          ) : (
            <div className="space-y-3">
              {configs.map((cfg) => {
                const isVisible = visibleKeys[cfg.key];
                return (
                  <Card key={cfg.key} className="flex items-center justify-between p-4 border-slate-800">
                    <div className="flex items-center gap-4 font-mono text-sm">
                      <span className="font-bold text-indigo-400">{cfg.key}</span>
                      <span className="text-slate-600">=</span>
                      <span className="text-slate-300">
                        {isVisible ? cfg.value : '••••••••••••••••'}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => toggleKeyVisibility(cfg.key)}
                        className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors"
                        title={isVisible ? 'Hide value' : 'Reveal value'}
                      >
                        {isVisible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                      <button
                        onClick={() => handleDeleteConfig(cfg.key)}
                        className="p-2 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                        title="Delete variable"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab 5: Danger Zone */}
      {activeTab === 'danger' && (
        <Card className="border-rose-500/30 bg-rose-500/5 p-6 space-y-4">
          <div>
            <h2 className="text-lg font-bold text-rose-400 flex items-center gap-2">
              <AlertCircle className="w-5 h-5" /> Delete Application
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Deleting an application stops all running Docker replicas, removes git repositories, and unlinks Caddy routing rules. This action cannot be undone.
            </p>
          </div>
          <Button variant="danger" onClick={() => setIsDeleteOpen(true)}>
            <Trash2 className="w-4 h-4" /> Permanently Delete {appName}
          </Button>
        </Card>
      )}

      {/* Scale Modal */}
      <Modal isOpen={isScaleOpen} onClose={() => setIsScaleOpen(false)} title="Scale Replicas">
        <div className="space-y-4">
          <p className="text-xs text-slate-400">
            Set the desired number of container replicas for <span className="font-mono text-indigo-400 font-bold">{appName}</span>.
          </p>
          <div className="flex items-center gap-4">
            <Input
              type="number"
              min={1}
              max={5}
              value={scalingCount}
              onChange={(e) => setScalingCount(parseInt(e.target.value) || 1)}
              label="Replica Count (1 - 5)"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" onClick={() => setIsScaleOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleScale} isLoading={scaleLoading}>
              Apply Scaling
            </Button>
          </div>
        </div>
      </Modal>

      {/* Add Config Modal */}
      <Modal isOpen={isAddConfigOpen} onClose={() => setIsAddConfigOpen(false)} title="Add Environment Variable">
        <form onSubmit={handleAddConfig} className="space-y-4">
          <Input
            label="Key"
            placeholder="e.g. DATABASE_URL"
            value={newKey}
            onChange={(e) => setNewKey(e.target.value)}
            required
          />
          <Input
            label="Value"
            placeholder="e.g. postgres://user:pass@host/db"
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={() => setIsAddConfigOpen(false)}>
              Cancel
            </Button>
            <Button type="submit">Save Variable</Button>
          </div>
        </form>
      </Modal>

      {/* GitHub-Style Delete App Modal */}
      <Modal isOpen={isDeleteOpen} onClose={() => setIsDeleteOpen(false)} title="Delete Application Confirmation">
        <form onSubmit={handleDeleteApp} className="space-y-4">
          {deleteError && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{deleteError}</span>
            </div>
          )}

          <p className="text-xs text-slate-300">
            This action <span className="font-bold text-rose-400">CANNOT</span> be undone. Please type{' '}
            <span className="font-mono bg-slate-900 px-1.5 py-0.5 rounded text-indigo-400 font-bold">{appName}</span> to confirm.
          </p>

          <Input
            placeholder="Type app name to confirm"
            value={confirmNameInput}
            onChange={(e) => setConfirmNameInput(e.target.value)}
            required
          />

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={() => setIsDeleteOpen(false)}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="danger"
              isLoading={deleteLoading}
              disabled={confirmNameInput !== appName}
            >
              I understand the consequences, delete app
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
