import { forwardRef, type InputHTMLAttributes } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className, ...props }, ref) => {
    return (
      <div className="space-y-1">
        <label className="block text-sm font-medium text-gray-300">
          {label}
        </label>
        <input
          ref={ref}
          className={`
            w-full px-3 py-2 bg-gray-700 border rounded-lg text-gray-100 placeholder-gray-400
            focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500
            transition-colors duration-200
            ${error ? 'border-red-500' : 'border-gray-600'}
            ${className || ''}
          `}
          {...props}
        />
        {error && <p className="text-sm text-red-400">{error}</p>}
      </div>
    );
  }
);

Input.displayName = 'Input';
