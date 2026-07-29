'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Server, Sun, Moon, LogOut, User, Shield, HelpCircle, LayoutDashboard } from 'lucide-react';
import { useTheme } from '@/lib/theme-context';
import { fetchApi, ApiUser } from '@/lib/api-client';

export const Navbar: React.FC = () => {
  const pathname = usePathname();
  const router = useRouter();
  const { theme, toggleTheme } = useTheme();
  const [user, setUser] = useState<ApiUser | null>(null);

  useEffect(() => {
    // Check if user is logged in
    fetchApi<{ user: ApiUser }>('/auth/me')
      .then((data) => setUser(data.user))
      .catch(() => setUser(null));
  }, [pathname]);

  const handleLogout = async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
      setUser(null);
      router.push('/login');
    } catch (err) {
      console.error('Logout error:', err);
    }
  };

  const navLinks = [
    { href: '/dashboard', label: 'Dashboard', icon: <LayoutDashboard className="w-4 h-4" /> },
    { href: '/help', label: 'Docs & Help', icon: <HelpCircle className="w-4 h-4" /> },
  ];

  if (user?.is_admin) {
    navLinks.push({ href: '/admin', label: 'Admin', icon: <Shield className="w-4 h-4 text-indigo-400" /> });
  }

  return (
    <header className="sticky top-0 z-40 w-full glass-nav border-b border-slate-800/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo */}
        <Link href={user ? '/dashboard' : '/'} className="flex items-center gap-2.5 group">
          <div className="w-9 h-9 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 group-hover:bg-indigo-600/30 transition-all">
            <Server className="w-5 h-5" />
          </div>
          <div className="flex flex-col">
            <span className="font-bold text-base tracking-tight text-slate-100 flex items-center gap-1.5">
              mini-heroku
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-mono">v2.0</span>
            </span>
          </div>
        </Link>

        {/* Navigation Links */}
        {user && (
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => {
              const isActive = pathname.startsWith(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-slate-800/80 text-indigo-400 border border-slate-700/80'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                  }`}
                >
                  {link.icon}
                  {link.label}
                </Link>
              );
            })}
          </nav>
        )}

        {/* Right Section Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent hover:border-slate-700/60 transition-all"
            title="Toggle theme"
          >
            {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-700" />}
          </button>

          {user ? (
            <div className="flex items-center gap-3 pl-3 border-l border-slate-800">
              <Link
                href="/profile"
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-200 text-sm transition-all"
              >
                <User className="w-4 h-4 text-indigo-400" />
                <span className="font-mono text-xs">{user.username}</span>
                {user.is_admin && (
                  <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-1.5 py-0.5 rounded font-semibold">
                    ADMIN
                  </span>
                )}
              </Link>

              <button
                onClick={handleLogout}
                className="p-2 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                title="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                href="/login"
                className="px-3.5 py-2 text-sm font-medium text-slate-300 hover:text-white transition-colors"
              >
                Log in
              </Link>
              <Link
                href="/register"
                className="px-4 py-2 text-sm font-medium bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg shadow-lg shadow-indigo-500/20 transition-all"
              >
                Get Started
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
