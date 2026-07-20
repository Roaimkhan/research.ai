import * as React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';
import { playButtonSound } from '@/lib/soundEngine';

const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap rounded-pill border border-hairline px-4 py-2 text-sm font-medium font-sans transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-ink focus-visible:ring-signal disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        primary: 'border-signal/40 bg-signal/10 text-signal shadow-[0_0_0_1px_rgba(111,255,192,0.12)] hover:bg-signal/20 hover:shadow-glow-signal',
        ghost: 'border-transparent bg-transparent text-text-muted hover:bg-ink/60 hover:text-text',
        parchment: 'border-parchment/20 bg-parchment/10 text-parchment hover:bg-parchment/20',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 px-3',
        lg: 'h-11 px-8',
        icon: 'size-10',
      },
    },
    defaultVariants: {
      variant: 'ghost',
      size: 'default',
    },
  },
);

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  sound?: 'default' | 'none';
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, asChild = false, sound = 'default', ...props }, ref) => {
  const shouldReduceMotion = useReducedMotion();
  const Comp = asChild ? Slot : 'button';
  const { style, ...restProps } = props;

  if (asChild) {
    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
  }

  const motionProps = (shouldReduceMotion
    ? restProps
    : {
        ...restProps,
        whileTap: { scale: 0.98 },
        transition: { type: 'spring' as const, stiffness: 380, damping: 30 },
      }) as unknown as React.ComponentPropsWithoutRef<typeof motion.button>;
  const resolvedProps = style ? ({ ...motionProps, style } as unknown as React.ComponentPropsWithoutRef<typeof motion.button>) : motionProps;

  return (
    <motion.button
      type={props.type ?? 'button'}
      className={cn(buttonVariants({ variant, size, className }))}
      ref={ref}
      onClick={(event) => {
        if (sound !== 'none') {
          playButtonSound();
        }
        props.onClick?.(event);
      }}
      {...resolvedProps}
    />
  );
});
Button.displayName = 'Button';

export { Button, buttonVariants };
