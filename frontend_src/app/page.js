'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    // Check if user is logged in
    const token = localStorage.getItem('access_token');
    if (token) {
      router.push('/dashboard');
    } else {
      router.push('/login');
    }
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center premium-bg animate-fade-in">
      <div className="text-center">
        <div className="w-20 h-20 bg-white/10 backdrop-blur-xl rounded-[2.5rem] flex items-center justify-center shadow-2xl ring-1 ring-white/20 animate-pulse relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-tr from-primary/20 to-secondary/20 animate-spin-slow"></div>
          <div className="w-10 h-10 border-4 border-white/20 border-t-white rounded-full animate-spin relative z-10"></div>
        </div>
        <p className="mt-8 text-white font-black uppercase tracking-[0.3em] text-xs drop-shadow-sm">Calibrating Nexus</p>
      </div>
    </div>
  );
}
