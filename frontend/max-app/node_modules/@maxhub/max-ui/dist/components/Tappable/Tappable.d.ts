import { type AllHTMLAttributes, type ElementType, type ReactNode } from 'react';
import { type AsChildProp, type MergeProps } from '../../types';
type TappableOwnProps = {
    as?: ElementType;
    parentChildren?: ReactNode;
} & AsChildProp;
export type TappableProps = MergeProps<AllHTMLAttributes<HTMLElement>, TappableOwnProps>;
export declare const Tappable: import("react").ForwardRefExoticComponent<Omit<AllHTMLAttributes<HTMLElement>, "asChild" | "parentChildren" | "as"> & {
    as?: ElementType;
    parentChildren?: ReactNode;
} & AsChildProp & import("react").RefAttributes<HTMLElement>>;
export {};
//# sourceMappingURL=Tappable.d.ts.map