import * as React from 'react';
import { Button } from './button';

interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  icon: React.ReactNode;
}

const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(({ label, icon, children, className, ...props }, ref) => {
  return (
    <Button ref={ref} variant="ghost" className={className} aria-label={label} {...props}>
      {icon}
      {children}
    </Button>
  );
});

IconButton.displayName = 'IconButton';

export { IconButton };
