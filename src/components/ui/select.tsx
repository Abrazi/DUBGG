import React from 'react';

interface SelectProps {
  value: string;
  onValueChange: (value: string) => void;
  children: React.ReactNode;
}

export const Select: React.FC<SelectProps> = ({ value, onValueChange, children }) => {
  // naive render - assume children contains items that call onValueChange
  return <div>{children}</div>;
};

export const SelectTrigger: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ children, className = '', ...props }) => (
  <div className={className} {...props}>
    {children}
  </div>
);

export const SelectContent: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ children, className = '', ...props }) => (
  <div className={className} {...props}>
    {children}
  </div>
);

export const SelectItem: React.FC<{ value: string; className?: string; children?: React.ReactNode }> = ({ value, className = '', children }) => (
  <div className={className} data-value={value}>
    {children}
  </div>
);

export const SelectValue: React.FC<{ placeholder?: string; children?: React.ReactNode }> = ({ placeholder, children }) => (
  <span>{children || placeholder}</span>
);
