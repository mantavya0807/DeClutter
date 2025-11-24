'use client';

import { login, signup } from './actions';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { ArrowLeft, Mail, Lock, Loader2, Github, Chrome } from 'lucide-react';
import { useState } from 'react';
import { useFormStatus } from 'react-dom';

function SubmitButton({ text, icon: Icon, variant = 'primary', ...props }: { text: string, icon?: any, variant?: 'primary' | 'secondary' } & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const { pending } = useFormStatus();
  
  return (
    <button 
      {...props}
      disabled={pending || props.disabled}
      className={`w-full py-3 px-4 rounded-xl font-semibold transition-all duration-200 flex items-center justify-center gap-2 ${
        variant === 'primary' 
          ? 'bg-gradient-to-r from-[#5BAAA7] to-[#1A6A6A] text-white hover:shadow-lg hover:scale-[1.02] active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed'
          : 'bg-white border-2 border-[#5BAAA7] text-[#5BAAA7] hover:bg-[#5BAAA7]/5 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed'
      }`}
    >
      {pending ? (
        <Loader2 className="w-5 h-5 animate-spin" />
      ) : (
        <>
          {Icon && <Icon className="w-5 h-5" />}
          {text}
        </>
      )}
    </button>
  );
}

export default function LoginPage() {
  const [isLogin, setIsLogin] = useState(true);

  return (
    <div className="min-h-screen w-full flex bg-[#F8F9FA]">
      {/* Left Side - Visual & Branding */}
      <div className="hidden lg:flex w-1/2 bg-[#0a1b2a] relative overflow-hidden items-center justify-center p-12">
        {/* Animated Background Elements */}
        <div className="absolute inset-0">
          <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-[#5BAAA7]/20 to-transparent opacity-60" />
          <motion.div 
            animate={{ 
              scale: [1, 1.2, 1],
              rotate: [0, 5, -5, 0],
            }}
            transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
            className="absolute -top-20 -left-20 w-96 h-96 bg-[#5BAAA7]/30 rounded-full blur-3xl"
          />
          <motion.div 
            animate={{ 
              scale: [1, 1.1, 1],
              x: [0, 30, 0],
            }}
            transition={{ duration: 15, repeat: Infinity, ease: "easeInOut" }}
            className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-[#1A6A6A]/40 rounded-full blur-3xl"
          />
        </div>

        {/* Content */}
        <div className="relative z-10 max-w-lg text-white">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <h1 className="text-5xl font-bold mb-6 leading-tight">
              Turn your clutter into <span className="text-[#5BAAA7]">cash</span>.
            </h1>
            <p className="text-xl text-gray-300 mb-8 leading-relaxed">
              Join thousands of users who are automatically identifying, pricing, and selling their unused items across multiple marketplaces with AI.
            </p>
            
            <div className="space-y-4">
              {[
                "AI-powered item detection",
                "Multi-platform listing automation",
                "Smart pricing intelligence",
                "Automated buyer communication"
              ].map((feature, i) => (
                <motion.div 
                  key={i}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.4 + (i * 0.1) }}
                  className="flex items-center gap-3"
                >
                  <div className="w-6 h-6 rounded-full bg-[#5BAAA7]/20 flex items-center justify-center border border-[#5BAAA7]/50">
                    <div className="w-2 h-2 rounded-full bg-[#5BAAA7]" />
                  </div>
                  <span className="text-gray-200">{feature}</span>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>

      {/* Right Side - Form */}
      <div className="w-full lg:w-1/2 flex flex-col items-center justify-center p-6 sm:p-12 relative">
        <Link 
          href="/" 
          className="absolute top-8 left-8 flex items-center gap-2 text-gray-500 hover:text-[#5BAAA7] transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Home
        </Link>

        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-md space-y-8"
        >
          <div className="text-center">
            <h2 className="text-3xl font-bold text-[#0a1b2a]">
              {isLogin ? 'Welcome back' : 'Create an account'}
            </h2>
            <p className="mt-2 text-gray-500">
              {isLogin ? 'Enter your details to access your dashboard' : 'Start your decluttering journey today'}
            </p>
          </div>

          {/* Social Login Buttons (Visual Only) */}
          <div className="grid grid-cols-2 gap-4">
            <button className="flex items-center justify-center gap-2 py-2.5 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors">
              <Github className="w-5 h-5" />
              <span className="text-sm font-medium text-gray-700">Github</span>
            </button>
            <button className="flex items-center justify-center gap-2 py-2.5 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors">
              <Chrome className="w-5 h-5 text-blue-500" />
              <span className="text-sm font-medium text-gray-700">Google</span>
            </button>
          </div>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-[#F8F9FA] text-gray-500">Or continue with email</span>
            </div>
          </div>

          <form className="space-y-6">
            <div className="space-y-4">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">Email address</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Mail className="h-5 w-5 text-gray-400" />
                  </div>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                    className="block w-full pl-10 pr-3 py-3 border border-gray-200 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#5BAAA7] focus:border-transparent transition-all bg-white"
                    placeholder="you@example.com"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Lock className="h-5 w-5 text-gray-400" />
                  </div>
                  <input
                    id="password"
                    name="password"
                    type="password"
                    autoComplete={isLogin ? "current-password" : "new-password"}
                    required
                    className="block w-full pl-10 pr-3 py-3 border border-gray-200 rounded-xl text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#5BAAA7] focus:border-transparent transition-all bg-white"
                    placeholder="••••••••"
                  />
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <input
                  id="remember-me"
                  name="remember-me"
                  type="checkbox"
                  className="h-4 w-4 text-[#5BAAA7] focus:ring-[#5BAAA7] border-gray-300 rounded"
                />
                <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-700">
                  Remember me
                </label>
              </div>

              {isLogin && (
                <div className="text-sm">
                  <a href="#" className="font-medium text-[#5BAAA7] hover:text-[#1A6A6A]">
                    Forgot password?
                  </a>
                </div>
              )}
            </div>

            <div className="space-y-3">
              {isLogin ? (
                <>
                  <SubmitButton text="Sign in" formAction={login} />
                  <button 
                    type="button"
                    onClick={() => setIsLogin(false)}
                    className="w-full py-3 px-4 rounded-xl font-semibold text-gray-600 hover:bg-gray-100 transition-all duration-200"
                  >
                    Create an account
                  </button>
                </>
              ) : (
                <>
                  <SubmitButton text="Create account" formAction={signup} />
                  <button 
                    type="button"
                    onClick={() => setIsLogin(true)}
                    className="w-full py-3 px-4 rounded-xl font-semibold text-gray-600 hover:bg-gray-100 transition-all duration-200"
                  >
                    Already have an account? Sign in
                  </button>
                </>
              )}
            </div>
          </form>
        </motion.div>
      </div>
    </div>
  );
}
