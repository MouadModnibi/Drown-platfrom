'use client';

import React, { useState } from 'react';
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
    cause:
      'Your SSH key has not been registered with your account, or the key registered does not match the one your local git client is using.',
    solution: [
      'Run "drown login" again — this re-generates your SSH key if needed and re-registers it with the platform automatically.',
      'If the problem persists, check that your SSH config has the drown-platform host alias: cat ~/.ssh/config',
    ],
  },
  {
    id: 'buildpack-fail',
    category: 'Build & Compilation',
    question: 'Deployment fails with "No buildpack detected"',
    errorSnippet:
      '-----> Detecting buildpack...\nERROR: Could not detect a valid buildpack for this repository.',
    cause:
      'The Cloud Native Buildpack engine could not find a standard application manifest file in your repository root.',
    solution: [
      'Ensure package.json (Node.js) or requirements.txt (Python) exists in the root of your repository, not in a subdirectory.',
      'Check file names are exact and case-correct.',
      'Commit the manifest file and re-push: git add package.json && git commit -m "add manifest" && git push platform main',
    ],
  },
  {
    id: 'frontend-config',
    category: 'Framework-Specific Setup',
    question: 'Frontend framework (Vite, Next.js, Expo) deploys but the app does not respond / shows no content',
    errorSnippet:
      'Deploying Node.js app...\n-----> Build succeeded\nERROR: Application failed to respond on port 8080.',
    cause:
      'Buildpacks can automatically detect and run backend apps (Python/Flask, plain Node servers), but frontend frameworks that compile static files need an explicit start command and build hook — otherwise the platform has no server process to run after the build. This is the same requirement real Heroku has for these frameworks.',
    solution: [
      '--- Vite / React (Vite) ---',
      'Run: npm install serve --save',
      'Add to package.json scripts: "start": "serve -s dist -l 8080"  and  "heroku-postbuild": "vite build"',
      '(For Create React App use "build" instead of "dist": "serve -s build -l 8080")',
      '--- Next.js ---',
      'No extra package needed — Next.js has its own production server.',
      'Add to package.json scripts: "start": "next start -p 8080"  and  "heroku-postbuild": "next build"',
      '--- Expo (React Native web export) ---',
      'Run: npm install serve --save',
      'Add to package.json scripts: "start": "serve -s dist -l 8080"  and  "heroku-postbuild": "expo export -p web"',
      'Note: this deploys only the web-compatible version of your Expo app. Native-only libraries may not work correctly in the web build.',
    ],
  },
  {
    id: 'port-bind',
    category: 'Runtime & Networking',
    question: 'Container crashes immediately or fails health check',
    errorSnippet: 'Error: listen EADDRINUSE :::3000\n    at Server.setupListenHandle [as _listen2]',
    cause:
      'The application is binding to a hardcoded port or to 127.0.0.1 instead of reading the PORT environment variable injected at runtime.',
    solution: [
      'Read the port dynamically: const port = process.env.PORT || 3000',
      'Always bind to 0.0.0.0: app.listen(port, "0.0.0.0")',
      'The platform always injects PORT=8080 — make sure your app respects it.',
    ],
  },
  {
    id: 'oom-killed',
    category: 'Runtime & Memory',
    question: 'Replica status shows "Stopped" or exits with code 137',
    errorSnippet: 'Container killed by Out-Of-Memory (OOM) killer. Exit Code: 137.',
    cause: 'The container process exceeded the allocated container memory limit.',
    solution: [
      'Check application logs in the App Detail view for memory leaks or runaway processes.',
      'For Node.js apps, set NODE_OPTIONS="--max-old-space-size=512" as an environment variable in the app config.',
    ],
  },
];

// Reusable copy button with self-contained copied state
function CopyBtn({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }}
      className="flex items-center gap-1.5 px-2 py-1 rounded bg-slate-800 border border-slate-700 hover:border-slate-600 text-slate-400 hover:text-slate-200 transition-all text-xs"
    >
      {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  );
}

function CodeLine({ code }: { code: string }) {
  return (
    <div className="flex items-center gap-2">
      <pre className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 font-mono text-xs text-indigo-300 overflow-x-auto">
        {code}
      </pre>
      <CopyBtn text={code} />
    </div>
  );
}

