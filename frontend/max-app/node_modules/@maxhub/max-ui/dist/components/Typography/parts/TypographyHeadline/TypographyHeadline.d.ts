import { type ComponentProps } from 'react';
import type { AsChildProp } from '../../../../types';
export type TypographyHeadlineVariant = 'large-strong' | 'medium' | 'medium-strong' | 'small' | 'small-strong' | 'custom';
export interface TypographyHeadlineProps extends ComponentProps<'span'>, AsChildProp {
    variant?: TypographyHeadlineVariant;
}
export declare const TypographyHeadline: import("react").ForwardRefExoticComponent<Omit<TypographyHeadlineProps, "ref"> & import("react").RefAttributes<HTMLSpanElement>>;
//# sourceMappingURL=TypographyHeadline.d.ts.map