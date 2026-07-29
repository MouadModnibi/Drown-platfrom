'use client';

import React from 'react';
import { Terminal, Shield, GitCommit } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="w-full border-t border-slate-800/80 bg-slate-950/40 py-8 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-slate-500">
        <div className="flex items-center gap-2 font-mono">
          <Terminal className="w-4 h-4 text-indigo-400" />
          <span>mini-heroku Platform v2.0 &bull; Developer Cloud Engine</span>
        </div>
        <div className="flex items-center gap-6">
          <span className="flex items-center gap-1.5">
            <Shield className="w-3.5 h-3.5 text-emerald-400" /> Caddy SSL Auto-Proxy
          </span>
          <span className="flex items-center gap-1.5">
            <GitCommit className="w-3.5 h-3.5 text-cyan-400" /> Heroku Buildpack v24
          </span>
        </div>
      </div>
    </footer>
  );
};