export default function HelpPage() {
  const [search, setSearch] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showManualKey, setShowManualKey] = useState(false);

  // Manual SSH key registration (advanced)
  const [publicKey, setPublicKey] = useState('');
  const [keyLoading, setKeyLoading] = useState(false);
  const [keySuccess, setKeySuccess] = useState('');
  const [keyError, setKeyError] = useState('');

  const handleRegisterKey = async (e: React.FormEvent) => {
    e.preventDefault();
    setKeySuccess('');
    setKeyError('');

    if (!publicKey.trim().startsWith('ssh-')) {
      setKeyError('Invalid public key format. Must start with ssh-rsa or ssh-ed25519.');
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
          Guides and solutions for common build &amp; runtime errors
        </p>
      </div>

      {/* SSH Key Setup Card */}
      <Card className="p-6 border-indigo-500/30 bg-indigo-500/5 space-y-4">
        <div className="flex items-center gap-2 text-indigo-400 font-semibold text-base">
          <Key className="w-5 h-5" />
          SSH Key Setup for Git Deployment
        </div>

        <p className="text-sm text-slate-300">
          The easiest way to set up SSH access is with the Drown CLI — it handles key generation,
          registration, and SSH config automatically:
        </p>

        <div className="space-y-2">
          <CodeLine code="pip install drown" />
          <CodeLine code="drown login" />
        </div>

        <p className="text-xs text-slate-400 leading-relaxed">
          Running <span className="font-mono text-slate-300">drown login</span> automatically generates an
          SSH key at <span className="font-mono text-slate-300">~/.drown/id_ed25519</span> if you don&apos;t
          already have one, registers the public key with your account, and writes the{' '}
          <span className="font-mono text-slate-300">Host drown-platform</span> entry to your SSH config —
          so <span className="font-mono text-slate-300">git push platform main</span> works immediately with
          no extra steps.
        </p>

        {/* Advanced: manual key registration toggle */}
        
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
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="text-xs px-2.5 py-1 rounded bg-slate-800 text-slate-400 font-mono whitespace-nowrap">
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
                      <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-rose-300">
                        <pre className="whitespace-pre-wrap">{faq.errorSnippet}</pre>
                      </div>
                    </div>

                    <div>
                      <p className="font-semibold text-slate-400 mb-1">Root Cause:</p>
                      <p className="text-slate-300">{faq.cause}</p>
                    </div>

                    <div>
                      <p className="font-semibold text-slate-400 mb-2">Resolution Steps:</p>
                      {faq.id === 'frontend-config' ? (
                        // Special rendering for the framework config entry — group by framework
                        <div className="space-y-4">
                          {/* Vite / CRA */}
                          <div className="space-y-2">
                            <p className="font-semibold text-slate-300">Vite / React (Vite)</p>
                            <CodeLine code='npm install serve --save' />
                            <p className="text-slate-400">Add to <span className="font-mono text-slate-300">package.json</span> scripts:</p>
                            <CodeLine code='"start": "serve -s dist -l 8080"' />
                            <CodeLine code='"heroku-postbuild": "vite build"' />
                            <p className="text-slate-500 italic">For Create React App, use <span className="font-mono not-italic text-slate-400">dist</span> → <span className="font-mono not-italic text-slate-400">build</span>: <span className="font-mono not-italic text-slate-400">"serve -s build -l 8080"</span></p>
                          </div>

                          {/* Next.js */}
                          <div className="space-y-2 border-t border-slate-800/60 pt-4">
                            <p className="font-semibold text-slate-300">Next.js</p>
                            <p className="text-slate-400">No extra package needed — Next.js includes its own production server. Add to <span className="font-mono text-slate-300">package.json</span> scripts:</p>
                            <CodeLine code='"start": "next start -p 8080"' />
                            <CodeLine code='"heroku-postbuild": "next build"' />
                          </div>

                          {/* Expo */}
                          <div className="space-y-2 border-t border-slate-800/60 pt-4">
                            <p className="font-semibold text-slate-300">Expo (React Native web export)</p>
                            <CodeLine code='npm install serve --save' />
                            <p className="text-slate-400">Add to <span className="font-mono text-slate-300">package.json</span> scripts:</p>
                            <CodeLine code='"start": "serve -s dist -l 8080"' />
                            <CodeLine code='"heroku-postbuild": "expo export -p web"' />
                            <p className="text-slate-500 italic">This deploys the web-compatible version only. Native-only libraries may not work in the web build.</p>
                          </div>
                        </div>
                      ) : (
                        <ol className="list-decimal list-inside space-y-1 text-slate-300">
                          {faq.solution.map((step, idx) => (
                            <li key={idx} className="leading-relaxed">
                              {step}
                            </li>
                          ))}
                        </ol>
                      )}
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
