import { type ComponentProps, type ReactNode } from 'react';
import { type AsChildProp, type InnerClassNamesProp } from '../../types';
export type ButtonSize = 'small' | 'medium' | 'large';
export type ButtonMode = 'primary' | 'secondary' | 'tertiary' | 'link';
export type ButtonAppearance = 'themed' | 'negative' | 'neutral' | 'neutral-themed' | 'contrast-static';
export type ButtonInnerElementKey = 'iconBefore' | 'iconAfter' | 'indicator' | 'content' | 'spinnerContainer' | 'spinner';
export interface ButtonProps extends ComponentProps<'button'>, AsChildProp {
    size?: ButtonSize;
    mode?: ButtonMode;
    appearance?: ButtonAppearance;
    stretched?: boolean;
    iconBefore?: ReactNode;
    iconAfter?: ReactNode;
    indicator?: ReactNode;
    innerClassNames?: InnerClassNamesProp<ButtonInnerElementKey>;
    loading?: boolean;
}
export declare const Button: import("react").ForwardRefExoticComponent<Omit<ButtonProps, "ref"> & import("react").RefAttributes<HTMLButtonElement>>;
//# sourceMappingURL=Button.d.ts.map