import { type ComponentProps, type ReactNode } from 'react';
import { type AsChildProp, type InnerClassNamesProp } from '../../types';
export type ToolButtonAppearance = 'default' | 'secondary';
export type ToolButtonElementKey = 'label' | 'icon';
export interface ToolButtonProps extends ComponentProps<'button'>, AsChildProp {
    icon?: ReactNode;
    innerClassNames?: InnerClassNamesProp<ToolButtonElementKey>;
    appearance?: ToolButtonAppearance;
}
export declare const ToolButton: import("react").ForwardRefExoticComponent<Omit<ToolButtonProps, "ref"> & import("react").RefAttributes<HTMLButtonElement>>;
//# sourceMappingURL=ToolButton.d.ts.map