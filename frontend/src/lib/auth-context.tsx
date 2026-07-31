'use client';

/**
 * AuthContext — single source of truth for the logged-in user.
 *
 * Why this exists:
 * - Previously, user state lived only in Navbar's local useState. That meant
 *   logout could clear the Navbar's state, but any other component (or the
 *   Navbar's own useEffect re-running on the next pathname change) could
 *   immediately re-fetch /auth/me and set the user back, creating a race.
 * - Now one context owns the user. Components read from it; logout clears it
 *   atomically before the hard-redirect, so there's no window where a
 *   concurrent useEffect can restore stale state.
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';

export interface AuthUser {
  id: number;
  username: string;
  is_admin: boolean;
}

interface AuthContextType {
  user: AuthUser | null;
  /** true while the initial /auth/me check is in flight */
  loading: boolean;
  /** Call after a successful login to populate the context without a refetch */
  setUser: (user: AuthUser | null) => void;
  /** Clears cookie via API, clears context, then does a hard redirect to /login */
  logout: () => Promise<void>;
  /** Re-fetch /auth/me from the server */
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      // Hit the dedicated /api/auth/me Next.js route (reads httpOnly cookie
      // server-side and calls Flask) — NOT the generic proxy.
      const res = await fetch('/api/auth/me', { method: 'GET' });
      if (!res.ok) {
        setUser(null);
        return;
      }
      const data = await res.json();
      setUser(data.user ?? null);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // Run once on mount — establishes initial auth state
  useEffect(() => {
    refresh();
  }, [refresh]);

  const logout = useCallback(async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
    } catch {
      // Even if the network call fails, clear the local state and redirect.
      // The next request to any protected route will bounce off middleware.
    } finally {
      // Clear local state first so nothing re-reads stale user
      setUser(null);
      // Hard navigation — forces a real HTTP request so middleware evaluates
      // the cleared cookie on a fresh request cycle. No client-router race.
      window.location.href = '/login';
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, setUser, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside <AuthProvider>');
  }
  return ctx;
}
