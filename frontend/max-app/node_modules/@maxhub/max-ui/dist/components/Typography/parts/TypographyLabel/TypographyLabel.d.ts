import { type ComponentProps } from 'react';
import type { AsChildProp } from '../../../../types';
export type TypographyLabelVariant = 'large' | 'large-strong' | 'large-caps' | 'medium' | 'medium-strong' | 'small-strong' | 'small-caps' | 'custom';
export interface TypographyLabelProps extends ComponentProps<'span'>, AsChildProp {
    variant?: TypographyLabelVariant;
}
export declare const TypographyLabel: import("react").ForwardRefExoticComponent<Omit<TypographyLabelProps, "ref"> & import("react").RefAttributes<HTMLSpanElement>>;
//# sourceMappingURL=TypographyLabel.d.ts.map