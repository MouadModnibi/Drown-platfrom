'use client';

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { User, Lock, Check, AlertCircle, ShieldCheck } from 'lucide-react';
import { fetchApi, ApiUser } from '@/lib/api-client';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Tabs } from '@/components/ui/Tabs';

export default function ProfilePage() {
  const [user, setUser] = useState<ApiUser | null>(null);
  const [activeTab, setActiveTab] = useState('username');

  // Username form
  const [newUsername, setNewUsername] = useState('');
  const [userLoading, setUserLoading] = useState(false);
  const [userSuccess, setUserSuccess] = useState('');
  const [userError, setUserError] = useState('');

  // Password form
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passLoading, setPassLoading] = useState(false);
  const [passSuccess, setPassSuccess] = useState('');
  const [passError, setPassError] = useState('');

  const loadUser = async () => {
    try {
      const data = await fetchApi<{ user: ApiUser }>('/auth/me');
      setUser(data.user);
      setNewUsername(data.user.username);
    } catch (err: any) {
      console.error('Failed to load profile:', err);
    }
  };

  useEffect(() => {
    loadUser();
  }, []);

  const handleUpdateUsername = async (e: React.FormEvent) => {
    e.preventDefault();
    setUserSuccess('');
    setUserError('');

    if (newUsername.trim().length < 3) {
      setUserError('Username must be at least 3 characters');
      return;
    }

    setUserLoading(true);

    try {
      const data = await fetchApi<{ message: string; username: string }>('/user/profile', {
        method: 'PUT',
        body: JSON.stringify({ action: 'update_username', new_username: newUsername.trim() }),
      });

      setUserSuccess(data.message || 'Username updated successfully');
      loadUser();
    } catch (err: any) {
      setUserError(err.message || 'Failed to update username');
    } finally {
      setUserLoading(false);
    }
  };

  const handleUpdatePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPassSuccess('');
    setPassError('');

    if (!currentPassword) {
      setPassError('Current password is required');
      return;
    }
    if (newPassword.length < 6) {
      setPassError('New password must be at least 6 characters');
      return;
    }
    if (newPassword !== confirmPassword) {
      setPassError('Passwords do not match');
      return;
    }

    setPassLoading(true);

    try {
      const data = await fetchApi<{ message: string }>('/user/profile', {
        method: 'PUT',
        body: JSON.stringify({
          action: 'update_password',
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      setPassSuccess(data.message || 'Password updated successfully');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      setPassError(err.message || 'Failed to update password');
    } finally {
      setPassLoading(false);
    }
  };

  const tabs = [
    { id: 'username', label: 'Change Username', icon: <User className="w-4 h-4" /> },
    { id: 'password', label: 'Change Password', icon: <Lock className="w-4 h-4" /> },
  ];

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Account Settings</h1>
        <p className="text-sm text-slate-400 mt-1">Manage your account credentials and security settings</p>
      </div>

      {/* Account Info Pill */}
      {user && (
        <Card className="flex items-center justify-between p-4 border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center font-mono font-bold">
              {user.username[0].toUpperCase()}
            </div>
            <div>
              <h3 className="font-semibold text-slate-100">{user.username}</h3>
              <p className="text-xs text-slate-500 font-mono">User ID: #{user.id}</p>
            </div>
          </div>

          {user.is_admin && (
            <span className="text-xs bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 px-2.5 py-1 rounded font-semibold flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" /> Administrator
            </span>
          )}
        </Card>
      )}

      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {/* Tab 1: Username */}
      {activeTab === 'username' && (
        <Card className="p-6 border-slate-800">
          <form onSubmit={handleUpdateUsername} className="space-y-4 max-w-md">
            {userSuccess && (
              <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
                <Check className="w-4 h-4 shrink-0" />
                <span>{userSuccess}</span>
              </div>
            )}
            {userError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{userError}</span>
              </div>
            )}

            <Input
              label="New Username"
              value={newUsername}
              onChange={(e) => setNewUsername(e.target.value)}
              icon={<User className="w-4 h-4" />}
              required
            />

            <Button type="submit" isLoading={userLoading}>
              Update Username
            </Button>
          </form>
        </Card>
      )}

      {/* Tab 2: Password */}
      {activeTab === 'password' && (
        <Card className="p-6 border-slate-800">
          <form onSubmit={handleUpdatePassword} className="space-y-4 max-w-md">
            {passSuccess && (
              <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
                <Check className="w-4 h-4 shrink-0" />
                <span>{passSuccess}</span>
              </div>
            )}
            {passError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{passError}</span>
              </div>
            )}

            <Input
              label="Current Password"
              type="password"
              placeholder="Required to verify identity"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              icon={<Lock className="w-4 h-4" />}
              required
            />

            <Input
              label="New Password"
              type="password"
              placeholder="Minimum 6 characters"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              icon={<Lock className="w-4 h-4" />}
              required
            />

            <Input
              label="Confirm New Password"
              type="password"
              placeholder="Repeat new password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              icon={<Lock className="w-4 h-4" />}
              required
            />

            <Button type="submit" isLoading={passLoading}>
              Update Password
            </Button>
          </form>
        </Card>
      )}
    </div>
  );
}
