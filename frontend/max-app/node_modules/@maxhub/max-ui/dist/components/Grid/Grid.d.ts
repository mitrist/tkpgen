import { type ComponentProps } from 'react';
import { type AsChildProp } from '../../types';
export type GridDisplay = 'grid' | 'inline-grid';
export type GridAlign = 'start' | 'center' | 'end' | 'baseline' | 'stretch';
export type GridJustify = 'start' | 'center' | 'end' | 'space-between';
export interface GridProps extends ComponentProps<'div'>, AsChildProp {
    display?: GridDisplay;
    align?: GridAlign;
    justify?: GridJustify;
    gap?: number | string;
    gapX?: number | string;
    gapY?: number | string;
    cols?: number;
    rows?: number;
}
export declare const Grid: import("react").ForwardRefExoticComponent<Omit<GridProps, "ref"> & import("react").RefAttributes<HTMLDivElement>>;
//# sourceMappingURL=Grid.d.ts.map