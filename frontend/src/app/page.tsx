'use client';

import React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Terminal, Cpu, ShieldCheck, Zap, ArrowRight, Layers, Lock, Activity } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

export default function LandingPage() {
  return (
    <div className="relative overflow-hidden bg-slate-950 text-slate-100 min-h-[calc(100vh-4rem)] flex flex-col justify-between">
      {/* Glow Effects */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-indigo-600/15 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute top-3/4 left-1/3 w-[400px] h-[300px] bg-cyan-600/10 blur-[100px] rounded-full pointer-events-none" />

      {/* Hero Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 pb-20 relative z-10">
        <div className="text-center space-y-6 max-w-3xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-mono"
          >
            <Zap className="w-3.5 h-3.5 text-indigo-400" />
            Next-Gen Developer Application Cloud
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-tight"
          >
            Push code.{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-cyan-400 to-emerald-400">
              Instant deployment.
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-lg text-slate-400 max-w-2xl mx-auto leading-relaxed"
          >
            Mini-Heroku builds and orchestrates your applications with Heroku Buildpacks,
            Docker container scaling, automated Caddy SSL proxying, and real-time metrics.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4"
          >
            <Link href="/register">
              <Button size="lg" className="w-full sm:w-auto font-semibold">
                Get Started Free <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </Link>
            <Link href="/login">
              <Button size="lg" variant="secondary" className="w-full sm:w-auto">
                Sign In to Console
              </Button>
            </Link>
          </motion.div>
        </div>

        {/* Live Terminal Preview Component */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="mt-14 max-w-4xl mx-auto glass-card rounded-xl border border-slate-800 shadow-2xl overflow-hidden"
        >
          <div className="bg-slate-900 px-4 py-3 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-rose-500/80" />
              <div className="w-3 h-3 rounded-full bg-amber-500/80" />
              <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
              <span className="text-xs font-mono text-slate-400 ml-2">bash &mdash; git push platform main</span>
            </div>
            <span className="text-xs font-mono text-slate-500">heroku/builder:24</span>
          </div>
          <div className="bg-slate-950 p-6 font-mono text-xs text-slate-300 space-y-2 leading-relaxed overflow-x-auto">
            <p className="text-slate-500">$ git remote add platform ssh://ubuntu@drown-platform/git/my-api.git</p>
            <p className="text-slate-300">$ git push platform main</p>
            <p className="text-indigo-400">----&gt; Detecting buildpack... Node.js App detected</p>
            <p className="text-indigo-400">----&gt; Building container via Cloud Native Buildpack v24</p>
            <p className="text-slate-400">&nbsp;&nbsp;&nbsp;&nbsp; Running npm install &amp; building assets...</p>
            <p className="text-emerald-400">----&gt; Build succeed! Container created ID: 7f3a8b1c9</p>
            <p className="text-cyan-400">----&gt; Registering Caddy HTTPS proxy endpoint...</p>
            <p className="text-emerald-400 font-semibold pt-1">
              &gt; App live at: <span className="underline">https://my-api.dr0wn.duckdns.org</span> [Status: 200 OK]
            </p>
          </div>
        </motion.div>

        {/* Feature Grid */}
        <div className="mt-20 grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card hoverGlow>
            <div className="w-10 h-10 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-4">
              <Terminal className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-slate-100 mb-2">Automated Git Deploys</h3>
            <p className="text-sm text-slate-400">
              Deploy your Node.js, Python, or Go app by pushing to git. Automated post-receive hooks build and launch your containers.
            </p>
          </Card>

          <Card hoverGlow>
            <div className="w-10 h-10 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 mb-4">
              <Layers className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-slate-100 mb-2">Dynamic Multi-Replica Scaling</h3>
            <p className="text-sm text-slate-400">
              Scale replica count up or down instantly. Container ports are allocated and load-balanced automatically.
            </p>
          </Card>

          <Card hoverGlow>
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mb-4">
              <Activity className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-slate-100 mb-2">Live Metrics &amp; Container Logs</h3>
            <p className="text-sm text-slate-400">
              Monitor real-time CPU % and memory footprint per replica. Inspect container logs with live streaming.
            </p>
          </Card>
        </div>
      </div>
    </div>
  );
}
