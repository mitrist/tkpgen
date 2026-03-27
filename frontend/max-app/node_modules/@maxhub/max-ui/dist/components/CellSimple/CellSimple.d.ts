import { type ComponentProps, type ElementType, type ReactNode } from 'react';
import { type AsChildProp, type InnerClassNamesProp, type MergeProps } from '../../types';
export type CellSimpleHeight = 'compact' | 'normal';
export type CellSimpleInnerElementKey = 'before' | 'after' | 'chevron' | 'content' | 'title' | 'subtitle' | 'overline';
interface CellSimpleOwnProps extends AsChildProp {
    height?: CellSimpleHeight;
    innerClassNames?: InnerClassNamesProp<CellSimpleInnerElementKey>;
    title?: ReactNode;
    subtitle?: ReactNode;
    overline?: ReactNode;
    before?: ReactNode;
    after?: ReactNode;
    showChevron?: boolean;
    as?: ElementType;
    disabled?: boolean;
}
export type CellSimpleProps = MergeProps<ComponentProps<'div'>, CellSimpleOwnProps>;
export declare const CellSimple: import("react").ForwardRefExoticComponent<Omit<CellSimpleProps, "ref"> & import("react").RefAttributes<HTMLDivElement>>;
export {};
//# sourceMappingURL=CellSimple.d.ts.map