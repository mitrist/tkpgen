import { type ComponentProps, type ReactNode } from 'react';
import { type AsChildProp, type InnerClassNamesProp, type MergeProps } from '../../types';
export type CellActionMode = 'primary' | 'destructive' | 'custom';
export type CellActionHeight = 'compact' | 'normal';
export type CellActionInnerElementKey = 'before' | 'chevron' | 'content';
interface CellActionOwnProps extends AsChildProp {
    mode?: CellActionMode;
    height?: CellActionHeight;
    before?: ReactNode;
    showChevron?: boolean;
    innerClassNames?: InnerClassNamesProp<CellActionInnerElementKey>;
}
export type CellActionProps = MergeProps<ComponentProps<'button'>, CellActionOwnProps>;
export declare const CellAction: import("react").ForwardRefExoticComponent<Omit<CellActionProps, "ref"> & import("react").RefAttributes<HTMLButtonElement>>;
export {};
//# sourceMappingURL=CellAction.d.ts.map