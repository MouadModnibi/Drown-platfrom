'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { clsx } from 'clsx';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  hoverGlow?: boolean;
}

export const Card: React.FC<CardProps> = ({ children, className = '', hoverGlow = false }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      whileHover={hoverGlow ? { y: -2, transition: { duration: 0.2 } } : undefined}
      className={clsx(
        'glass-card rounded-xl p-5 relative overflow-hidden transition-shadow duration-300',
        hoverGlow && 'hover:shadow-xl hover:shadow-indigo-500/10 hover:border-slate-700/80',
        className
      )}
    >
      {children}
    </motion.div>
  );
};
