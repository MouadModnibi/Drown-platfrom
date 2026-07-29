'use client';

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  HelpCircle,
  Search,
  Key,
  Terminal,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
} from 'lucide-react';
import { fetchApi } from '@/lib/api-client';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';

interface FAQ {
  id: string;
  category: string;
  question: string;
  errorSnippet: string;
  cause: string;
  solution: string[];
}

const FAQS: FAQ[] = [
  {
    id: 'ssh-denied',
    category: 'Git & Deployment',
    question: 'Git push fails with "Permission denied (publickey)"',
    errorSnippet: 'Permission denied (publickey).\nfatal: Could not read from remote repository.',
    cause: 'Your local SSH public key has not been registered with your Mini-Heroku account or is not loaded into ssh-agent.',
    solution: [
      'Copy your local SSH public key (~/.ssh/id_ed25519.pub or ~/.ssh/id_rsa.pub).',
      'Paste it into the SSH Key Registration card on this page.',
      'Test your SSH connection via: ssh -T ubuntu@51.170.134.251',
    ],
  },
  {
    id: 'buildpack-fail',
    category: 'Build & Compilation',
    question: 'Deployment fails with "No buildpack detected"',
    errorSnippet: '-----> Detecting buildpack...\nERROR: Could not detect a valid buildpack for this repository.',
    cause: 'The Cloud Native Buildpack engine could not identify standard application manifest files (e.g. package.json, requirements.txt, go.mod).',
    solution: [
      'Ensure package.json (for Node.js) or requirements.txt (for Python) exists in the repository root directory.',
      'Check that your file names are exact (case-sensitive).',
      'Commit the manifest file to git and re-push: git add package.json && git commit -m "add manifest" && git push platform main',
    ],
  },
  {
    id: 'port-bind',
    category: 'Runtime & Networking',
    question: 'Container crashes immediately or fails health check',
    errorSnippet: 'Error: listen EADDRINUSE :::3000\n    at Server.setupListenHandle [as _listen2]',
    cause: 'The application inside the container is attempting to bind to a hardcoded port or 127.0.0.1 instead of reading the dynamic PORT environment variable.',
    solution: [
      'In your application server startup code, bind to process.env.PORT || 3000.',
      'Always bind to host 0.0.0.0 (e.g. app.listen(process.env.PORT, "0.0.0.0")).',
    ],
  },
  {
    id: 'oom-killed',
    category: 'Runtime & Memory',
    question: 'Replica status shows "Stopped" or exits with code 137',
    errorSnippet: 'Container killed by Out-Of-Memory (OOM) killer. Exit Code: 137.',
    cause: 'The container process exceeded the allocated container memory limit.',
    solution: [
      'Inspect application logs in the App Detail view to detect memory leaks.',
      'Optimize node memory limits (e.g. NODE_OPTIONS="--max-old-space-size=512").',
    ],
  },
];

