'use client';

import React from 'react';
import { clsx } from 'clsx';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  icon,
  className = '',
  id,
  ...props
}) => {
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className="w-full flex flex-col gap-1.5">
      {label && (
        <label htmlFor={inputId} className="text-xs font-medium text-slate-400">
          {label}
        </label>
      )}
      <div className="relative flex items-center">
        {icon && (
          <div className="absolute left-3 text-slate-500 pointer-events-none">
            {icon}
          </div>
        )}
        <input
          id={inputId}
          className={clsx(
            'w-full rounded-lg bg-slate-900/80 border border-slate-800 text-slate-100 text-sm px-3.5 py-2.5 outline-none transition-all placeholder:text-slate-600 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/50',
            icon && 'pl-10',
            error && 'border-rose-500 focus:border-rose-500 focus:ring-rose-500/50',
            className
          )}
          {...props}
        />
      </div>
      {error && <p className="text-xs text-rose-400 mt-0.5">{error}</p>}
    </div>
  );
};
