import { type ComponentProps } from 'react';
import { type AsChildProp, type InnerClassNamesProp } from '../../types';
export type IconButtonSize = 'small' | 'medium' | 'large';
export type IconButtonMode = 'primary' | 'secondary' | 'tertiary' | 'link';
export type IconButtonAppearance = 'themed' | 'negative' | 'neutral' | 'neutral-themed' | 'contrast-static';
export type IconButtonInnerElementKey = 'content' | 'spinnerContainer' | 'spinner';
export interface IconButtonProps extends ComponentProps<'button'>, AsChildProp {
    size?: IconButtonSize;
    mode?: IconButtonMode;
    appearance?: IconButtonAppearance;
    disabled?: boolean;
    loading?: boolean;
    innerClassNames?: InnerClassNamesProp<IconButtonInnerElementKey>;
}
export declare const IconButton: import("react").ForwardRefExoticComponent<Omit<IconButtonProps, "ref"> & import("react").RefAttributes<HTMLButtonElement>>;
//# sourceMappingURL=IconButton.d.ts.map