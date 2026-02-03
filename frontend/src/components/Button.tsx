import type { ButtonHTMLAttributes, ReactNode } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: 'primary' | 'secondary';
  isLoading?: boolean;
}

export function Button({
  children,
  variant = 'primary',
  isLoading,
  disabled,
  className,
  ...props
}: ButtonProps) {
  const baseStyles =
    'px-4 py-2 rounded-lg font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50';
  const variants = {
    primary:
      'bg-blue-600 text-white hover:bg-blue-500 active:scale-[0.98] disabled:bg-blue-600/50 disabled:text-blue-200/50',
    secondary:
      'bg-gray-700 text-gray-200 border border-gray-600 hover:bg-gray-600 active:scale-[0.98] disabled:bg-gray-700/50 disabled:text-gray-400/50',
  };

  return (
    <button
      className={`${baseStyles} ${variants[variant]} ${className || ''}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? 'Loading...' : children}
    </button>
  );
}