export default function HelpPage() {
  const [search, setSearch] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>('ssh-denied');

  // SSH Key Register state
  const [publicKey, setPublicKey] = useState('');
  const [keyLoading, setKeyLoading] = useState(false);
  const [keySuccess, setKeySuccess] = useState('');
  const [keyError, setKeyError] = useState('');

  const [copiedSnippet, setCopiedSnippet] = useState<string | null>(null);

  const handleRegisterKey = async (e: React.FormEvent) => {
    e.preventDefault();
    setKeySuccess('');
    setKeyError('');

    if (!publicKey.trim().startsWith('ssh-')) {
      setKeyError('Invalid public key format. Must start with ssh-rsa or ssh-ed25519');
      return;
    }

    setKeyLoading(true);

    try {
      const data = await fetchApi<{ message: string }>('/keys/register', {
        method: 'POST',
        body: JSON.stringify({ public_key: publicKey.trim() }),
      });
      setKeySuccess(data.message || 'Key registered successfully!');
      setPublicKey('');
    } catch (err: any) {
      setKeyError(err.message || 'Failed to register SSH key');
    } finally {
      setKeyLoading(false);
    }
  };

  const copyToClipboard = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSnippet(id);
    setTimeout(() => setCopiedSnippet(null), 2000);
  };

  const filteredFaqs = FAQS.filter(
    (faq) =>
      faq.question.toLowerCase().includes(search.toLowerCase()) ||
      faq.cause.toLowerCase().includes(search.toLowerCase()) ||
      faq.category.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
          <HelpCircle className="w-6 h-6 text-indigo-400" />
          Help &amp; Deployment Troubleshooting
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Guides, SSH key registration, and solutions for common build &amp; runtime errors
        </p>
      </div>

      {/* SSH Key Registration Card */}
      <Card className="p-6 border-indigo-500/30 bg-indigo-500/5 space-y-4">
        <div className="flex items-center gap-2 text-indigo-400 font-semibold text-base">
          <Key className="w-5 h-5" />
          Register SSH Public Key for Git Deployment
        </div>
        <p className="text-xs text-slate-300">
          Paste your public key below (`cat ~/.ssh/id_ed25519.pub`) to authenticate git push commands to `ssh://ubuntu@drown-platform`.
        </p>

        <form onSubmit={handleRegisterKey} className="space-y-3">
          {keySuccess && (
            <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{keySuccess}</span>
            </div>
          )}
          {keyError && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{keyError}</span>
            </div>
          )}

          <textarea
            rows={2}
            placeholder="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... user@example.com"
            value={publicKey}
            onChange={(e) => setPublicKey(e.target.value)}
            className="w-full rounded-lg bg-slate-900/90 border border-slate-800 text-slate-100 font-mono text-xs p-3 outline-none focus:border-indigo-500"
            required
          />

          <Button type="submit" size="sm" isLoading={keyLoading}>
            Register SSH Key
          </Button>
        </form>
      </Card>

      {/* Search Bar */}
      <div className="max-w-md">
        <Input
          placeholder="Search errors or keywords..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          icon={<Search className="w-4 h-4" />}
        />
      </div>

      {/* FAQs Accordion */}
      <div className="space-y-4">
        <h2 className="text-lg font-bold text-slate-100">Common Build &amp; Runtime Fixes</h2>

        {filteredFaqs.length === 0 ? (
          <Card className="text-center py-8 text-slate-400 text-sm">
            No troubleshooting guides found matching your search.
          </Card>
        ) : (
          filteredFaqs.map((faq) => {
            const isExpanded = expandedId === faq.id;
            return (
              <Card key={faq.id} className="border-slate-800 p-0 overflow-hidden">
                <button
                  onClick={() => setExpandedId(isExpanded ? null : faq.id)}
                  className="w-full text-left p-5 flex items-center justify-between gap-4 hover:bg-slate-800/30 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xs px-2.5 py-1 rounded bg-slate-800 text-slate-400 font-mono">
                      {faq.category}
                    </span>
                    <h3 className="text-sm font-semibold text-slate-100">{faq.question}</h3>
                  </div>
                  {isExpanded ? (
                    <ChevronUp className="w-4 h-4 text-slate-400 shrink-0" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-slate-400 shrink-0" />
                  )}
                </button>

                {isExpanded && (
                  <div className="px-5 pb-5 pt-2 border-t border-slate-800/80 space-y-4 text-xs">
                    <div>
                      <p className="font-semibold text-slate-400 mb-1">Observed Error Snippet:</p>
                      <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-rose-300 relative">
                        <pre className="whitespace-pre-wrap">{faq.errorSnippet}</pre>
                      </div>
                    </div>

                    <div>
                      <p className="font-semibold text-slate-400 mb-1">Root Cause:</p>
                      <p className="text-slate-300">{faq.cause}</p>
                    </div>

                    <div>
                      <p className="font-semibold text-slate-400 mb-1">Resolution Steps:</p>
                      <ol className="list-decimal list-inside space-y-1 text-slate-300">
                        {faq.solution.map((step, idx) => (
                          <li key={idx} className="leading-relaxed">
                            {step}
                          </li>
                        ))}
                      </ol>
                    </div>
                  </div>
                )}
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
}
