'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Shield, Users, Box, Trash2, Globe, AlertCircle, RefreshCw, Layers, ScrollText } from 'lucide-react';
import { fetchApi, AdminApp } from '@/lib/api-client';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';

export default function AdminDashboardPage() {
  const [apps, setApps] = useState<AdminApp[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Delete App Modal state
  const [selectedApp, setSelectedApp] = useState<string | null>(null);
  const [confirmNameInput, setConfirmNameInput] = useState('');
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  const loadAdminApps = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await fetchApi<{ apps: AdminApp[] }>('/admin/apps');
      setApps(data.apps || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load admin applications');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAdminApps();
  }, []);

  const handleDeleteApp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedApp) return;
    if (confirmNameInput !== selectedApp) {
      setDeleteError('App name confirmation does not match');
      return;
    }

    setDeleteLoading(true);
    setDeleteError('');

    try {
      await fetchApi(`/apps/${selectedApp}`, {
        method: 'DELETE',
        body: JSON.stringify({ confirm_name: confirmNameInput }),
      });
      setSelectedApp(null);
      setConfirmNameInput('');
      loadAdminApps();
    } catch (err: any) {
      setDeleteError(err.message || 'Failed to delete app');
    } finally {
      setDeleteLoading(false);
    }
  };

  // Group apps by owner username
  const appsByUser = apps.reduce((acc, app) => {
    const owner = app.owner_username || 'Unassigned';
    if (!acc[owner]) acc[owner] = [];
    acc[owner].push(app);
    return acc;
  }, {} as Record<string, AdminApp[]>);

  const totalUsers = Object.keys(appsByUser).length;
  const totalApps = apps.length;
  const totalReplicas = apps.reduce((sum, a) => sum + (a.replica_count || 0), 0);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-100">Global Admin Dashboard</h1>
            <span className="text-xs bg-indigo-500/20 text-indigo-400 px-2 py-0.5 rounded font-semibold border border-indigo-500/30 flex items-center gap-1">
              <Shield className="w-3 h-3" /> System Admin
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Platform-wide management across all registered users and applications
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/admin/audit-log">
            <Button variant="secondary">
              <ScrollText className="w-4 h-4" /> Audit Log
            </Button>
          </Link>
          <Button variant="secondary" onClick={loadAdminApps} isLoading={loading}>
            <RefreshCw className="w-4 h-4" /> Refresh Global List
          </Button>
        </div>
      </div>

      {/* Global Overview Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <Card className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-slate-400 font-medium">Platform Users</p>
            <h3 className="text-2xl font-extrabold text-slate-100 mt-0.5">{totalUsers}</h3>
          </div>
        </Card>

        <Card className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 shrink-0">
            <Box className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-slate-400 font-medium">Total Platform Apps</p>
            <h3 className="text-2xl font-extrabold text-slate-100 mt-0.5">{totalApps}</h3>
          </div>
        </Card>

        <Card className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shrink-0">
            <Layers className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-slate-400 font-medium">Active Replicas</p>
            <h3 className="text-2xl font-extrabold text-slate-100 mt-0.5">{totalReplicas}</h3>
          </div>
        </Card>
      </div>

      {/* Error state */}
      {error && (
        <Card className="border-rose-500/30 bg-rose-500/10 p-4 text-rose-400 text-sm flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </Card>
      )}

      {/* Grouped User Applications */}
      {loading ? (
        <div className="space-y-6">
          {[1, 2].map((i) => (
            <div key={i} className="h-48 glass-card rounded-xl animate-pulse bg-slate-900/40" />
          ))}
        </div>
      ) : Object.keys(appsByUser).length === 0 ? (
        <Card className="text-center py-12">
          <Box className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-200">No user applications deployed yet</h3>
        </Card>
      ) : (
        <div className="space-y-8">
          {Object.entries(appsByUser).map(([username, userApps]) => (
            <div key={username} className="space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <span className="w-7 h-7 rounded-lg bg-indigo-600/20 text-indigo-400 flex items-center justify-center text-xs font-bold font-mono">
                    {username[0].toUpperCase()}
                  </span>
                  <h2 className="text-lg font-bold text-slate-100">{username}</h2>
                  <span className="text-xs text-slate-500 font-mono">
                    ({userApps.length} {userApps.length === 1 ? 'app' : 'apps'})
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {userApps.map((app) => (
                  <Card key={app.name} className="border-slate-800 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-3">
                        <Link href={`/apps/${app.name}`}>
                          <h3 className="text-base font-bold text-slate-100 hover:text-indigo-400 transition-colors">
                            {app.name}
                          </h3>
                        </Link>
                        <Badge status={app.status} />
                      </div>

                      <p className="text-xs font-mono text-slate-400 break-all flex items-center gap-1">
                        <Globe className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                        https://{app.domain}
                      </p>
                    </div>

                    <div className="mt-5 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
                      <div className="flex items-center gap-1.5">
                        <Layers className="w-3.5 h-3.5 text-indigo-400" />
                        <span>{app.replica_count} {app.replica_count === 1 ? 'replica' : 'replicas'}</span>
                      </div>

                      <button
                        onClick={() => {
                          setSelectedApp(app.name);
                          setConfirmNameInput('');
                          setDeleteError('');
                        }}
                        className="flex items-center gap-1 px-2.5 py-1 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 hover:bg-rose-500/20 transition-colors text-xs font-medium"
                      >
                        <Trash2 className="w-3 h-3" /> Admin Delete
                      </button>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Admin Delete Confirmation Modal */}
      <Modal
        isOpen={Boolean(selectedApp)}
        onClose={() => setSelectedApp(null)}
        title="Admin App Deletion Confirmation"
      >
        <form onSubmit={handleDeleteApp} className="space-y-4">
          {deleteError && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{deleteError}</span>
            </div>
          )}

          <p className="text-xs text-slate-300">
            As an administrator, you are deleting application{' '}
            <span className="font-mono bg-slate-900 px-1.5 py-0.5 rounded text-indigo-400 font-bold">
              {selectedApp}
            </span>
            . Please type the exact app name to confirm deletion.
          </p>

          <Input
            placeholder="Type app name to confirm"
            value={confirmNameInput}
            onChange={(e) => setConfirmNameInput(e.target.value)}
            required
          />

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={() => setSelectedApp(null)}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="danger"
              isLoading={deleteLoading}
              disabled={confirmNameInput !== selectedApp}
            >
              Confirm Admin Delete
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
