import { type ComponentProps } from 'react';
import type { AsChildProp } from '../../../../types';
export type TypographyActionVariant = 'large' | 'medium' | 'small' | 'label' | 'custom';
export interface TypographyActionProps extends ComponentProps<'span'>, AsChildProp {
    variant?: TypographyActionVariant;
}
export declare const TypographyAction: import("react").ForwardRefExoticComponent<Omit<TypographyActionProps, "ref"> & import("react").RefAttributes<HTMLSpanElement>>;
//# sourceMappingURL=TypographyAction.d.ts.map