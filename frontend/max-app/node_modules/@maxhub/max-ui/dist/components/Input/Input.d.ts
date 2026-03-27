import { type ComponentProps, type ReactNode } from 'react';
import { type InnerClassNamesProp } from '../../types';
export type InputMode = 'primary' | 'secondary';
export type InputElementKey = 'input' | 'clearButton' | 'body' | 'iconBefore' | 'iconAfter';
export interface InputProps extends ComponentProps<'input'> {
    mode?: InputMode;
    compact?: boolean;
    iconBefore?: ReactNode;
    iconAfter?: ReactNode;
    innerClassNames?: InnerClassNamesProp<InputElementKey>;
    withClearButton?: boolean;
}
export declare const Input: import("react").ForwardRefExoticComponent<Omit<InputProps, "ref"> & import("react").RefAttributes<HTMLInputElement>>;
//# sourceMappingURL=Input.d.ts.map