import { type ComponentProps } from 'react';
export type CounterAppearance = 'themed' | 'neutral' | 'neutral-themed' | 'neutral-static' | 'negative';
export type CounterMode = 'filled' | 'inverse';
export interface CounterProps extends ComponentProps<'span'> {
    value: number;
    rounded?: boolean;
    appearance?: CounterAppearance;
    disabled?: boolean;
    muted?: boolean;
    mode?: CounterMode;
}
export declare const Counter: import("react").ForwardRefExoticComponent<Omit<CounterProps, "ref"> & import("react").RefAttributes<HTMLSpanElement>>;
//# sourceMappingURL=Counter.d.ts.map