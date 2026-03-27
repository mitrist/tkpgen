import { type ComponentProps } from 'react';
import { type AsChildProp } from '../../types';
export type FlexDisplay = 'flex' | 'inline-flex';
export type FlexDirection = 'row' | 'column' | 'row-reverse' | 'column-reverse';
export type FlexAlign = 'flex-start' | 'flex-end' | 'center' | 'baseline' | 'stretch';
export type FlexJustify = 'start' | 'center' | 'end' | 'space-between';
export type FlexWrap = 'wrap' | 'nowrap' | 'wrap-reverse';
export interface FlexProps extends ComponentProps<'div'>, AsChildProp {
    display?: FlexDisplay;
    direction?: FlexDirection;
    align?: FlexAlign;
    justify?: FlexJustify;
    wrap?: FlexWrap;
    gap?: number | string;
    gapX?: number | string;
    gapY?: number | string;
}
export declare const Flex: import("react").ForwardRefExoticComponent<Omit<FlexProps, "ref"> & import("react").RefAttributes<HTMLDivElement>>;
//# sourceMappingURL=Flex.d.ts.map