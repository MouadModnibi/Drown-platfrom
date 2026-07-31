'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  Plus,
  Search,
  Box,
  Layers,
  Globe,
  ArrowUpRight,
  RefreshCw,
  Terminal,
  Copy,
  Check,
  AlertCircle,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { fetchApi, ApiApp } from '@/lib/api-client';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';

// Individual copy button that tracks its own copied state
function CopyButton({ text, className = '' }: { text: string; className?: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={handleCopy}
      className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800 border border-slate-700 hover:border-slate-600 text-slate-400 hover:text-slate-200 transition-all text-xs font-medium ${className}`}
      title="Copy to clipboard"
    >
      {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
      {copied ? 'Copied!' : 'Copy'}
    </button>
  );
}

// Code block with inline copy button
function CodeBlock({ code, label }: { code: string; label?: string }) {
  return (
    <div className="space-y-1">
      {label && <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wide">{label}</p>}
      <div className="flex items-start gap-2">
        <pre className="flex-1 bg-slate-950 border border-slate-800 rounded-lg p-3 font-mono text-xs text-indigo-300 overflow-x-auto whitespace-pre-wrap break-all">
          {code}
        </pre>
        <CopyButton text={code} className="shrink-0 mt-0.5" />
      </div>
    </div>
  );
}

// Numbered step wrapper
function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-3">
      <div className="shrink-0 w-7 h-7 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 text-xs font-bold flex items-center justify-center mt-0.5">
        {n}
      </div>
      <div className="flex-1 space-y-2 min-w-0">
        <p className="text-sm font-semibold text-slate-200">{title}</p>
        {children}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [apps, setApps] = useState<ApiApp[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newAppName, setNewAppName] = useState('');
  const [createError, setCreateError] = useState('');
  const [createLoading, setCreateLoading] = useState(false);
  const [createdResult, setCreatedResult] = useState<{
    app: string;
    domain: string;
    git_remote: string;
    push_instructions: string;
  } | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const loadApps = async () => {
    setLoading(true);
    try {
      const data = await fetchApi<{ apps: ApiApp[] }>('/apps');
      setApps(data.apps || []);
    } catch (err: any) {
      console.error('Failed to load apps:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApps();
  }, []);

  const handleCreateApp = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError('');
    setCreateLoading(true);

    try {
      const res = await fetchApi<{
        app: string;
        domain: string;
        git_remote: string;
        push_instructions: string;
      }>('/apps/create', {
        method: 'POST',
        body: JSON.stringify({ name: newAppName.trim().toLowerCase() }),
      });

      setCreatedResult(res);
      loadApps();
    } catch (err: any) {
      setCreateError(err.message || 'Failed to create app');
    } finally {
      setCreateLoading(false);
    }
  };

  const filteredApps = apps.filter(
    (app) =>
      app.name.toLowerCase().includes(search.toLowerCase()) ||
      app.domain.toLowerCase().includes(search.toLowerCase())
  );

  const totalReplicas = apps.reduce((acc, a) => acc + (a.replicas || 0), 0);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header & Main Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Apps Dashboard</h1>
          <p className="text-sm text-slate-400 mt-1">
            Manage, scale, and monitor your deployed applications
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="secondary" onClick={loadApps} isLoading={loading}>
            <RefreshCw className="w-4 h-4" /> Refresh
          </Button>
          <Button
            onClick={() => {
              setCreatedResult(null);
              setNewAppName('');
              setCreateError('');
              setShowAdvanced(false);
              setIsCreateOpen(true);
            }}
          >
            <Plus className="w-4 h-4" /> Deploy New App
          </Button>
        </div>
      </div>

      {/* Stats Summary Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <Card className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0">
            <Box className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-slate-400 font-medium">Total Apps</p>
            <h3 className="text-2xl font-extrabold text-slate-100 mt-0.5">{apps.length}</h3>
          </div>
        </Card>

        <Card className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 shrink-0">
            <Layers className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-slate-400 font-medium">Active Replicas</p>
            <h3 className="text-2xl font-extrabold text-slate-100 mt-0.5">{totalReplicas}</h3>
          </div>
        </Card>

        <Card className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shrink-0">
            <Globe className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-slate-400 font-medium">Global Proxy</p>
            <h3 className="text-sm font-semibold text-emerald-400 mt-1 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Caddy SSL Healthy
            </h3>
          </div>
        </Card>
      </div>

      {/* Search & Filter Bar */}
      <div className="flex items-center justify-between gap-4">
        <div className="w-full sm:max-w-xs">
          <Input
            placeholder="Search apps..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            icon={<Search className="w-4 h-4" />}
          />
        </div>
      </div>

      {/* Apps Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-44 glass-card rounded-xl animate-pulse bg-slate-900/40" />
          ))}
        </div>
      ) : filteredApps.length === 0 ? (
        <Card className="text-center py-12">
          <Box className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-200">No applications found</h3>
          <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
            {search ? 'No apps match your search query.' : 'Create your first app to start deploying containers.'}
          </p>
          {!search && (
            <Button
              onClick={() => setIsCreateOpen(true)}
              className="mt-4"
              size="sm"
            >
              <Plus className="w-4 h-4" /> Create App Now
            </Button>
          )}
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredApps.map((app) => (
            <Link key={app.name} href={`/apps/${app.name}`}>
              <Card hoverGlow className="h-full flex flex-col justify-between group cursor-pointer">
                <div>
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <h3 className="text-lg font-bold text-slate-100 group-hover:text-indigo-400 transition-colors flex items-center gap-1.5">
                      {app.name}
                      <ArrowUpRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity text-indigo-400" />
                    </h3>
                    <Badge status={app.status} />
                  </div>

                  <p className="text-xs font-mono text-slate-400 break-all flex items-center gap-1">
                    <Globe className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                    https://{app.domain}
                  </p>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
                  <div className="flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-indigo-400" />
                    <span>{app.replicas} {app.replicas === 1 ? 'replica' : 'replicas'}</span>
                  </div>
                  <span className="text-indigo-400 group-hover:translate-x-0.5 transition-transform font-medium">
                    View Details &rarr;
                  </span>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}

      {/* Create App Modal */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title={createdResult ? 'App Provisioned Successfully!' : 'Create New Application'}
      >
        {createdResult ? (
          <div className="space-y-5">
            {/* Success banner */}
            <div className="p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
              <Check className="w-4 h-4 shrink-0" />
              <span>
                <span className="font-semibold">{createdResult.app}</span> provisioned at{' '}
                <span className="font-mono">https://{createdResult.domain}</span>
              </span>
            </div>

            {/* CLI onboarding steps */}
            <div className="space-y-5">
              <Step n={1} title="Install the Drown CLI (if not already)">
                <CodeBlock code="pip install drown" />
              </Step>

              <Step n={2} title="Log in to Drown">
                <CodeBlock code="drown login" />
              </Step>

              <Step n={3} title="Set up your project (if not already a git repo)">
                <CodeBlock code={`cd your-project/\ngit init`} />
              </Step>

              <Step n={4} title={`Connect this app`}>
                <CodeBlock code={`drown create ${createdResult.app}`} />
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  Already created via the dashboard — this command links your local repo to the existing app.
                </p>
              </Step>

              <Step n={5} title="Deploy">
                <CodeBlock code={`git add .\ngit commit -m "Initial commit"\ngit push platform main`} />
              </Step>
            </div>

            {/* Advanced / manual setup toggle */}
            <div className="border-t border-slate-800 pt-3">
              <button
                onClick={() => setShowAdvanced((v) => !v)}
                className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
              >
                {showAdvanced
                  ? <ChevronUp className="w-3.5 h-3.5" />
                  : <ChevronDown className="w-3.5 h-3.5" />}
                Advanced: manual git remote setup
              </button>

              {showAdvanced && (
                <div className="mt-3 space-y-3 pl-1">
                  <CodeBlock label="Git remote URL" code={createdResult.git_remote} />
                  <CodeBlock label="Manual push command" code={createdResult.push_instructions} />
                </div>
              )}
            </div>

            <div className="flex justify-end pt-1">
              <Link href={`/apps/${createdResult.app}`}>
                <Button onClick={() => setIsCreateOpen(false)}>
                  Go to App Dashboard &rarr;
                </Button>
              </Link>
            </div>
          </div>
        ) : (
          <form onSubmit={handleCreateApp} className="space-y-4">
            {createError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{createError}</span>
              </div>
            )}

            <Input
              label="App Name"
              placeholder="e.g. my-api"
              value={newAppName}
              onChange={(e) => setNewAppName(e.target.value)}
              icon={<Terminal className="w-4 h-4" />}
              required
            />
            <p className="text-[11px] text-slate-500">
              Only lowercase letters, numbers, and hyphens (3-30 characters).
            </p>

            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="ghost" onClick={() => setIsCreateOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" isLoading={createLoading}>
                Provision App
              </Button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
