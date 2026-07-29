'use client';

import React from 'react';
import { clsx } from 'clsx';

interface BadgeProps {
  status: 'running' | 'building' | 'stopped' | 'success' | 'failed' | string;
  label?: string;
  pulse?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({ status, label, pulse = true }) => {
  const normStatus = status.toLowerCase();

  const isRunning = normStatus === 'running' || normStatus === 'success';
  const isBuilding = normStatus === 'building' || normStatus === 'pending';
  const isStopped = normStatus === 'stopped' || normStatus === 'failed';

  const badgeStyles = clsx(
    'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium uppercase tracking-wider border',
    isRunning && 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    isBuilding && 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    isStopped && 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    !isRunning && !isBuilding && !isStopped && 'bg-slate-800 text-slate-300 border-slate-700'
  );

  const dotStyles = clsx(
    'w-1.5 h-1.5 rounded-full',
    isRunning && 'bg-emerald-400',
    isBuilding && 'bg-amber-400 animate-pulse',
    isStopped && 'bg-rose-400',
    !isRunning && !isBuilding && !isStopped && 'bg-slate-400'
  );

  return (
    <span className={badgeStyles}>
      <span className={clsx(dotStyles, isRunning && pulse && 'status-pulse-running')} />
      {label || status}
    </span>
  );
};
