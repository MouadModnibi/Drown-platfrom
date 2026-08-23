'use client';

import React, { useState, Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { Server, Lock, User, AlertCircle } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { useAuth } from '@/lib/auth-context';

export const dynamic = 'force-dynamic';

function LoginForm() {
  const searchParams = useSearchParams();
  const next = searchParams.get('next') || '/dashboard';
  const { setUser } = useAuth();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.error || 'Invalid credentials');
        setLoading(false);
        return;
      }

      // Populate the auth context immediately so the Navbar reflects the
      // logged-in state as soon as we arrive on the dashboard — no extra
      // round-trip to /auth/me needed.
      setUser({ id: data.id ?? 0, username: data.username, is_admin: data.is_admin ?? false });

      // Hard navigation so the middleware re-evaluates the freshly-set cookie
      // on a real HTTP request. This also clears any stale React state from
      // previous sessions (including the loading flag on this form).
      window.location.href = next;
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred');
      setLoading(false);
    }
  };

  return (
    <Card className="p-8 border-slate-800 shadow-2xl">
      <div className="text-center mb-8">
        <div className="w-12 h-12 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 mx-auto mb-3">
          <Server className="w-6 h-6" />
        </div>
        <h2 className="text-2xl font-bold text-slate-100">Welcome Back</h2>
        <p className="text-sm text-slate-400 mt-1">Sign in to your Drown console</p>
      </div>

      {error && (
        <motion.div
          initial={{ opacity: 0, y: -5 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-5 p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm flex items-center gap-2.5"
        >
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </motion.div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Username"
          type="text"
          placeholder="Enter your username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          icon={<User className="w-4 h-4" />}
          required
        />

        <Input
          label="Password"
          type="password"
          placeholder="••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          icon={<Lock className="w-4 h-4" />}
          required
        />

        <Button type="submit" isLoading={loading} className="w-full mt-2">
          Sign In
        </Button>
      </form>

      <div className="mt-6 text-center text-xs text-slate-400">
        Don&apos;t have an account yet?{' '}
        <Link href="/register" className="text-indigo-400 hover:underline font-medium">
          Create one
        </Link>
      </div>
    </Card>
  );
}

export default function LoginPage() {
  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center p-4 relative">
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[300px] bg-indigo-600/10 blur-[100px] rounded-full pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
        className="w-full max-w-md relative z-10"
      >
        <Suspense fallback={<div className="text-slate-400 text-center py-10">Loading...</div>}>
          <LoginForm />
        </Suspense>
      </motion.div>
    </div>
  );
}
