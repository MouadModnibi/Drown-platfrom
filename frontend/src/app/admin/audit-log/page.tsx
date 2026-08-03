'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  ScrollText,
  ArrowLeft,
  RefreshCw,
  AlertCircle,
  Filter,
} from 'lucide-react';
import { fetchApi } from '@/lib/api-client';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface AuditEntry {
  id: number;
  user_id: number | null;
  username: string | null;
  action: string;
  target: string | null;
  details: string | null;
  ip_address: string | null;
  created_at: string;
}

// Map action names to badge colours
const ACTION_STYLES: Record<string, string> = {
  login:            'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  login_failed:     'bg-rose-500/10 text-rose-400 border-rose-500/20',
  logout:           'bg-slate-800/80 text-slate-400 border-slate-700/60',
  app_create:       'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
  app_delete:       'bg-rose-500/15 text-rose-300 border-rose-500/30',
  app_scale:        'bg-violet-500/10 text-violet-400 border-violet-500/20',
  config_set:       'bg-amber-500/10 text-amber-400 border-amber-500/20',
  config_unset:     'bg-amber-500/10 text-amber-400 border-amber-500/20',
  password_change:  'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
  username_change:  'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
  ssh_key_register: 'bg-violet-500/10 text-violet-400 border-violet-500/20',
};

function ActionBadge({ action }: { action: string }) {
  const cls = ACTION_STYLES[action] ?? 'bg-slate-800 text-slate-400 border-slate-700';
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-semibold border ${cls} whitespace-nowrap`}>
      {action}
    </span>
  );
}

const LIMIT_OPTIONS = [50, 100, 200, 500];

export default function AuditLogPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [limit, setLimit] = useState(100);
  const [actionTypes, setActionTypes] = useState<string[]>([]);

  const load = async (action?: string, lim?: number) => {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams();
      if (action) params.set('action', action);
      params.set('limit', String(lim ?? limit));
      const data = await fetchApi<{ entries: AuditEntry[] }>(
        `/admin/audit-log?${params.toString()}`
      );
      const fetched = data.entries || [];
      setEntries(fetched);
      // Build action type list from all entries on first full load
      if (!action) {
        const types = [...new Set(fetched.map((e) => e.action))].sort();
        setActionTypes(types);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load audit log');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleApply = () => load(actionFilter || undefined, limit);

  const handleClear = () => {
    setActionFilter('');
    load(undefined, limit);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <Link
            href="/admin"
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 mb-3 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Admin Dashboard
          </Link>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-100">Audit Log</h1>
            <span className="text-xs bg-indigo-500/20 text-indigo-400 px-2 py-0.5 rounded font-semibold border border-indigo-500/30 flex items-center gap-1">
              <ScrollText className="w-3 h-3" /> Admin Only
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Platform-wide action history — all users, all events
          </p>
        </div>
        <Button variant="secondary" onClick={() => load(actionFilter || undefined, limit)} isLoading={loading}>
          <RefreshCw className="w-4 h-4" /> Refresh
        </Button>
      </div>

      {/* Filter bar */}
      <Card className="p-4 flex flex-wrap items-end gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide flex items-center gap-1">
            <Filter className="w-3 h-3" /> Action type
          </label>
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 min-w-[180px]"
          >
            <option value="">All actions</option>
            {actionTypes.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide">
            Row limit
          </label>
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            {LIMIT_OPTIONS.map((l) => (
              <option key={l} value={l}>{l} rows</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2 pb-0.5">
          <Button size="sm" onClick={handleApply} isLoading={loading}>
            Apply
          </Button>
          {actionFilter && (
            <Button size="sm" variant="ghost" onClick={handleClear}>
              Clear filter
            </Button>
          )}
        </div>

        {/* Colour legend */}
        <div className="flex flex-wrap gap-1.5 ml-auto">
          {Object.entries(ACTION_STYLES).map(([action, cls]) => (
            <span
              key={action}
              className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono border ${cls}`}
            >
              {action}
            </span>
          ))}
        </div>
      </Card>

      {/* Error */}
      {error && (
        <Card className="border-rose-500/30 bg-rose-500/10 p-4 text-rose-400 text-sm flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </Card>
      )}

      {/* Table */}
      {loading ? (
        <div className="space-y-2">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-12 glass-card rounded-lg animate-pulse bg-slate-900/40" />
          ))}
        </div>
      ) : entries.length === 0 ? (
        <Card className="text-center py-12">
          <ScrollText className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-200">No audit entries found</h3>
          <p className="text-xs text-slate-400 mt-1">
            {actionFilter ? `No events matching action "${actionFilter}".` : 'No events have been recorded yet.'}
          </p>
        </Card>
      ) : (
        <>
          <div className="glass-card rounded-xl border border-slate-800 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-900/60">
                    <th className="text-left px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wider w-12">#</th>
                    <th className="text-left px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wider whitespace-nowrap">Timestamp</th>
                    <th className="text-left px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">User</th>
                    <th className="text-left px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Action</th>
                    <th className="text-left px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Target</th>
                    <th className="text-left px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Details</th>
                    <th className="text-left px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">IP</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {entries.map((e) => (
                    <tr key={e.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="px-4 py-3 font-mono text-xs text-slate-600">{e.id}</td>
                      <td className="px-4 py-3 font-mono text-xs text-slate-400 whitespace-nowrap">{e.created_at}</td>
                      <td className="px-4 py-3">
                        {e.username ? (
                          <span className="font-semibold text-indigo-400 text-xs font-mono">
                            {e.username}
                            {e.user_id && (
                              <span className="text-slate-600 ml-1 font-normal">#{e.user_id}</span>
                            )}
                          </span>
                        ) : (
                          <span className="text-slate-600 text-xs">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <ActionBadge action={e.action} />
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-slate-300">
                        {e.target || <span className="text-slate-600">—</span>}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-400 max-w-xs truncate" title={e.details ?? ''}>
                        {e.details || <span className="text-slate-600">—</span>}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-slate-500">
                        {e.ip_address || <span className="text-slate-600">—</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <p className="text-xs text-slate-500 text-right">
            Showing {entries.length} most recent entries
            {actionFilter && <> filtered to <span className="text-slate-300 font-mono">{actionFilter}</span></>}
          </p>
        </>
      )}
    </div>
  );
}
